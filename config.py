from __future__ import annotations
import os

APP_NAME = "GARIBALDI MARKET ORACLE™"
STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "200"))
WORKER_INTERVAL_SECONDS = max(60, int(os.getenv("WORKER_INTERVAL_SECONDS", "300")))
ENABLE_AUTOTRADE = os.getenv("ENABLE_AUTOTRADE", "true").lower() == "true"
ENABLE_NEWS = os.getenv("ENABLE_NEWS", "true").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
AUTO_UPGRADE_EMPTY_PORTFOLIOS = os.getenv("AUTO_UPGRADE_EMPTY_PORTFOLIOS", "true").lower() == "true"

CASH_WATCHLIST = {
    "SPY": "S&P 500 ETF", "QQQ": "Nasdaq-100 ETF", "IWM": "Russell 2000 ETF",
    "DIA": "Dow Jones ETF", "GLD": "Gold ETF", "SLV": "Silver ETF",
    "TLT": "Long Treasury ETF", "UUP": "US Dollar ETF", "XLE": "Energy ETF",
    "XLF": "Financial ETF", "XLK": "Technology ETF", "AAPL": "Apple",
    "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "META": "Meta",
    "GOOGL": "Alphabet", "TSLA": "Tesla", "RKLB": "Rocket Lab", "PLTR": "Palantir",
    "AVGO": "Broadcom", "AMD": "AMD", "SMCI": "Super Micro Computer",
}
CRYPTO_WATCHLIST = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana",
    "XRP-USD": "XRP", "DOGE-USD": "Dogecoin", "ADA-USD": "Cardano",
    "AVAX-USD": "Avalanche", "LINK-USD": "Chainlink", "LTC-USD": "Litecoin",
}
WATCHLISTS = {"cash": CASH_WATCHLIST, "crypto": CRYPTO_WATCHLIST}

MAX_POSITION_FRACTION = float(os.getenv("MAX_POSITION_FRACTION", "0.25"))
MIN_TRADE_VALUE = float(os.getenv("MIN_TRADE_VALUE", "5.00"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "4"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.06"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.12"))
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "0.05"))
SIGNAL_BUY_THRESHOLD = float(os.getenv("SIGNAL_BUY_THRESHOLD", "0.60"))
SIGNAL_SELL_THRESHOLD = float(os.getenv("SIGNAL_SELL_THRESHOLD", "0.40"))
TRADE_COOLDOWN_MINUTES = int(os.getenv("TRADE_COOLDOWN_MINUTES", "60"))
MAX_DAILY_DRAWDOWN_PCT = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.10"))
