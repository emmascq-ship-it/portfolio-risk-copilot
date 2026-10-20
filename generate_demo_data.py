from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "sample_inputs"


def main() -> None:
    INPUT.mkdir(parents=True, exist_ok=True)

    portfolio = pd.DataFrame(
        [
            ["SPY", "Equity", 1800, 570.0, "USD", 0.35],
            ["QQQ", "Equity", 1250, 490.0, "USD", 0.30],
            ["EEM", "Equity", 4200, 45.0, "USD", 0.15],
            ["TLT", "Rates", 3200, 94.0, "USD", 0.20],
            ["HYG", "Credit", 3600, 80.0, "USD", 0.20],
            ["GLD", "Commodity", 1100, 240.0, "USD", 0.15],
            ["UUP", "FX", 2500, 29.0, "USD", 0.10],
        ],
        columns=["ticker", "asset_class", "quantity", "price", "currency", "limit_weight"],
    )
    portfolio.to_csv(INPUT / "portfolio.csv", index=False)

    scenarios = pd.DataFrame(
        [
            ["Equity sell-off", "Equity", -0.18], ["Equity sell-off", "Rates", 0.05],
            ["Equity sell-off", "Credit", -0.08], ["Equity sell-off", "Commodity", -0.04],
            ["Equity sell-off", "FX", 0.04],
            ["Rates +150bp", "Equity", -0.07], ["Rates +150bp", "Rates", -0.12],
            ["Rates +150bp", "Credit", -0.06], ["Rates +150bp", "Commodity", -0.03],
            ["Rates +150bp", "FX", 0.05],
            ["Credit widening", "Equity", -0.10], ["Credit widening", "Rates", 0.02],
            ["Credit widening", "Credit", -0.13], ["Credit widening", "Commodity", -0.02],
            ["Credit widening", "FX", 0.03],
            ["USD reversal", "Equity", 0.03], ["USD reversal", "Rates", 0.01],
            ["USD reversal", "Credit", 0.02], ["USD reversal", "Commodity", 0.08],
            ["USD reversal", "FX", -0.10],
        ],
        columns=["scenario", "asset_class", "shock"],
    )
    scenarios.to_csv(INPUT / "stress_scenarios.csv", index=False)

    rng = np.random.default_rng(20261020)
    dates = pd.bdate_range(end="2026-10-16", periods=520)
    factors = rng.multivariate_normal(
        mean=[0.00035, 0.00005, 0.00008, 0.00002],
        cov=np.array(
            [
                [0.00014, -0.000025, 0.000055, -0.000010],
                [-0.000025, 0.000045, -0.000010, 0.000005],
                [0.000055, -0.000010, 0.000080, -0.000005],
                [-0.000010, 0.000005, -0.000005, 0.000030],
            ]
        ),
        size=len(dates),
    )
    loadings = {
        "SPY": [1.00, 0.00, 0.10, -0.05],
        "QQQ": [1.25, -0.10, 0.05, -0.08],
        "EEM": [0.95, -0.05, 0.25, -0.25],
        "TLT": [-0.10, 1.20, -0.10, 0.05],
        "HYG": [0.35, 0.15, 0.85, -0.05],
        "GLD": [0.05, 0.25, 0.00, -0.30],
        "UUP": [-0.05, 0.05, -0.05, 1.00],
    }
    starts = {"SPY": 450, "QQQ": 380, "EEM": 39, "TLT": 98, "HYG": 76, "GLD": 180, "UUP": 28}
    price_data: dict[str, object] = {"date": dates}
    for ticker, beta in loadings.items():
        idio = rng.normal(0, 0.004 if ticker in {"SPY", "TLT", "UUP"} else 0.006, len(dates))
        returns = factors @ np.array(beta) + idio
        price_data[ticker] = starts[ticker] * np.exp(np.cumsum(returns))
    pd.DataFrame(price_data).to_csv(INPUT / "market_prices.csv", index=False, date_format="%Y-%m-%d")


if __name__ == "__main__":
    main()

