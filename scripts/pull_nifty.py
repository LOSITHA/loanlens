import yfinance as yf

df = yf.download("^NSEI", start="2007-09-01", auto_adjust=True, progress=False)
if hasattr(df.columns, "droplevel") and df.columns.nlevels > 1:
    df.columns = df.columns.droplevel(1)   # newer yfinance returns MultiIndex columns
df = df[["Close"]].dropna()
df.index.name = "Date"
df.to_csv("data/nifty50.csv")
print(df.head(), "\n...\n", df.tail())
print("Rows:", len(df), "| From", df.index.min().date(), "to", df.index.max().date())