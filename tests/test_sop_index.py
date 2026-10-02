import hashlib

import pytest

pytest.importorskip("chromadb")
from soc_copilot import config
from soc_copilot.sop_store import Sop, SopStore


class HashEF:
    def __call__(self, input):
        return [[b / 255.0 + 0.01 for b in hashlib.sha256(t.encode()).digest()[:16]] for t in input]

    def name(self):
        return "hash_ef"


BODY = ("## Điều kiện áp dụng\nSSH thất bại nhiều lần. Wazuh rule 5712.\n\n"
        "## Cách xác minh\nchạy grep abc\n\n## Ngăn chặn\nchặn bằng iptables\n")


def mk(body=BODY):
    return Sop(id="s", title="Tiêu đề", category="Cat", default_severity="High",
               body=body, sha256="x", path="s.md")


def test_index_text_only_conditions(monkeypatch):
    monkeypatch.setattr(config, "EMBED_TEXT_MODE", "conditions", raising=False)
    t = mk().index_text
    assert "SSH thất bại nhiều lần" in t and "Tiêu đề" in t and "Cat" in t
    assert "grep" not in t and "iptables" not in t


def test_index_text_fallback_without_section(monkeypatch):
    monkeypatch.setattr(config, "EMBED_TEXT_MODE", "conditions", raising=False)
    assert "Nội dung không có mục" in mk("Nội dung không có mục điều kiện.").index_text


def test_full_mode_is_old_behaviour(monkeypatch):
    monkeypatch.setattr(config, "EMBED_TEXT_MODE", "full", raising=False)
    s = mk()
    assert s.index_text == s.document


def test_prompt_document_stays_full(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EMBED_TEXT_MODE", "conditions", raising=False)
    d = tmp_path / "sops"
    d.mkdir()
    (d / "s.md").write_text(f"---\nid: s\ntitle: T\ncategory: c\ndefault_severity: High\n---\n{BODY}",
                            encoding="utf-8")
    st = SopStore(chroma_path=tmp_path / "ch", sop_dir=d, embedding_function=HashEF(), embed_model="m")
    st.sync()
    assert "iptables" in st.get_sop("s")["document"]      # prompt vẫn nhận SOP đầy đủ


def test_mode_change_triggers_reindex(tmp_path, monkeypatch):
    d = tmp_path / "sops"
    d.mkdir()
    (d / "s.md").write_text(f"---\nid: s\ntitle: T\ncategory: c\ndefault_severity: High\n---\n{BODY}",
                            encoding="utf-8")
    monkeypatch.setattr(config, "EMBED_TEXT_MODE", "conditions", raising=False)
    st = SopStore(chroma_path=tmp_path / "ch", sop_dir=d, embedding_function=HashEF(), embed_model="m")
    assert st.sync()["added"] == ["s"]
    assert st.sync()["unchanged"] == ["s"]
    monkeypatch.setattr(config, "EMBED_TEXT_MODE", "full", raising=False)
    assert st.sync()["updated"] == ["s"]
