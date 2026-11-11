import pandas as pd


def load_nifty(path: str = "data/nifty50.csv") -> pd.Series:
    df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    return df["Close"].sort_index()


def rolling_returns(prices: pd.Series, years: int) -> pd.Series:
    """Annualised return of investing on each date and holding for `years`."""
    end_dates = prices.index + pd.DateOffset(years=years)
    valid = end_dates <= prices.index[-1]
    end_prices = prices.reindex(end_dates[valid], method="ffill")
    start_prices = prices[valid]
    total = end_prices.values / start_prices.values
    return pd.Series(total ** (1 / years) - 1, index=start_prices.index)


def invest_beats_prepay(prices: pd.Series, loan_rate_pct: float, years: int) -> dict:
    """Share of historical windows where Nifty's annual return beat the loan rate."""
    rets = rolling_returns(prices, years)
    hurdle = loan_rate_pct / 100
    return {
        "windows": int(len(rets)),
        "pct_invest_wins": float((rets > hurdle).mean() * 100),
        "median_return_pct": float(rets.median() * 100),
        "worst_return_pct": float(rets.min() * 100),
        "best_return_pct": float(rets.max() * 100),
    }