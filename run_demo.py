from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents import DataControlAgent, RiskCommunicationAgent, RiskReviewAgent, build_review_packet
from reporting import create_backtest_chart, create_dashboard, create_html_report
from risk_engine import calculate_risk, load_inputs


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "sample_inputs")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--approve", action="store_true", help="Create an approved copy after explicit analyst review")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    portfolio, prices, scenarios = load_inputs(args.input)
    bundle = calculate_risk(portfolio, prices, scenarios)
    control_review = DataControlAgent().review(bundle)
    if control_review["status"] != "READY":
        raise SystemExit("Risk workflow blocked by failed controls")
    findings = RiskReviewAgent().review(bundle)
    packet = build_review_packet(bundle, control_review, findings)
    narrative = RiskCommunicationAgent().draft(packet)

    (args.output / "risk_metrics.json").write_text(json.dumps(bundle.metrics, indent=2), encoding="utf-8")
    (args.output / "risk_review_packet.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    bundle.factor_exposures.to_csv(args.output / "factor_exposures.csv", index=False)
    bundle.backtest.to_csv(args.output / "var_backtest.csv", index=False)
    create_dashboard(bundle, args.output / "risk_dashboard.png")
    create_backtest_chart(bundle, args.output / "var_backtest.png")
    create_html_report(bundle, findings, narrative, args.output / "risk_brief.html")
    if args.approve:
        create_html_report(bundle, findings, narrative, args.output / "approved_risk_brief.html", approved=True)
    print(json.dumps({"status": "READY", "output": str(args.output), "metrics": bundle.metrics}, indent=2))


if __name__ == "__main__":
    main()

