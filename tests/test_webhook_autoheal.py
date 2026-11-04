import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import webhook_autoheal as w  # noqa: E402


def alert(name="PodCrashLooping", status="firing", ns="shop", dep="checkout"):
    return {"status": status, "labels": {"alertname": name, "namespace": ns, "deployment": dep}}


class DecideTests(unittest.TestCase):
    def test_allowed_alert_builds_command(self):
        cmd, reason = w.decide(alert(), 1000, {})
        self.assertEqual(reason, "allowed")
        self.assertEqual(cmd, ["kubectl", "rollout", "restart", "deployment/checkout", "-n", "shop"])

    def test_resolved_alert_ignored(self):
        self.assertIsNone(w.decide(alert(status="resolved"), 1000, {})[0])

    def test_unknown_alert_ignored(self):
        self.assertIsNone(w.decide(alert(name="SomethingElse"), 1000, {})[0])

    def test_cooldown(self):
        last = {}
        self.assertIsNotNone(w.decide(alert(), 1000, last)[0])
        self.assertEqual(w.decide(alert(), 1100, last), (None, "cooldown active"))
        self.assertIsNotNone(w.decide(alert(), 1000 + w.COOLDOWN_SEC + 1, last)[0])

    def test_rejects_injection(self):
        cmd, reason = w.decide(alert(dep="x; rm -rf /"), 1000, {})
        self.assertIsNone(cmd)
        self.assertIn("invalid", reason)


if __name__ == "__main__":
    unittest.main()
