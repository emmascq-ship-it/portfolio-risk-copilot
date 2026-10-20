# Interview guide

## 45-second description

I built a multi-asset portfolio-risk workflow to connect my FRM knowledge with Python automation and controlled use of AI. The deterministic engine calculates volatility, historical and parametric VaR, Expected Shortfall, drawdown, beta, position risk contribution, factor sensitivities, scenario losses, and rolling VaR exceptions. The review layer ranks limit breaches and material concentrations, while an AI-assisted communication layer drafts a brief using only validated evidence. I intentionally kept human approval and model controls in the workflow because a useful risk tool needs governance, not just attractive charts.

## Three-minute demonstration sequence

1. Start on **Decision brief** and state the decision question: where is risk concentrated and what requires escalation?
2. Open **Exposure map** and compare economic weight with contribution to volatility; explain why they are not the same.
3. Open **Stress testing** and interpret the worst scenario in both percentage and dollar terms.
4. Open **Model monitoring** and explain that each VaR estimate uses the preceding 250 observations, preventing look-ahead bias.
5. Finish on **Controls & governance**: calculations and statuses are deterministic, AI only summarizes the evidence packet, and publication requires analyst approval.

## Three points to demonstrate

1. **Controls first:** remove a ticker column from the price file and show that the workflow blocks calculation.
2. **Risk concentration:** identify the position whose volatility contribution is larger than its capital weight.
3. **Stress before narrative:** show the scenario loss in the canonical JSON, then show how the same evidence appears in the risk brief.

## Questions to be ready for

- Why is Expected Shortfall larger than VaR?
- What assumptions make parametric VaR fragile?
- Why can component risk contribution be different from portfolio weight?
- Why do we backtest VaR, and what does an exception mean?
- Why should an LLM not calculate or approve risk metrics?
- What would need to change before production use?

## Honest limitations

- Demo prices are synthetic and are not presented as live data.
- No options, nonlinear risk, liquidity horizon, or counterparty exposure.
- The rolling VaR backtest is a model-monitoring demonstration, not a regulatory-capital calculation.
- The optional LLM drafts commentary only; it does not alter risk results.

