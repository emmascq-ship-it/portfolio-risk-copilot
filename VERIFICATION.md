# Publication verification — October 19, 2026

## Design polish — October 20, 2026

- Applied the supplied `developing-with-streamlit` routing skill and version-matched local design, theme, layout and chart references.
- Preserved the calculation engine, review agents, report generation and five-view workflow.
- Added explicit high-priority review status, compact responsive metric cards, full labels and time horizons, readable financial table formats, paired exposure bars, percentage chart axes and exception markers.
- Confirmed all five existing calculation tests pass. Streamlit AppTest renders all views without exceptions; incomplete uploads stop analysis, and demo mode resumes with unchanged backtest results.
- Verified the final local preview on desktop and at 390 × 844. The mobile document width equals the viewport; metric labels do not clip. Screenshots are saved under the ignored `output/` directory.
- Pinned Streamlit to the locally verified version 1.66.0 and declared the Altair chart dependency.

Recovered the existing V2 source from `Portfolio_Risk_Copilot_V2.zip` in the original project chat. The archive excluded `.git`, so its two original development commits could not be recovered. The local recovery commit is preserved on `codex/recovered-v2`.

Public source: https://github.com/emmascq-ship-it/portfolio-risk-copilot

The authenticated GitHub connector published the recovered source after command-line Git had no credentials. The published tree matched the local recovery tree (`2ca22f5c38b4a2f321430fd7f9d72fed84867378`). Local `main` now tracks `origin/main`.

## Completed locally

- Five existing unit tests passed.
- Streamlit AppTest rendered without exceptions.
- Demo metrics: NAV $2.75M; annualized volatility 15.6%; historical 95% VaR 1.47%; 95% Expected Shortfall 1.96%; worst stress -12.5%.
- Backtest: 269 observations, 18 exceptions, 6.7% exception rate.
- Chrome rendered the decision brief, exposure charts, and governance/report-download control.
- At 390 × 844, cards stack, tabs scroll, and document width equals viewport width (390 px). This is browser emulation, not a physical-device test.
- Prepared `LINKEDIN_FEATURED.md` and a 1200 × 627 cover in `assets/linkedin-featured.png`.

## Public deployment verified

Live demo: https://emma-portfolio-risk-copilot.streamlit.app/

- Deployed the existing `app.py` from GitHub `main` through Streamlit Community Cloud, with no API key added.
- Opened the application in a separate browser session without signing in; demo metrics and all eight controls rendered.
- Verified the live backtest shows 269 observations, 18 exceptions, and a 6.7% exception rate.
- Downloaded `portfolio_risk_brief.html` from the live governance view.
- Checked the public app at 390 × 844: cards stack and tabs scroll; the outer document width is 390 px. Browser emulation was used, not a physical phone.
- Saved live desktop and mobile screenshots in the ignored `output/` directory.
- Custom-input mode was exercised, but automated CSV attachment was blocked by the Chrome extension's file-URL permission. End-to-end custom-upload verification remains uncompleted; this limitation is separate from the passing calculation tests.
