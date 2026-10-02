"""Lớp chuyển đổi ui.backend.to_contract: kết quả phẳng của lõi (Bình) -> khoá mà UI/storage đọc."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["SOC_COPILOT_UI_MOCK"] = "1"
sys.path.insert(0, ROOT)

from ui import backend  # noqa: E402

ALERT = {"rule": {"id": "5712", "level": 10, "description": "sshd: brute force",
                  "groups": ["sshd"], "mitre": {"id": ["T1110"]}},
         "agent": {"name": "web01"}, "data": {"srcip": "203.0.113.7"}, "full_log": "Failed password"}

CORE = {  # đúng tên khoá của soc_copilot.models.AnalysisResult
    "severity": "High", "recommended_action": "BLOCK_IP", "reasoning": "Nhiều lần SSH thất bại.",
    "report_md": None, "sop_id": "sop_ssh_bruteforce", "sop_distance": 0.21, "margin": 0.1,
    "alternatives": [{"sop_id": "sop_general", "distance": 0.5}], "sop_is_fallback": False,
    "block_target": "203.0.113.7", "needs_human_confirm": False, "rule_bucket": "High",
    "severity_mismatch": False, "suspected_injection": False, "guard_notes": [],
    "model": "qwen2.5:7b", "prompt_version": "v1", "threshold": 0.45, "retrieval_mode": "rag",
    "prompt_eval_count": 900, "eval_count": 80, "truncated": False,
    "t_retrieve": 0.05, "t_llm": 3.2, "t_total": 3.3, "error": None,
}


class ContractTest(unittest.TestCase):
    def test_maps_core_keys_to_ui_keys(self):
        c = backend.to_contract(dict(CORE), ALERT)
        self.assertEqual(c["rule_severity"], "High")
        self.assertEqual(c["action_target_ip"], "203.0.113.7")
        self.assertEqual(c["sop_alternatives"], CORE["alternatives"])
        self.assertEqual(c["timings"]["t_llm"], 3.2)
        self.assertEqual(c["meta"]["model"], "qwen2.5:7b")
        self.assertEqual(c["meta"]["retrieval_mode"], "rag")
        self.assertEqual(c["summary"], "Nhiều lần SSH thất bại.")
        self.assertTrue(c["ok"])

    def test_alert_summary_and_report(self):
        c = backend.to_contract(dict(CORE), ALERT)
        self.assertEqual(c["alert_summary"]["rule_id"], "5712")
        self.assertEqual(c["alert_summary"]["srcip"], "203.0.113.7")
        self.assertTrue(c["attack_type"])
        self.assertIn("Lập luận của mô hình", c["report_md"])
        self.assertIn("Cách xác minh", c["report_md"])      # trích từ data/sops/sop_ssh_bruteforce.md

    def test_error_result_keeps_ok_false(self):
        c = backend.to_contract({"error": "Ollama chưa chạy", "guard_notes": []}, ALERT)
        self.assertFalse(c["ok"])
        self.assertFalse(c.get("report_md"))

    def test_does_not_overwrite_existing_contract_keys(self):
        mock = backend.mock_backend.analyze(ALERT, "m", "rule_map", 0.45)
        c = backend.to_contract(dict(mock), ALERT)
        self.assertEqual(c["rule_severity"], mock["rule_severity"])
        self.assertEqual(c["timings"], mock["timings"])

    def test_sop_id_is_not_a_path(self):
        self.assertEqual(backend._sop_info("../../etc/passwd"), ("", {}))


if __name__ == "__main__":
    unittest.main()
