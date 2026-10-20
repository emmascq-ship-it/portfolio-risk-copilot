# Deployment

## Live deployment

Public demo: https://emma-portfolio-risk-copilot.streamlit.app/

Hosted on Streamlit Community Cloud from `emmascq-ship-it/portfolio-risk-copilot`, branch `main`, entry point `app.py`. No API key was added. The default narrator is deterministic.

## Recommended public demo: Streamlit Community Cloud

1. Create a GitHub repository and push the project files.
2. In Streamlit Community Cloud, select the repository, branch, and `app.py` entry point.
3. Do not add an API key for the public portfolio version. The deterministic narrator is sufficient and keeps the demo reproducible.
4. Deploy and test the public URL in an incognito browser before adding it to LinkedIn.

## LinkedIn presentation

Add the public demo through **Featured → Add a link**. Use:

- **Title:** Multi-Asset Portfolio Risk Copilot
- **Description:** Interactive Python risk workflow combining VaR and Expected Shortfall, factor and concentration diagnostics, stress testing, model backtesting, automated controls, and evidence-grounded AI communication.

Also include the GitHub repository in the project description so a technical reviewer can inspect the implementation. The live application should be the primary link because it has lower viewing friction.

## Safe public-demo rules

- Keep the synthetic-data disclosure visible.
- Do not store keys in the repository.
- Do not describe the demo as a trading or regulatory risk system.
- Test file uploads with intentionally invalid inputs and confirm that controls block calculation.
