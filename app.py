from __future__ import annotations

import html
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from agents import DataControlAgent, RiskCommunicationAgent, RiskReviewAgent, build_review_packet
from reporting import create_html_report
from risk_engine import calculate_risk, load_inputs


ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Portfolio Risk Copilot", page_icon=":material/monitoring:", layout="wide")
# Scoped presentation styles; chart values and the calculation engine are unchanged.
st.html("""
<style>
.risk-kicker {color:#0C706F;font-size:.72rem;font-weight:700;letter-spacing:.16em;margin:0 0 .5rem;}
.risk-intro {color:#566A7C;max-width:760px;font-size:1rem;line-height:1.6;margin:0 0 .6rem;}
.risk-meta {color:#566A7C;font-size:.78rem;line-height:1.6;}
.risk-summary {display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding:1rem 1.2rem;border:1px solid #E6C6B8;border-left:4px solid #AE4727;border-radius:8px;background:#FFF6F1;margin:.6rem 0;}
.risk-summary strong {color:#8F361B;font-size:1rem;}
.risk-summary span {color:#6D493A;font-size:.85rem;}
.risk-summary.clear {border-color:#BAD6CF;border-left-color:#0C706F;background:#F0F8F5;}
.risk-summary.clear strong,.risk-summary.clear span {color:#0C625D;}
.risk-metrics {padding:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:.5rem 0 1.3rem;}
.risk-metric {min-width:0;padding:17px 16px;background:#FFF;border:1px solid #DFE6EC;border-radius:8px;}
.risk-metric dt {font-size:.78rem;font-weight:600;color:#42586A;line-height:1.45;min-height:2.25em;}
.risk-metric dd {margin:6px 0;font-size:1.85rem;letter-spacing:-.04em;font-weight:650;font-variant-numeric:tabular-nums;color:#102A43;}
.risk-metric small {font-size:.7rem;color:#617487;line-height:1.4;display:block;}
.risk-metric.loss {border-top:3px solid #AE4727;padding-top:15px;}
.risk-metric.loss dd {color:#9C3F24;}
@media(max-width:1050px) {.risk-metrics {grid-template-columns:repeat(3,minmax(0,1fr));}}
@media(max-width:600px) {.risk-metrics {grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:1rem;} .risk-metric {padding:12px;} .risk-metric dt {min-height:0;font-size:.74rem;} .risk-metric dd {font-size:1.6rem;margin:4px 0;} .risk-metric:last-child {grid-column:span 2;display:grid;grid-template-columns:1fr 1fr;align-items:center;} .risk-metric:last-child dd {grid-column:2;grid-row:1 / span 2;text-align:right;} .risk-metric:last-child small {grid-column:1;} .risk-summary {padding:.75rem;gap:.35rem;} }
</style>
""")


def _load_uploaded_inputs():
    with st.sidebar:
        st.header("Analysis inputs")
        st.caption("Use the bundled portfolio or upload three files with the documented schema.")
        use_demo = st.toggle("Use demonstration portfolio", value=True, key="use_demo")
        portfolio_file = st.file_uploader("Portfolio CSV", type="csv", disabled=use_demo)
        prices_file = st.file_uploader("Market prices CSV", type="csv", disabled=use_demo)
        scenarios_file = st.file_uploader("Stress scenarios CSV", type="csv", disabled=use_demo)
        st.caption("INPUT CONTRACT · THREE CSV FILES")
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


st.html('<p class="risk-kicker">MULTI-ASSET RISK / DAILY REVIEW</p>')
st.title("Portfolio Risk Copilot")
st.html('<p class="risk-intro">Understand the exposure. Identify the exceptions. Prepare the risk brief.</p>')

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

high_findings = [finding for finding in findings if finding.priority == "HIGH"]
data_label = "Synthetic demonstration data" if st.session_state.use_demo else "Uploaded portfolio data"
st.html(f'<p class="risk-meta">{data_label} · As of {metrics["as_of_date"]} · Daily loss horizon</p>')
st.markdown(
    f':green-badge[:material/check_circle: {control_review["passed_checks"]}/{control_review["total_checks"]} input controls passed] '
    ':gray-badge[Draft · human review required]'
)
if high_findings:
    summary_title = f"{len(high_findings)} high-priority findings require review"
    summary_detail = " · ".join(finding.title for finding in high_findings)
else:
    summary_title = "No high-priority findings"
    summary_detail = "Review the queue before approving the draft brief."
