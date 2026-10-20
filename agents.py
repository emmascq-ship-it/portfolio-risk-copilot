from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

import pandas as pd

from risk_engine import RiskBundle


@dataclass
class ReviewFinding:
    priority: str
    title: str
    explanation: str
    evidence_refs: list[str]
    action: str


class DataControlAgent:
    """Allows downstream review only when deterministic input controls pass."""

    def review(self, bundle: RiskBundle) -> dict[str, Any]:
        failed = [c for c in bundle.controls if c["status"] != "PASS"]
        return {
            "status": "BLOCKED" if failed else "READY",
            "failed_checks": failed,
            "passed_checks": len(bundle.controls) - len(failed),
            "total_checks": len(bundle.controls),
        }


class RiskReviewAgent:
    """Ranks deterministic results without changing any calculated value."""

    def review(self, bundle: RiskBundle) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        metrics = bundle.metrics
        worst = bundle.stresses.iloc[0]
        top_risk = bundle.contributions.sort_values("risk_contribution", ascending=False).iloc[0]
        breaches = bundle.contributions[bundle.contributions["weight_limit_status"] == "BREACH"]
        backtest_status = metrics["var_backtest_status"]

        findings.append(
            ReviewFinding(
                "HIGH" if worst["portfolio_return"] <= -0.12 else "MEDIUM",
                f"Worst scenario: {worst['scenario']}",
                f"The scenario produces an estimated portfolio loss of {worst['portfolio_return']:.1%} (${abs(worst['pnl']):,.0f}).",
                ["stress.worst", "metric.worst_stress_return"],
                "Review scenario concentration and confirm escalation tolerance.",
            )
        )
        findings.append(
            ReviewFinding(
                "MEDIUM",
                f"Largest risk contributor: {top_risk['ticker']}",
                f"{top_risk['ticker']} contributes {top_risk['risk_contribution']:.1%} of modelled volatility versus a {top_risk['weight']:.1%} portfolio weight.",
                [f"position.{top_risk['ticker']}.risk_contribution", f"position.{top_risk['ticker']}.weight"],
                "Assess whether the exposure is intentional and compensated by expected return.",
            )
        )
        if len(breaches):
            names = ", ".join(breaches["ticker"])
            findings.append(
                ReviewFinding(
                    "HIGH", "Position limit breach", f"The following positions exceed configured weight limits: {names}.",
                    [f"position.{ticker}.weight_limit_status" for ticker in breaches["ticker"]],
                    "Escalate the breach or document an approved temporary exception.",
                )
            )
        else:
            findings.append(
                ReviewFinding(
                    "LOW", "Position limits", "All position weights remain within the configured demonstration limits.",
                    ["control.position_limits"], "No immediate limit action; continue monitoring.",
                )
            )
        findings.append(
            ReviewFinding(
                "MEDIUM" if metrics["historical_var_95"] > 0.02 else "LOW",
                "One-day loss estimate",
                f"Historical 95% VaR is {metrics['historical_var_95']:.2%} of NAV and 95% Expected Shortfall is {metrics['expected_shortfall_95']:.2%}.",
                ["metric.historical_var_95", "metric.expected_shortfall_95"],
                "Compare with the approved risk appetite and investigate material changes.",
            )
        )
        findings.append(
            ReviewFinding(
                "LOW" if backtest_status == "PASS" else "MEDIUM",
                f"VaR backtest: {backtest_status}",
                f"The rolling 95% historical VaR produced {metrics['var_backtest_exceptions']} exceptions "
                f"across {metrics['var_backtest_observations']} out-of-sample observations "
                f"({metrics['var_backtest_exception_rate']:.1%}).",
                ["metric.var_backtest_exceptions", "metric.var_backtest_exception_rate"],
                "Review exception dates and model assumptions if the exception rate exceeds tolerance.",
            )
        )
        return findings


def build_review_packet(bundle: RiskBundle, control_review: dict[str, Any], findings: list[ReviewFinding]) -> dict[str, Any]:
    position_records = []
    for row in bundle.contributions.to_dict(orient="records"):
        position_records.append({k: _clean_value(v) for k, v in row.items()})
    stress_records = []
    for row in bundle.stresses.to_dict(orient="records"):
        stress_records.append({k: _clean_value(v) for k, v in row.items()})
    factor_records = []
    for row in bundle.factor_exposures.to_dict(orient="records"):
        factor_records.append({k: _clean_value(v) for k, v in row.items()})
    return {
        "purpose": "Draft a daily portfolio-risk brief from validated calculations only.",
        "calculation_boundary": "Narration may summarize but may not change inputs, calculations, limits, or statuses.",
        "control_review": control_review,
        "metrics": bundle.metrics,
        "positions": position_records,
        "stress_results": stress_records,
        "factor_exposures": factor_records,
        "ranked_findings": [finding.__dict__ for finding in findings],
        "required_disclosures": [
            "Demo market history is deterministic and synthetic.",
            "VaR and Expected Shortfall are model estimates, not maximum-loss forecasts.",
            "Human approval is required before distribution.",
        ],
    }


def _clean_value(value: Any) -> Any:
    if isinstance(value, (np_integer := __import__("numpy").integer, __import__("numpy").floating)):
        return value.item()
    return value


class RiskCommunicationAgent:
    def draft(self, packet: dict[str, Any]) -> str:
        if os.getenv("RISK_COPILOT_USE_LLM") == "1" and os.getenv("OPENAI_API_KEY"):
            return self._draft_with_llm(packet)
        return self._deterministic_draft(packet)

    def _deterministic_draft(self, packet: dict[str, Any]) -> str:
        metrics = packet["metrics"]
        findings = packet["ranked_findings"]
        lead = findings[0]
        return (
            f"Portfolio risk review as of {metrics['as_of_date']}. The portfolio has annualized volatility of "
            f"{metrics['annualized_volatility']:.1%}, historical 95% VaR of {metrics['historical_var_95']:.2%}, "
            f"and 95% Expected Shortfall of {metrics['expected_shortfall_95']:.2%}. "
            f"The priority scenario is {metrics['worst_stress_scenario']}, with an estimated impact of "
            f"{metrics['worst_stress_return']:.1%}. {lead['action']}"
        )

    def _draft_with_llm(self, packet: dict[str, Any]) -> str:
        payload = {
            "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            "input": [
                {"role": "system", "content": "Draft a concise risk-manager brief using only the supplied evidence. Never invent values. Preserve all disclosures."},
                {"role": "user", "content": json.dumps(packet)},
            ],
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read())
        text_parts = []
        for item in result.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    text_parts.append(content["text"])
        return "\n".join(text_parts) or self._deterministic_draft(packet)

