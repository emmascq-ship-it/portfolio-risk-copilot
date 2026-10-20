from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from agents import DataControlAgent, RiskCommunicationAgent, RiskReviewAgent, build_review_packet
from reporting import create_html_report
from risk_engine import calculate_risk, load_inputs


ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Portfolio Risk Copilot", page_icon="◆", layout="wide")
st.markdown(
    """
    <style>
    :root {--navy:#102A43;--teal:#168C8C;--coral:#E36B4F;--paper:#F5F7F8;}
    .stApp {background:var(--paper); color:#243746;}
    .block-container {max-width:1240px; padding-top:2.2rem;}
    h1,h2,h3 {color:var(--navy); letter-spacing:-.02em;}
    div[data-testid="stMetric"] {background:white;border:1px solid #DCE3E8;border-radius:12px;padding:16px;}
    .hero {padding:22px 0 10px 0;}
    .eyebrow {color:var(--teal);font-size:.75rem;font-weight:800;letter-spacing:.14em;}
    .subtle {color:#607383;max-width:820px;line-height:1.55;}
    .decision {background:#E8F3F2;border-left:4px solid var(--teal);padding:17px 19px;border-radius:7px;line-height:1.55;}
    .warning {background:#FFF0EC;border-left:4px solid var(--coral);padding:14px 17px;border-radius:7px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _load_uploaded_inputs():
    with st.sidebar:
        st.header("Analysis inputs")
        st.caption("Use the bundled portfolio or upload three files with the documented schema.")
        use_demo = st.toggle("Use demonstration portfolio", value=True)
        portfolio_file = st.file_uploader("Portfolio CSV", type="csv", disabled=use_demo)
        prices_file = st.file_uploader("Market prices CSV", type="csv", disabled=use_demo)
        scenarios_file = st.file_uploader("Stress scenarios CSV", type="csv", disabled=use_demo)
        st.divider()
        st.caption("Demo data are deterministic and synthetic. Results are analytical estimates, not investment advice.")
    if use_demo:
        return load_inputs(ROOT / "sample_inputs")
    if not all([portfolio_file, prices_file, scenarios_file]):
        st.info("Upload all three input files to run a custom analysis.")
        st.stop()
    portfolio = pd.read_csv(portfolio_file)
    prices = pd.read_csv(prices_file, parse_dates=["date"]).set_index("date")
    scenarios = pd.read_csv(scenarios_file)
    return portfolio, prices, scenarios


st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">MULTI-ASSET RISK · CONTROLLED AI WORKFLOW</div>
      <h1>Portfolio Risk Copilot</h1>
      <p class="subtle">A reviewer-facing workspace for exposure diagnostics, loss estimation,
      stress testing, model monitoring and evidence-grounded risk communication.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    portfolio, prices, scenarios = _load_uploaded_inputs()
    bundle = calculate_risk(portfolio, prices, scenarios)
except Exception as exc:
    st.error(f"Risk calculation blocked: {exc}")
    st.stop()

control_review = DataControlAgent().review(bundle)
findings = RiskReviewAgent().review(bundle)
packet = build_review_packet(bundle, control_review, findings)
narrative = RiskCommunicationAgent().draft(packet)
metrics = bundle.metrics

status_colour = "#168C8C" if control_review["status"] == "READY" else "#E36B4F"
st.markdown(
    f"<span style='color:{status_colour};font-weight:800'>● {control_review['status']}</span> &nbsp; "
    f"<span style='color:#607383'>As of {metrics['as_of_date']} · {control_review['passed_checks']}/{control_review['total_checks']} controls passed</span>",
    unsafe_allow_html=True,
)

cols = st.columns(5)
cards = [
    ("Portfolio NAV", f"${metrics['nav']/1_000_000:.2f}M"),
    ("Annualized volatility", f"{metrics['annualized_volatility']:.1%}"),
    ("Historical VaR · 95%", f"{metrics['historical_var_95']:.2%}"),
    ("Expected Shortfall · 95%", f"{metrics['expected_shortfall_95']:.2%}"),
    ("Worst stress", f"{metrics['worst_stress_return']:.1%}"),
]
for column, (label, value) in zip(cols, cards):
    column.metric(label, value)

overview, exposures, stress_tab, monitoring, governance = st.tabs(
    ["Decision brief", "Exposure map", "Stress testing", "Model monitoring", "Controls & governance"]
)

with overview:
    st.subheader("Daily risk brief")
    st.markdown(f"<div class='decision'>{narrative}</div>", unsafe_allow_html=True)
    st.subheader("Prioritized review queue")
    for finding in findings:
        icon = "🔴" if finding.priority == "HIGH" else "🟠" if finding.priority == "MEDIUM" else "🟢"
        with st.expander(f"{icon} {finding.priority} · {finding.title}", expanded=finding.priority == "HIGH"):
            st.write(finding.explanation)
            st.markdown(f"**Analyst action:** {finding.action}")
            st.caption("Evidence: " + ", ".join(finding.evidence_refs))

with exposures:
    left, right = st.columns([1.35, 1])
    contribution_view = bundle.contributions.set_index("ticker")[["weight", "risk_contribution"]]
    contribution_view.columns = ["Portfolio weight", "Risk contribution"]
    left.subheader("Weight versus risk contribution")
    left.bar_chart(contribution_view, color=["#9CB5C3", "#168C8C"])
    right.subheader("Factor sensitivities")
    factor_view = bundle.factor_exposures.set_index("factor")[["sensitivity"]]
    right.bar_chart(factor_view, color="#E36B4F")
    st.dataframe(
        bundle.contributions.style.format(
            {"market_value": "${:,.0f}", "weight": "{:.1%}", "annualized_volatility": "{:.1%}", "risk_contribution": "{:.1%}", "market_beta": "{:.2f}"}
        ),
        width="stretch",
        hide_index=True,
    )

with stress_tab:
    st.subheader("Scenario loss distribution")
    stress_view = bundle.stresses.set_index("scenario")[["portfolio_return"]]
    st.bar_chart(stress_view, color="#E36B4F")
    st.dataframe(
        bundle.stresses.style.format({"portfolio_return": "{:.1%}", "pnl": "${:,.0f}"}),
        width="stretch",
        hide_index=True,
    )

with monitoring:
    st.subheader("Rolling 95% historical VaR backtest")
    chart_data = bundle.backtest.set_index("date")[["realized_return", "var_95"]].copy()
    chart_data["VaR loss threshold"] = -chart_data.pop("var_95")
    st.line_chart(chart_data, color=["#547087", "#E36B4F"])
    a, b, c = st.columns(3)
    a.metric("Out-of-sample days", metrics["var_backtest_observations"])
    b.metric("VaR exceptions", metrics["var_backtest_exceptions"])
    c.metric("Exception rate", f"{metrics['var_backtest_exception_rate']:.1%}")
    exceptions = bundle.backtest[bundle.backtest["exception"]]
    st.caption("Exception log")
    st.dataframe(exceptions, width="stretch", hide_index=True)

with governance:
    left, right = st.columns(2)
    left.subheader("Input controls")
    left.dataframe(pd.DataFrame(bundle.controls), width="stretch", hide_index=True)
    right.subheader("Governance boundary")
    right.markdown(
        """
        - Deterministic code owns positions, prices, metrics, limits and pass/fail status.
        - The communication agent receives only the validated evidence packet.
        - AI may summarize results but cannot alter calculated values.
        - A human reviewer remains accountable for approval and escalation.
        """
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = Path(temp_dir) / "risk_brief.html"
        create_html_report(bundle, findings, narrative, report_path)
        st.download_button(
            "Download draft risk brief",
            report_path.read_bytes(),
            file_name="portfolio_risk_brief.html",
            mime="text/html",
            type="primary",
        )