st.html(
    f'<div class="risk-summary {"" if high_findings else "clear"}">'
    f'<strong>{html.escape(summary_title)}</strong><span>{html.escape(summary_detail)}</span></div>'
)
cards = [
    ("Portfolio NAV", f"${metrics['nav']/1_000_000:.2f}M", "Current position value", ""),
    ("Annualized volatility", f"{metrics['annualized_volatility']:.1%}", "252 trading days", ""),
    ("Historical VaR", f"{metrics['historical_var_95']:.2%}", "1 day · 95% confidence", ""),
    ("Expected Shortfall", f"{metrics['expected_shortfall_95']:.2%}", "1 day · 95% tail", ""),
    ("Worst stress", f"{metrics['worst_stress_return']:.1%}", metrics["worst_stress_scenario"], "loss"),
]
st.html('<dl class="risk-metrics">' + ''.join(
    f'<div class="risk-metric {tone}"><dt>{label}</dt><dd>{value}</dd><small>{html.escape(detail)}</small></div>'
    for label, value, detail, tone in cards
) + '</dl>')

overview, exposures, stress_tab, monitoring, governance = st.tabs(
    ["Decision brief", "Exposure map", "Stress testing", "Model monitoring", "Controls & governance"]
)

with overview:
    st.subheader("Daily risk brief")
    with st.container(border=True):
        st.markdown(narrative)
        st.caption("Deterministic commentary from the validated evidence packet. Optional LLM narration is available in the source code.")
    st.subheader("Prioritized review queue")
    for finding in sorted(findings, key=lambda item: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[item.priority]):
        icon = ":material/error:" if finding.priority == "HIGH" else ":material/info:"
        with st.expander(f"{finding.priority} · {finding.title}", icon=icon, expanded=finding.priority == "HIGH"):
            st.write(finding.explanation)
            st.markdown(f"**Analyst action:** {finding.action}")
            st.caption("Evidence: " + ", ".join(finding.evidence_refs))

with exposures:
    left, right = st.columns([1.35, 1])
    contribution_view = bundle.contributions.set_index("ticker")[["weight", "risk_contribution"]]
    contribution_view.columns = ["Portfolio weight", "Risk contribution"]
    left.subheader("Weight versus risk contribution")
    contribution_data = contribution_view.reset_index().melt("ticker", var_name="Series", value_name="Share")
    contribution_chart = alt.Chart(contribution_data).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y("ticker:N", title=None, sort=bundle.contributions.sort_values("risk_contribution", ascending=False)["ticker"].tolist()),
        yOffset="Series:N",
        x=alt.X("Share:Q", title="Share of portfolio / volatility", axis=alt.Axis(format=".0%")),
        color=alt.Color("Series:N", scale=alt.Scale(domain=["Portfolio weight", "Risk contribution"], range=["#9EAFBF", "#0C706F"]), legend=alt.Legend(orient="top", title=None)),
        tooltip=[alt.Tooltip("ticker:N", title="Position"), "Series:N", alt.Tooltip("Share:Q", format=".1%")],
    ).properties(height=310)
    left.altair_chart(contribution_chart, width="stretch", alt="Portfolio weights compared with volatility contributions for each position")
    left.caption("Paired bars compare allocation with risk. Negative contributions indicate diversification in this model.")
    right.subheader("Factor sensitivities")
    factor_chart = alt.Chart(bundle.factor_exposures).mark_bar(color="#416A8A", cornerRadiusEnd=3).encode(
        y=alt.Y("factor:N", title=None, sort="-x"),
        x=alt.X("sensitivity:Q", title="Proxy-factor sensitivity (×)"),
        tooltip=[alt.Tooltip("factor:N", title="Factor"), alt.Tooltip("proxy:N", title="Proxy"), alt.Tooltip("sensitivity:Q", title="Sensitivity", format=".3f")],
    ).properties(height=310)
    right.altair_chart(factor_chart, width="stretch", alt="OLS sensitivities to equity, rates, credit, commodity and USD proxy returns")
    right.caption("OLS proxy sensitivities, not percentage portfolio weights.")
    st.subheader("Position detail")
    st.dataframe(bundle.contributions, width="stretch", hide_index=True, alt="Position weights, risk contributions, betas and limit status", column_config={
        "ticker": st.column_config.TextColumn("Position", pinned=True),
        "asset_class": "Asset class", "market_value": st.column_config.NumberColumn("Market value", format="dollar", step=1),
        "weight": st.column_config.NumberColumn("Weight", format="percent", step=.001),
        "limit_weight": st.column_config.NumberColumn("Weight limit", format="percent", step=.001),
        "annualized_volatility": st.column_config.NumberColumn("Annualized volatility", format="percent", step=.001),
        "risk_contribution": st.column_config.NumberColumn("Risk contribution", format="percent", step=.001),
        "market_beta": st.column_config.NumberColumn("Market beta", format="%.2f"), "weight_limit_status": "Limit status",
    })

