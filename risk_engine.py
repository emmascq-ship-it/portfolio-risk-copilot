from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm


TRADING_DAYS = 252


@dataclass
class RiskBundle:
    metrics: dict[str, Any]
    controls: list[dict[str, Any]]
    positions: pd.DataFrame
    returns: pd.DataFrame
    contributions: pd.DataFrame
    stresses: pd.DataFrame
    factor_exposures: pd.DataFrame
    backtest: pd.DataFrame


def load_inputs(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    portfolio = pd.read_csv(input_dir / "portfolio.csv")
    prices = pd.read_csv(input_dir / "market_prices.csv", parse_dates=["date"]).set_index("date")
    scenarios = pd.read_csv(input_dir / "stress_scenarios.csv")
    return portfolio, prices, scenarios


def validate_inputs(portfolio: pd.DataFrame, prices: pd.DataFrame, scenarios: pd.DataFrame) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(check: str, passed: bool, evidence: str) -> None:
        checks.append({"check": check, "status": "PASS" if passed else "FAIL", "evidence": evidence})

    required = {"ticker", "asset_class", "quantity", "price", "currency", "limit_weight"}
    add("Portfolio schema", required.issubset(portfolio.columns), f"Required columns present: {required.issubset(portfolio.columns)}")
    add("Unique tickers", not portfolio["ticker"].duplicated().any(), f"Duplicate tickers: {int(portfolio['ticker'].duplicated().sum())}")
    add("Positive positions", bool((portfolio[["quantity", "price"]].astype(float) > 0).all().all()), "Quantities and prices must be positive")
    missing_tickers = sorted(set(portfolio["ticker"]) - set(prices.columns))
    add("Price coverage", not missing_tickers, f"Missing price series: {missing_tickers or 'none'}")
    add("Unique price dates", bool(prices.index.is_unique), f"Rows: {len(prices)}")
    missing_ratio = float(prices.isna().sum().sum() / max(prices.size, 1))
    add("Missing prices", missing_ratio == 0, f"Missing ratio: {missing_ratio:.2%}")
    add("History length", len(prices) >= 252, f"Business-day observations: {len(prices)}")
    required_classes = set(portfolio["asset_class"])
    scenario_classes = set(scenarios["asset_class"])
    add("Stress coverage", required_classes.issubset(scenario_classes), f"Covered classes: {sorted(scenario_classes)}")
    return checks


def _json_number(value: float) -> float:
    return float(np.round(value, 10))


def _calculate_factor_exposures(returns: pd.DataFrame, portfolio_returns: np.ndarray) -> pd.DataFrame:
    """Estimate transparent proxy-factor sensitivities with ordinary least squares."""
    proxy_map = {
        "Equity": "SPY",
        "Rates": "TLT",
        "Credit": "HYG",
        "Commodity": "GLD",
        "USD": "UUP",
    }
    available = [(factor, ticker) for factor, ticker in proxy_map.items() if ticker in returns.columns]
    if not available:
        return pd.DataFrame(columns=["factor", "proxy", "sensitivity"])
    x = returns[[ticker for _, ticker in available]].to_numpy()
    x = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(x, portfolio_returns, rcond=None)
    return pd.DataFrame(
        [
            {"factor": factor, "proxy": ticker, "sensitivity": _json_number(coefficients[index + 1])}
            for index, (factor, ticker) in enumerate(available)
        ]
    )


def _calculate_var_backtest(portfolio_returns: np.ndarray, dates: pd.Index, window: int = 250) -> pd.DataFrame:
    """Run a one-day 95% historical VaR backtest using only information available at each date."""
    rows: list[dict[str, Any]] = []
    for index in range(window, len(portfolio_returns)):
        history = portfolio_returns[index - window:index]
        var_95 = -float(np.quantile(history, 0.05))
        realized = float(portfolio_returns[index])
        rows.append(
            {
                "date": dates[index],
                "realized_return": realized,
                "var_95": var_95,
                "exception": realized < -var_95,
            }
        )
    return pd.DataFrame(rows)


def calculate_risk(portfolio: pd.DataFrame, prices: pd.DataFrame, scenarios: pd.DataFrame) -> RiskBundle:
    controls = validate_inputs(portfolio, prices, scenarios)
    if any(c["status"] == "FAIL" for c in controls):
        raise ValueError("Input controls failed; risk calculations were blocked")

    tickers = portfolio["ticker"].tolist()
    returns = prices[tickers].pct_change().dropna()
    positions = portfolio.copy()
    positions["market_value"] = positions["quantity"] * positions["price"]
    nav = float(positions["market_value"].sum())
    positions["weight"] = positions["market_value"] / nav
    weights = positions.set_index("ticker")["weight"].reindex(tickers).to_numpy()
    portfolio_returns = returns.to_numpy() @ weights

    cov_daily = returns.cov().to_numpy()
    port_var_daily = float(weights @ cov_daily @ weights)
    port_vol_daily = float(np.sqrt(max(port_var_daily, 0)))
    ann_vol = port_vol_daily * np.sqrt(TRADING_DAYS)
    hist_var_95 = -float(np.quantile(portfolio_returns, 0.05))
    hist_var_99 = -float(np.quantile(portfolio_returns, 0.01))
    es_95 = -float(portfolio_returns[portfolio_returns <= np.quantile(portfolio_returns, 0.05)].mean())
    param_var_95 = float(norm.ppf(0.95) * port_vol_daily)

    cumulative = np.cumprod(1 + portfolio_returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative / running_max - 1
    max_drawdown = float(drawdowns.min())

    marginal_vol = cov_daily @ weights / max(port_vol_daily, 1e-12)
    component_vol = weights * marginal_vol
    component_share = component_vol / max(component_vol.sum(), 1e-12)
    contributions = positions[["ticker", "asset_class", "market_value", "weight", "limit_weight"]].copy()
    contributions["annualized_volatility"] = returns.std().reindex(tickers).to_numpy() * np.sqrt(TRADING_DAYS)
    contributions["risk_contribution"] = component_share
    contributions["weight_limit_status"] = np.where(contributions["weight"].abs() <= contributions["limit_weight"], "PASS", "BREACH")

    market = returns["SPY"]
    betas = {}
    market_var = float(market.var())
    for ticker in tickers:
        betas[ticker] = float(returns[ticker].cov(market) / market_var) if market_var else 0.0
    contributions["market_beta"] = contributions["ticker"].map(betas)
    portfolio_beta = float((contributions["weight"] * contributions["market_beta"]).sum())

    scenario_table = scenarios.pivot(index="scenario", columns="asset_class", values="shock").fillna(0)
    class_weights = positions.groupby("asset_class")["weight"].sum()
    stress_rows = []
    for scenario, shocks in scenario_table.iterrows():
        impact = float(sum(class_weights.get(asset_class, 0) * shock for asset_class, shock in shocks.items()))
        stress_rows.append({"scenario": scenario, "portfolio_return": impact, "pnl": nav * impact})
    stresses = pd.DataFrame(stress_rows).sort_values("portfolio_return")
    factor_exposures = _calculate_factor_exposures(returns, portfolio_returns)
    backtest = _calculate_var_backtest(portfolio_returns, returns.index)
    exception_count = int(backtest["exception"].sum()) if len(backtest) else 0
    observation_count = int(len(backtest))
    exception_rate = exception_count / observation_count if observation_count else 0.0
    backtest_status = "PASS" if observation_count and exception_rate <= 0.075 else "REVIEW"

    metrics = {
        "as_of_date": prices.index.max().date().isoformat(),
        "nav": _json_number(nav),
        "annualized_volatility": _json_number(ann_vol),
        "historical_var_95": _json_number(hist_var_95),
        "historical_var_99": _json_number(hist_var_99),
        "expected_shortfall_95": _json_number(es_95),
        "parametric_var_95": _json_number(param_var_95),
        "max_drawdown": _json_number(max_drawdown),
        "market_beta": _json_number(portfolio_beta),
        "largest_weight": _json_number(float(contributions["weight"].max())),
        "largest_risk_contribution": _json_number(float(contributions["risk_contribution"].max())),
        "worst_stress_return": _json_number(float(stresses.iloc[0]["portfolio_return"])),
        "worst_stress_scenario": str(stresses.iloc[0]["scenario"]),
        "var_backtest_observations": observation_count,
        "var_backtest_exceptions": exception_count,
        "var_backtest_exception_rate": _json_number(exception_rate),
        "var_backtest_status": backtest_status,
    }
    return RiskBundle(metrics, controls, positions, returns, contributions, stresses, factor_exposures, backtest)

