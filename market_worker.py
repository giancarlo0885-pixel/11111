from __future__ import annotations
import logging
import os
import signal
from threading import Event

from config import WATCHLISTS, WORKER_INTERVAL_SECONDS
from database import (
    connect, initialize_database, save_forecast, save_intelligence_event,
    save_json_signal, trim_old_records, utc_now,
)
from market_data import get_history
from news_intelligence import get_news_sentiment
from engine import analyze_market
from forecasting import forecast_price
from oracle_bot import update_prices, risk_exits, process_signals, snapshot
from intelligence_hub import collect_all

log = logging.getLogger("market-worker")
stop_event = Event()
signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
signal.signal(signal.SIGINT, lambda *_: stop_event.set())


def _ensure_status_table() -> None:
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_worker_status (
                market TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                message TEXT,
                last_run TEXT,
                heartbeat TEXT
            )
        """)


def set_market_status(market: str, status: str, message: str, completed: bool = False) -> None:
    now = utc_now()
    with connect() as conn:
        conn.execute("""
            INSERT INTO market_worker_status(market,status,message,last_run,heartbeat)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT (market) DO UPDATE SET
                status=EXCLUDED.status,
                message=EXCLUDED.message,
                heartbeat=EXCLUDED.heartbeat,
                last_run=CASE WHEN %s THEN EXCLUDED.last_run ELSE market_worker_status.last_run END
        """, (market, status, message, now if completed else None, now, completed))


def scan_market(market: str) -> list[str]:
    watchlist = WATCHLISTS[market]
    signals, prices = [], {}
    for symbol, name in watchlist.items():
        if stop_event.is_set():
            break
        try:
            hist = get_history(symbol, "1y", "1d")
            if hist.empty:
                continue
            news = get_news_sentiment(f"{name} {symbol}")
            sig = analyze_market(symbol, hist, news.sentiment)
            if not sig:
                continue
            signals.append(sig)
            prices[symbol] = sig.price
            save_json_signal(
                market, symbol, sig.price, sig.score, sig.action, sig.confidence,
                sig.to_dict() | {"headlines": news.headlines[:5], "news_source": news.source},
            )
            fc = forecast_price(hist, 5)
            if fc:
                save_forecast(market, symbol, fc)
        except Exception as exc:
            log.exception("%s scan failed for %s: %s", market, symbol, exc)

    update_prices(market, prices)
    actions = risk_exits(market, prices) + process_signals(market, signals)
    snapshot(market)
    return actions


def run_worker(market: str) -> None:
    if market not in WATCHLISTS:
        raise ValueError(f"Unknown market: {market}")

    initialize_database()
    _ensure_status_table()
    interval = max(60, int(os.getenv(f"{market.upper()}_WORKER_INTERVAL_SECONDS", str(WORKER_INTERVAL_SECONDS))))
    label = "Stock Market" if market == "cash" else "Crypto Market"
    log.info("Starting %s worker with %s-second cycles", label, interval)

    while not stop_event.is_set():
        try:
            set_market_status(market, "running", f"{label} worker is scanning.")
            actions = scan_market(market)

            # Run broader intelligence once from the stock worker to prevent duplicate inserts.
            if market == "cash":
                for category, result in collect_all().items():
                    if result.available:
                        for record in result.records:
                            save_intelligence_event(category, result.provider, record.get("title", category), record)
                trim_old_records()

            message = f"{label} scan completed."
            message += " Actions: " + ", ".join(actions) if actions else " No trades met the rules."
            set_market_status(market, "healthy", message, True)
            log.info(message)
        except Exception as exc:
            log.exception("%s worker cycle failed: %s", label, exc)
            set_market_status(market, "error", str(exc), True)

        stop_event.wait(interval)

    set_market_status(market, "stopped", f"{label} worker stopped.")


def configure_logging(name: str) -> None:
    logging.basicConfig(
        level=os.getenv("WORKER_LOG_LEVEL", "INFO").upper(),
        format=f"%(asctime)s | %(levelname)s | {name} | %(message)s",
    )
