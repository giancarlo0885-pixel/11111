"""Compatibility launcher. Railway should use stock_worker.py and crypto_worker.py separately."""
import os
from market_worker import configure_logging, run_worker

if __name__ == "__main__":
    market = os.getenv("WORKER_MARKET", "cash").strip().lower()
    if market == "stock":
        market = "cash"
    configure_logging(market.upper())
    run_worker(market)
