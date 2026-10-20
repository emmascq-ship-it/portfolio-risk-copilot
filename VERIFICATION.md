# Publication verification — October 19, 2026

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

## Pending

Streamlit Community Cloud requires the user to approve its GitHub OAuth permissions before deployment. No public app URL or live-app verification is claimed. Deploy branch `main`, entry point `app.py`, with no API key, after authorization. Then repeat desktop/mobile checks against the public URL and test custom CSV uploads and report export.
