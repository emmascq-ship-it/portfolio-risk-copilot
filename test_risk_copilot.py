from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from agents import DataControlAgent, RiskReviewAgent, build_review_packet
from generate_demo_data import main as generate_demo_data
from risk_engine import calculate_risk, load_inputs, validate_inputs


ROOT = Path(__file__).resolve().parent


class RiskCopilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        generate_demo_data()
        cls.portfolio, cls.prices, cls.scenarios = load_inputs(ROOT / "sample_inputs")

    def test_controls_pass_for_demo(self) -> None:
        checks = validate_inputs(self.portfolio, self.prices, self.scenarios)
        self.assertTrue(all(check["status"] == "PASS" for check in checks))

    def test_metrics_are_economically_valid(self) -> None:
        bundle = calculate_risk(self.portfolio, self.prices, self.scenarios)
        self.assertGreater(bundle.metrics["nav"], 0)
        self.assertGreater(bundle.metrics["annualized_volatility"], 0)
        self.assertGreater(bundle.metrics["expected_shortfall_95"], bundle.metrics["historical_var_95"])
        self.assertAlmostEqual(bundle.contributions["risk_contribution"].sum(), 1.0, places=8)
        self.assertGreater(bundle.metrics["var_backtest_observations"], 0)
        self.assertEqual(len(bundle.factor_exposures), 5)

    def test_backtest_uses_prior_window_and_flags_exceptions(self) -> None:
        bundle = calculate_risk(self.portfolio, self.prices, self.scenarios)
        self.assertEqual(len(bundle.backtest), len(bundle.returns) - 250)
        self.assertTrue((bundle.backtest["var_95"] > 0).all())
        self.assertEqual(
            bundle.metrics["var_backtest_exceptions"],
            int(bundle.backtest["exception"].sum()),
        )

    def test_missing_price_series_blocks_calculation(self) -> None:
        prices = self.prices.drop(columns=["QQQ"])
        with self.assertRaises(ValueError):
            calculate_risk(self.portfolio, prices, self.scenarios)

    def test_agent_packet_preserves_calculated_metrics(self) -> None:
        bundle = calculate_risk(self.portfolio, self.prices, self.scenarios)
        control = DataControlAgent().review(bundle)
        findings = RiskReviewAgent().review(bundle)
        packet = build_review_packet(bundle, control, findings)
        self.assertEqual(packet["metrics"], bundle.metrics)
        self.assertEqual(control["status"], "READY")
        self.assertGreaterEqual(len(findings), 3)
        self.assertEqual(len(packet["factor_exposures"]), 5)


if __name__ == "__main__":
    unittest.main()