with stress_tab:
    st.subheader("Stress scenario impact")
    st.caption("Hypothetical shocks applied to current asset-class weights. These are scenarios, not forecasts.")
    stress_chart = alt.Chart(bundle.stresses).mark_bar(color="#AE4727", cornerRadiusEnd=3).encode(
        y=alt.Y("scenario:N", title=None, sort="x"),
        x=alt.X("portfolio_return:Q", title="Portfolio return", axis=alt.Axis(format=".0%")),
        tooltip=[alt.Tooltip("scenario:N", title="Scenario"), alt.Tooltip("portfolio_return:Q", title="Return", format=".1%"), alt.Tooltip("pnl:Q", title="P&L", format="$,.0f")],
    ).properties(height=280)
    st.altair_chart(stress_chart, width="stretch", alt="Estimated portfolio return under each hypothetical stress scenario")
    st.dataframe(bundle.stresses, width="stretch", hide_index=True, alt="Stress scenario returns and dollar profit or loss", column_config={
        "scenario": "Scenario", "portfolio_return": st.column_config.NumberColumn("Portfolio return", format="percent", step=.001),
        "pnl": st.column_config.NumberColumn("Estimated P&L", format="dollar", step=1),
    })

with monitoring:
    st.subheader("Rolling 95% historical VaR backtest")
    st.caption("250-day trailing window · one-day horizon · historical 95% VaR. Each estimate uses prior observations only.")
    chart_data = bundle.backtest.copy()
    chart_data["VaR loss threshold"] = -chart_data["var_95"]
    chart_data = chart_data.rename(columns={"realized_return": "Realized return"})
    lines = alt.Chart(chart_data.melt("date", value_vars=["Realized return", "VaR loss threshold"], var_name="Series", value_name="Return")).mark_line(strokeWidth=1.5).encode(
        x=alt.X("date:T", title=None), y=alt.Y("Return:Q", title="Daily return", axis=alt.Axis(format=".0%")),
        color=alt.Color("Series:N", scale=alt.Scale(domain=["Realized return", "VaR loss threshold"], range=["#416A8A", "#AE4727"]), legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("date:T", title="Date"), "Series:N", alt.Tooltip("Return:Q", format=".2%")],
    )
    exception_dots = alt.Chart(chart_data[chart_data["exception"]]).mark_circle(color="#AE4727", size=45).encode(x="date:T", y="Realized return:Q", tooltip=[alt.Tooltip("date:T", title="Exception date"), alt.Tooltip("Realized return:Q", format=".2%")])
    st.altair_chart((lines + exception_dots).properties(height=300), width="stretch", alt="Daily returns and historical VaR threshold, with exceptions marked as dots")
    a, b, c = st.columns(3)
    a.metric("Out-of-sample days", metrics["var_backtest_observations"])
    b.metric("VaR exceptions", metrics["var_backtest_exceptions"])
    c.metric("Exception rate", f"{metrics['var_backtest_exception_rate']:.1%}")
    exceptions = bundle.backtest[bundle.backtest["exception"]]
    st.caption("Exception log")
    st.dataframe(exceptions, width="stretch", hide_index=True, alt="Dates when realized losses exceeded the prior-day VaR estimate", column_config={
        "date": st.column_config.DateColumn("Exception date", format="YYYY-MM-DD"),
        "realized_return": st.column_config.NumberColumn("Realized return", format="percent", step=.0001),
        "var_95": st.column_config.NumberColumn("VaR estimate", format="percent", step=.0001), "exception": "Exception",
    })
    st.caption("PASS is the existing demonstration rule: exception rate ≤ 7.5%. It is not a regulatory model-validation verdict.")

with governance:
    left, right = st.columns(2)
    left.subheader("Input controls")
    left.dataframe(pd.DataFrame(bundle.controls).rename(columns={"check": "Control", "status": "Status", "evidence": "Evidence"}), width="stretch", hide_index=True, alt="Input validation controls and supporting evidence")
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
            icon=":material/download:",
        )


st.caption("Portfolio demonstration · VaR and Expected Shortfall are estimates, not maximum-loss forecasts. Human review is required before distribution.")
