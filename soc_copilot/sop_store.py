"""B2: kho SOP + Chroma. Nguồn sự thật là data/sops/*.md, Chroma chỉ là chỉ mục."""
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml
import chromadb
from chromadb.config import Settings

from . import config

COLLECTION_NAME = "soc_sops_v1"
_FRONT = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n(.*))?\Z", re.S)
_REQUIRED = ("id", "title", "category", "default_severity")
_COND = re.compile(r"^##[ \t]*Điều kiện áp dụng[ \t]*\n(.*?)(?=^##[ \t]|\Z)", re.S | re.M)
_FALLBACK_CHARS = 600


def embed_text_mode() -> str:
    """'conditions' (mặc định): chỉ embed tiêu đề + loại + mục 'Điều kiện áp dụng'.
    'full': embed cả tiêu đề + toàn bộ nội dung (hành vi cũ). Đặt config.EMBED_TEXT_MODE để đổi."""
    mode = getattr(config, "EMBED_TEXT_MODE", "conditions")
    return mode if mode in ("conditions", "full") else "conditions"


def index_version() -> str:
    # đổi chế độ embed thì sync tự nhúng lại, không cần xoá thư mục Chroma
    return f"{embed_text_mode()}-v1"


class SopStoreError(Exception):
    pass


class EmbedModelMismatch(SopStoreError):
    pass


@dataclass
class Sop:
    id: str
    title: str
    category: str
    default_severity: str
    body: str
    sha256: str
    path: str

    @property
    def document(self) -> str:
        # văn bản đầy đủ: lưu trong Chroma và đưa vào prompt
        return f"{self.title}\n\n{self.body}"

    @property
    def index_text(self) -> str:
        # văn bản dùng để tính embedding (chỉ ảnh hưởng truy xuất, không ảnh hưởng prompt)
        if embed_text_mode() == "full":
            return self.document
        m = _COND.search(self.body)
        cond = m.group(1).strip() if m else self.body[:_FALLBACK_CHARS].strip()
        return f"{self.title}\n{self.category}\n{cond}"

    @property
    def metadata(self) -> dict:
        return {"title": self.title, "category": self.category,
                "default_severity": self.default_severity,
                "sha256": self.sha256, "path": self.path,
                "index_v": index_version()}


def parse_sop_file(path: Path) -> Sop:
    # chuẩn hoá xuống dòng để git autocrlf trên Windows không làm đổi hash
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    m = _FRONT.match(text)
    if not m:
        raise SopStoreError(f"{path.name}: thiếu front matter YAML (--- ... ---)")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise SopStoreError(f"{path.name}: front matter YAML lỗi: {e}")
    if not isinstance(meta, dict):
        raise SopStoreError(f"{path.name}: front matter phải là mapping")
    missing = [k for k in _REQUIRED if not meta.get(k)]
    if missing:
        raise SopStoreError(f"{path.name}: thiếu trường {missing}")
    body = (m.group(2) or "").strip()
    if not body:
        raise SopStoreError(f"{path.name}: nội dung SOP rỗng")
    return Sop(id=str(meta["id"]), title=str(meta["title"]),
               category=str(meta["category"]),
               default_severity=str(meta["default_severity"]), body=body,
               sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
               path=path.name)


def load_sops(sop_dir=config.SOP_DIR) -> List[Sop]:
    files = sorted(Path(sop_dir).glob("*.md"))
    sops, seen = [], {}
    for f in files:
        s = parse_sop_file(f)
        if s.id in seen:
            raise SopStoreError(f"id '{s.id}' trùng: {seen[s.id]} và {f.name}")
        seen[s.id] = f.name
        sops.append(s)
    return sops


class SopStore:
    def __init__(self, chroma_path=config.CHROMA_PATH, sop_dir=config.SOP_DIR,
                 embedding_function=None, embed_model=config.EMBED_MODEL,
                 collection_name=COLLECTION_NAME):
        self.sop_dir = Path(sop_dir)
        self.embed_model = embed_model
        self.client = chromadb.PersistentClient(
            path=str(chroma_path), settings=Settings(anonymized_telemetry=False))
        if embedding_function is None:
            from chromadb.utils import embedding_functions
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embed_model)
        self.ef = embedding_function
        exists = collection_name in [c.name for c in self.client.list_collections()]
        if exists:
            self.coll = self.client.get_collection(
                collection_name, embedding_function=embedding_function)
        else:
            self.coll = self.client.create_collection(
                collection_name, embedding_function=embedding_function,
                metadata={"hnsw:space": "cosine", "embed_model": embed_model})
        self._check_metadata()

    def _check_metadata(self):
        meta = self.coll.metadata or {}
        stored = meta.get("embed_model")
        if stored != self.embed_model:
            raise EmbedModelMismatch(
                f"Collection được tạo với embed_model='{stored}' nhưng config là "
                f"'{self.embed_model}'. Xoá thư mục Chroma và sync lại, hoặc sửa config.")
        if meta.get("hnsw:space") != "cosine":
            raise SopStoreError(
                f"Collection không dùng cosine (hnsw:space={meta.get('hnsw:space')!r}). "
                "Xoá thư mục Chroma và sync lại.")

    def sync(self) -> dict:
        sops = load_sops(self.sop_dir)
        if not sops:
            raise SopStoreError(
                f"Không có file .md nào trong {self.sop_dir}; dừng để tránh xoá sạch DB.")
        existing = self.coll.get(include=["metadatas"])
        old = {i: ((m or {}).get("sha256"), (m or {}).get("index_v")) for i, m in
               zip(existing["ids"], existing["metadatas"])}
        new = {s.id: s for s in sops}
        ver = index_version()

        def same(i):
            return old[i] == (new[i].sha256, ver)

        added = [i for i in new if i not in old]
        updated = [i for i in new if i in old and not same(i)]
        removed = [i for i in old if i not in new]
        unchanged = [i for i in new if i in old and same(i)]

        todo = [new[i] for i in added + updated]
        if todo:
            # embedding tính từ index_text; documents vẫn là văn bản đầy đủ
            vecs = self.ef([s.index_text for s in todo])
            self.coll.upsert(ids=[s.id for s in todo],
                             embeddings=[[float(x) for x in v] for v in vecs],
                             documents=[s.document for s in todo],
                             metadatas=[s.metadata for s in todo])
        if removed:
            self.coll.delete(ids=removed)
        return {"added": added, "updated": updated,
                "removed": removed, "unchanged": unchanged}

    def count(self) -> int:
        return self.coll.count()

    def get_sop(self, sop_id: str) -> Optional[dict]:
        r = self.coll.get(ids=[sop_id], include=["documents", "metadatas"])
        if not r["ids"]:
            return None
        return {"id": r["ids"][0], "document": r["documents"][0],
                "metadata": r["metadatas"][0]}

    def all_sops(self) -> List[dict]:
        r = self.coll.get(include=["documents", "metadatas"])
        return [{"id": i, "document": d, "metadata": m}
                for i, d, m in zip(r["ids"], r["documents"], r["metadatas"])]

    def query(self, text: str, n_results: int = 3) -> List[dict]:
        n = max(1, min(n_results, self.coll.count()))
        r = self.coll.query(query_texts=[text], n_results=n,
                            include=["distances", "metadatas"])
        return [{"id": i, "distance": d, "metadata": m} for i, d, m in
                zip(r["ids"][0], r["distances"][0], r["metadatas"][0])]
