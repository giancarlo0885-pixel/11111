# GARIBALDI MARKET ORACLE™ — Dual Worker Upgrade

This upgrade keeps the original Hope-is-near project and separates its continuous paper-trading engine into two independent Railway workers:

- **Stock Market Worker:** `python stock_worker.py`
- **Crypto Market Worker:** `python crypto_worker.py`
- **Web Dashboard:** `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`

Both portfolios start at **$200** by default. There are no legacy small-balance challenge settings in this upgrade.

## Railway setup

Create three services from the same GitHub repository:

1. Web service — use the Streamlit command above.
2. Stock worker — use `python stock_worker.py`.
3. Crypto worker — use `python crypto_worker.py`.

Give all three services the same PostgreSQL `DATABASE_URL` and the same API variables.

Recommended variables:

```text
STARTING_BALANCE=200
ENABLE_AUTOTRADE=true
ENABLE_NEWS=true
WORKER_INTERVAL_SECONDS=300
STOCK_WORKER_INTERVAL_SECONDS=300
CRYPTO_WORKER_INTERVAL_SECONDS=300
```

The processes run continuously. The crypto worker can receive fresh market data around the clock. The stock worker also stays online continuously, but stock trades depend on available market data and market hours.

## Important

This remains simulated paper trading. It does not connect to a brokerage or guarantee profits.
