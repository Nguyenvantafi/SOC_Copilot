"""ui/backend.py: lớp nối giữa giao diện và lõi pipeline của Bình.

Giao diện chỉ gọi các hàm ở đây, không import trực tiếp soc_copilot ở nơi khác. Nếu chưa có `soc_copilot.core`
thì tự dùng backend GIẢ (ui/mock_backend.py) và giao diện hiện cảnh báo rõ ràng.

HỢP ĐỒNG với Bình (xem docs/GIAO_DIEN_VOI_BINH.md):
  soc_copilot.core.analyze_alert(alert, model=..., threshold=..., retrieval=...) -> AnalysisResult (pydantic) hoặc dict
  soc_copilot.llm.health() -> dict {ok: bool, version: str|None, models: list[str], error: str|None}
  soc_copilot.config: THRESHOLD, DEFAULT_MODEL, PROTECTED_IPS (đều tuỳ chọn ở phía giao diện)
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional

from . import mock_backend

MODES = {
    "rag": "RAG (truy xuất ngữ nghĩa)",
    "rule_map": "Baseline: tra theo rule.id",
    "full_context": "Baseline: đưa toàn bộ SOP vào prompt",
}

_IMPORT_ERROR: Optional[str] = None
_FORCE_MOCK = os.environ.get("SOC_COPILOT_UI_MOCK", "").strip().lower() in ("1", "true", "yes")
try:  # pragma: no cover - phụ thuộc repo của Bình
    if _FORCE_MOCK:
        raise ImportError("SOC_COPILOT_UI_MOCK=1: ép dùng backend giả")
    from soc_copilot.core import analyze_alert as _analyze_alert  # type: ignore
    from soc_copilot import llm as _llm  # type: ignore
    _REAL = True
except Exception as _e:  # ImportError hoặc lỗi khác khi import
    _analyze_alert = None
    _llm = None
    _REAL = False
    _IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

try:  # pragma: no cover
    from soc_copilot import config as _config  # type: ignore
except Exception:
    _config = None


def is_real() -> bool:
    return _REAL


def import_error() -> Optional[str]:
    return _IMPORT_ERROR


def cfg(name: str, default: Any = None) -> Any:
    return getattr(_config, name, default) if _config is not None else default


def to_dict(result: Any) -> dict:
    """AnalysisResult (pydantic v2/v1) hoặc dict -> dict thuần."""
    if isinstance(result, dict):
        return result
    for attr in ("model_dump", "dict"):
        fn = getattr(result, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                continue
    return dict(getattr(result, "__dict__", {}))


# ---------------------------------------------------------------------------
# Chuyển kết quả của lõi (AnalysisResult phẳng của Bình) sang hợp đồng mà UI/storage đọc
# (Phụ lục A của kế hoạch: rule_severity, action_target_ip, sop_alternatives, timings{}, meta{}, alert_summary{}...).
# Nếu thiếu bước này, UI chạy nhưng âm thầm không hiện badge theo rule.level, thời gian, mô hình, bằng chứng...
# ---------------------------------------------------------------------------
_SOP_FRONT = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n(.*)\Z", re.S)


def _sop_info(sop_id: Optional[str]) -> tuple[str, dict]:
    """(tiêu đề, {tên mục: nội dung}) của một SOP, đọc thẳng data/sops/<id>.md (không cần Chroma)."""
    if not sop_id or not re.fullmatch(r"[A-Za-z0-9_\-]+", str(sop_id)):
        return "", {}
    sop_dir = cfg("SOP_DIR", None)
    if sop_dir is None:
        return "", {}
    try:
        text = (sop_dir / f"{sop_id}.md").read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return "", {}
    m = _SOP_FRONT.match(text)
    if not m:
        return "", {}
    title = ""
    for line in m.group(1).splitlines():
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip().strip("\"'")
    sections = {}
    for part in re.split(r"(?m)^## ", m.group(2))[1:]:
        head, _, body = part.partition("\n")
        sections[head.strip()] = body.strip()
    return title, sections


def _alert_summary(alert: Any) -> dict:
    try:
        from soc_copilot import features
        c = features.compact_alert(features.normalize_alert(alert))
        out = {"rule_id": c.get("rule_id"), "level": c.get("level"), "agent": c.get("agent"),
               "srcip": c.get("srcip"), "mitre": c.get("mitre")}
        if c.get("url"):
            out["url"] = c["url"]
        if c.get("syscheck_path"):
            out["path"] = c["syscheck_path"]
        return {k: v for k, v in out.items() if v not in (None, "", [])}
    except Exception:
        return {}


def to_contract(res: dict, alert: Any = None) -> dict:
    """Bổ sung các khoá UI cần từ kết quả phẳng của lõi. Không ghi đè khoá đã có (backend giả đã đúng hợp đồng)."""
    out = dict(res)
    out.setdefault("alert_summary", _alert_summary(alert) if alert is not None else {})
    out.setdefault("rule_severity", res.get("rule_bucket"))
    out.setdefault("action_target_ip", res.get("block_target"))
    out.setdefault("sop_alternatives", res.get("alternatives") or [])
    out.setdefault("sop_is_fallback", bool(res.get("sop_is_fallback", False)))
    out.setdefault("timings", {"t_retrieve": res.get("t_retrieve"), "t_llm": res.get("t_llm"),
                               "t_total": res.get("t_total"),
                               "prompt_eval_count": res.get("prompt_eval_count"),
                               "eval_count": res.get("eval_count")})
    out.setdefault("meta", {"model": res.get("model"), "prompt_version": res.get("prompt_version"),
                            "threshold": res.get("threshold"), "retrieval_mode": res.get("retrieval_mode")})
    title, sections = _sop_info(res.get("sop_id"))
    if not out.get("attack_type"):
        out["attack_type"] = title or ("Chưa phân loại" if res.get("ok", not res.get("error")) else "")
    if not out.get("summary"):
        out["summary"] = res.get("reasoning") or ""
    if not out.get("report_md") and not res.get("error"):
        parts = ["_Báo cáo ghép từ lập luận của mô hình và nội dung SOP đã truy xuất; chưa có bước sinh báo cáo riêng._", ""]
        if res.get("reasoning"):
            parts += ["## Lập luận của mô hình", res["reasoning"], ""]
        for head in ("Cách xác minh", "Ngăn chặn"):
            if sections.get(head):
                parts += [f"## {head} (trích SOP)", sections[head], ""]
        out["report_md"] = "\n".join(parts).strip()
    out.setdefault("ok", not res.get("error"))
    return out


def health() -> dict:
    """Trạng thái Ollama, luôn trả về dict đủ khoá."""
    out = {"ok": False, "version": None, "models": [], "error": None}
    try:
        h = _llm.health() if _REAL else mock_backend.health()
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out
    if isinstance(h, bool):
        out["ok"] = h
    elif isinstance(h, dict):
        out["ok"] = bool(h.get("ok", h.get("online", False)))
        out["version"] = h.get("version")
        models = h.get("models") or []
        out["models"] = [m if isinstance(m, str) else str(m.get("name", m)) if isinstance(m, dict) else str(m) for m in models]
        out["error"] = h.get("error")
    return out


def analyze(alert: dict, model: Optional[str], mode: str, threshold: float) -> dict:
    """Luôn trả về dict; không ném exception (lỗi nằm trong result['error'])."""
    try:
        if _REAL:
            res = _analyze_alert(alert, model=model, threshold=threshold, retrieval=mode)
            return to_contract(to_dict(res), alert)
        return mock_backend.analyze(alert, model or "mock-model", mode, threshold)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "attack_type": "", "guard_notes": [],
                "meta": {"model": model, "retrieval_mode": mode}}
