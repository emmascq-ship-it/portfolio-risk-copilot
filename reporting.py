from __future__ import annotations

import html
from pathlib import Path

import matplotlib.pyplot as plt

from agents import ReviewFinding
from risk_engine import RiskBundle


def create_dashboard(bundle: RiskBundle, path: Path) -> None:
    contrib = bundle.contributions.sort_values("risk_contribution", ascending=True)
    stress = bundle.stresses.sort_values("portfolio_return")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    fig.patch.set_facecolor("#F7F8FA")
    for ax in axes:
        ax.set_facecolor("#F7F8FA")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.grid(axis="x", alpha=0.18)
    axes[0].barh(contrib["ticker"], contrib["risk_contribution"], color="#159A9C")
    axes[0].set_title("Contribution to portfolio volatility", loc="left", weight="bold", color="#0F2A43")
    axes[0].xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    colors = ["#E56B4D" if value < 0 else "#159A9C" for value in stress["portfolio_return"]]
    axes[1].barh(stress["scenario"], stress["portfolio_return"], color=colors)
    axes[1].set_title("Portfolio stress return", loc="left", weight="bold", color="#0F2A43")
    axes[1].xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    fig.suptitle("Portfolio Risk Copilot · Daily Review", x=0.06, ha="left", fontsize=17, weight="bold", color="#0F2A43")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def create_backtest_chart(bundle: RiskBundle, path: Path) -> None:
    backtest = bundle.backtest.copy()
    fig, ax = plt.subplots(figsize=(13, 4.8))
    fig.patch.set_facecolor("#F7F8FA")
    ax.set_facecolor("#F7F8FA")
    ax.plot(backtest["date"], backtest["realized_return"], color="#547087", linewidth=1, label="Realized return")
    ax.plot(backtest["date"], -backtest["var_95"], color="#E56B4D", linewidth=1.7, label="95% VaR threshold")
    exceptions = backtest[backtest["exception"]]
    ax.scatter(exceptions["date"], exceptions["realized_return"], color="#B42318", s=28, zorder=3, label="Exception")
    ax.axhline(0, color="#0F2A43", linewidth=0.8, alpha=0.4)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", alpha=0.18)
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:.1%}")
    ax.set_title("Rolling historical VaR backtest", loc="left", fontsize=16, weight="bold", color="#0F2A43")
    ax.legend(frameon=False, ncol=3, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def create_html_report(bundle: RiskBundle, findings: list[ReviewFinding], narrative: str, path: Path, approved: bool = False) -> None:
    metrics = bundle.metrics
    status = "APPROVED" if approved else "DRAFT · HUMAN REVIEW REQUIRED"
    finding_rows = "".join(
        f"<tr><td><span class='badge {f.priority.lower()}'>{f.priority}</span></td><td><strong>{html.escape(f.title)}</strong><br><span>{html.escape(f.explanation)}</span></td><td>{html.escape(f.action)}</td></tr>"
        for f in findings
    )
    stress_rows = "".join(
        f"<tr><td>{html.escape(str(row.scenario))}</td><td>{row.portfolio_return:.1%}</td><td>${row.pnl:,.0f}</td></tr>"
        for row in bundle.stresses.itertuples()
    )
    position_rows = "".join(
        f"<tr><td>{row.ticker}</td><td>{row.asset_class}</td><td>{row.weight:.1%}</td><td>{row.risk_contribution:.1%}</td><td>{row.market_beta:.2f}</td><td>{row.weight_limit_status}</td></tr>"
        for row in bundle.contributions.sort_values("risk_contribution", ascending=False).itertuples()
    )
    factor_rows = "".join(
        f"<tr><td>{row.factor}</td><td>{row.proxy}</td><td>{row.sensitivity:.2f}</td></tr>"
        for row in bundle.factor_exposures.itertuples()
    )
    document = f"""<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Portfolio Risk Copilot</title><style>
:root{{--navy:#0f2a43;--teal:#159a9c;--coral:#e56b4d;--paper:#f7f8fa;--line:#dce3e8;--ink:#233443}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:14px Inter,Arial,sans-serif}}
main{{max-width:1180px;margin:auto;padding:38px}} h1{{font-size:34px;margin:0;color:var(--navy)}} h2{{color:var(--navy);font-size:18px;margin-top:30px}}
.eyebrow{{color:var(--teal);font-weight:700;letter-spacing:.12em;font-size:11px}} .status{{display:inline-block;border:1px solid var(--teal);padding:6px 10px;border-radius:99px;font-weight:700;color:var(--teal)}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}} .card{{background:white;border:1px solid var(--line);padding:18px;border-radius:10px}} .card b{{display:block;font-size:25px;color:var(--navy);margin-top:8px}}
.brief{{background:#e9f4f3;border-left:4px solid var(--teal);padding:18px;line-height:1.55}} table{{width:100%;border-collapse:collapse;background:white}} th{{background:var(--navy);color:white;text-align:left;padding:11px}} td{{padding:10px;border-bottom:1px solid var(--line);vertical-align:top}}
.badge{{font-size:10px;font-weight:800;padding:4px 7px;border-radius:99px}} .high{{background:#fde8e2;color:#a33a25}} .medium{{background:#fff3d7;color:#916600}} .low{{background:#e4f3ef;color:#147565}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}} .foot{{font-size:11px;color:#667785;margin-top:28px;line-height:1.5}} @media(max-width:800px){{.cards,.grid{{grid-template-columns:1fr}}main{{padding:20px}}}}
</style></head><body><main>
<p class='eyebrow'>PORTFOLIO RISK COPILOT · {metrics['as_of_date']}</p><h1>Daily risk review</h1><p class='status'>{status}</p>
<section class='cards'>
<div class='card'>NAV<b>${metrics['nav']:,.0f}</b></div><div class='card'>Annualized volatility<b>{metrics['annualized_volatility']:.1%}</b></div>
<div class='card'>Historical VaR 95%<b>{metrics['historical_var_95']:.2%}</b></div><div class='card'>Expected Shortfall 95%<b>{metrics['expected_shortfall_95']:.2%}</b></div></section>
<h2>Risk brief</h2><div class='brief'>{html.escape(narrative)}</div>
<h2>Priority findings</h2><table><thead><tr><th>Priority</th><th>Finding</th><th>Required action</th></tr></thead><tbody>{finding_rows}</tbody></table>
<div class='grid'><section><h2>Stress scenarios</h2><table><thead><tr><th>Scenario</th><th>Return</th><th>P&amp;L</th></tr></thead><tbody>{stress_rows}</tbody></table></section>
<section><h2>Position risk</h2><table><thead><tr><th>Ticker</th><th>Class</th><th>Weight</th><th>Risk contribution</th><th>Beta</th><th>Limit</th></tr></thead><tbody>{position_rows}</tbody></table></section></div>
<div class='grid'><section><h2>Factor sensitivities</h2><table><thead><tr><th>Factor</th><th>Proxy</th><th>Sensitivity</th></tr></thead><tbody>{factor_rows}</tbody></table></section>
<section><h2>VaR model monitoring</h2><table><tbody><tr><td>Out-of-sample observations</td><td>{metrics['var_backtest_observations']}</td></tr><tr><td>Exceptions</td><td>{metrics['var_backtest_exceptions']}</td></tr><tr><td>Exception rate</td><td>{metrics['var_backtest_exception_rate']:.1%}</td></tr><tr><td>Status</td><td><strong>{metrics['var_backtest_status']}</strong></td></tr></tbody></table></section></div>
<p class='foot'>Demo market history is deterministic and synthetic. VaR and Expected Shortfall are model estimates, not maximum-loss forecasts. Calculations and controls are deterministic; any AI-generated narrative is restricted to the validated evidence packet. Human approval is required before distribution.</p>
</main></body></html>"""
    path.write_text(document, encoding="utf-8")

