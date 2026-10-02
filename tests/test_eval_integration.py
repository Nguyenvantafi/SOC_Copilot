"""Bộ eval (Đức) phải đo đúng hệ thống thật (Bình/Tài): cấu hình guard, ngữ cảnh rule_map, metric truy xuất SOP."""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from soc_copilot import config  # noqa: E402
from soc_copilot.guard import apply_guard  # noqa: E402
import eval_context  # noqa: E402
import metrics  # noqa: E402


class ProtectedIpTest(unittest.TestCase):
    def test_adversarial_protected_ips_are_in_config(self):
        for name in ("12_srcip_matches_protected_ip.json", "13_bruteforce_from_protected_ip.json"):
            alert = json.loads((ROOT / "data" / "adversarial" / name).read_text(encoding="utf-8"))
            ip = alert["data"]["srcip"]
            self.assertIn(ip, config.PROTECTED_IPS, name)
            g = apply_guard(alert, "High", "BLOCK_IP")
            self.assertEqual(g.action, "REVIEW_LOG", name)
            self.assertIsNone(g.block_target, name)


class EvalContextTest(unittest.TestCase):
    def test_rule_map_context_contains_sop_text_not_only_id(self):
        ctx = eval_context.get_context({"rule": {"id": "5712"}}, "rule_map", ROOT / "data" / "sops")
        self.assertIn("sop_ssh_bruteforce", ctx)
        self.assertIn("Cách xác minh", ctx)

    def test_rule_map_unknown_rule_falls_back_to_general(self):
        ctx = eval_context.get_context({"rule": {"id": "999999"}}, "rule_map", ROOT / "data" / "sops")
        self.assertIn("sop_general", ctx)


class RetrievalMetricsTest(unittest.TestCase):
    def rec(self, ref, top, final, fallback=False, llm="BLOCK_IP", act="REVIEW_LOG", inj=False):
        return {"alert_ref": ref, "model": "m", "mode": "rag", "error": None, "latency_seconds": 1.0,
                "call_index_in_run": 2,
                "parsed_output": {"sop_id": final, "sop_is_fallback": fallback,
                                  "retrieved_top": [{"sop_id": t, "distance": 0.1} for t in top],
                                  "guard_notes": [], "llm_action": llm, "recommended_action": act,
                                  "suspected_injection": inj}}

    def test_hit_at_k_fallback_and_guard(self):
        labels = {"a": {"expected_sop": "sop_xss"}, "b": {"expected_sop": "sop_general"},
                  "c": {"expected_sop": "sop_sqli"}}
        recs = [self.rec("a", ["sop_xss", "sop_sqli", "sop_general"], "sop_xss"),
                self.rec("b", ["sop_ddos", "sop_general", "sop_xss"], "sop_general", fallback=True, inj=True),
                self.rec("c", ["sop_xss", "sop_sqli", "sop_general"], "sop_xss")]
        m = metrics.compute_group_metrics(recs, labels)
        self.assertEqual((m["sop_hit_at_1"]["k"], m["sop_hit_at_1"]["n"]), (1, 3))
        self.assertEqual((m["sop_hit_at_3"]["k"], m["sop_hit_at_3"]["n"]), (3, 3))
        self.assertEqual((m["fallback_used"]["k"], m["fallback_correct"]["k"]), (1, 1))
        self.assertEqual(m["guard_changed_action"]["k"], 3)
        self.assertEqual(m["suspected_injection_flagged"]["k"], 1)

    def test_no_labels_means_zero_not_invented(self):
        m = metrics.compute_group_metrics([self.rec("a", ["sop_xss"], "sop_xss")], {"a": {}})
        self.assertEqual(m["sop_hit_at_1"]["n"], 0)


if __name__ == "__main__":
    unittest.main()
