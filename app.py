from __future__ import annotations
import json
from datetime import datetime, timezone
import pandas as pd
import plotly.express as px
import streamlit as st

from config import APP_NAME, STARTING_BALANCE, WATCHLISTS
from database import initialize_database, row, rows
from oracle_bot import portfolio_equity
from analytics import portfolio_analytics
from api_manager import api_status
from intelligence_hub import collect_all
from market_data import get_history
from backtesting import run_backtest

st.set_page_config(page_title=APP_NAME, page_icon="🔮", layout="wide")
st.markdown("""
<style>
.stApp{background:#0b1018}.block-container{max-width:1450px;padding-top:1.2rem}
.hero{padding:1.1rem 1.3rem;border:1px solid #263449;border-radius:18px;background:linear-gradient(135deg,#111b29,#0d1520);margin-bottom:1rem}
.hero h1{margin:0;font-size:clamp(1.8rem,4vw,3rem)}.hero p{margin:.35rem 0 0;color:#aebbd0}
.status{padding:.75rem 1rem;border-radius:12px;background:#111a26;border:1px solid #263449;margin-bottom:1rem}
[data-testid="stMetric"]{background:#111a26;border:1px solid #263449;padding:.85rem;border-radius:14px}
</style>
""", unsafe_allow_html=True)

initialize_database()
st.markdown(f'<div class="hero"><h1>🔮 {APP_NAME}</h1><p>Two independent 24/7 engines · Stock Market vs Crypto Market · simulated trading intelligence</p></div>', unsafe_allow_html=True)

def worker_card(market: str, name: str) -> None:
    try:
        status = row("SELECT * FROM market_worker_status WHERE market=%s", (market,))
    except Exception:
        status = None
    healthy = False
    if status and status.get("heartbeat"):
        try:
            heartbeat = datetime.fromisoformat(status["heartbeat"])
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=timezone.utc)
            healthy = status.get("status") == "healthy" and (datetime.now(timezone.utc)-heartbeat).total_seconds() < 1200
        except (TypeError, ValueError):
            pass
    label = "🟢 ONLINE" if healthy else "🟠 WAITING / CHECK SERVICE"
    st.markdown(f'<div class="status"><b>{name} worker:</b> {label}<br><small>{(status or {}).get("message", "No heartbeat yet")}</small></div>', unsafe_allow_html=True)

wc1, wc2 = st.columns(2)
with wc1:
    worker_card("cash", "Stock Market")
with wc2:
    worker_card("crypto", "Crypto Market")

tabs = st.tabs(["Trading Pit","Signals","Heat Map","Intelligence","Analytics","Backtest","Journal","System"])

def pit(market: str, title: str) -> None:
    a = portfolio_analytics(market)
    starting = float(a["starting_balance"]); equity = float(a["equity"])
    ret = (equity / starting - 1) * 100 if starting else 0
    st.subheader(title)
    c = st.columns(4)
    c[0].metric("Equity", f"${equity:,.2f}", f"${equity-starting:+,.2f}")
    c[1].metric("Return", f"{ret:+.2f}%")
    c[2].metric("Cash", f"${float(a['cash']):,.2f}")
    c[3].metric("Invested", f"${float(a['positions_value']):,.2f}")
    snap = rows("SELECT created_at,equity FROM equity_snapshots WHERE market=%s ORDER BY id", (market,))
    if snap:
        df = pd.DataFrame(snap); df["created_at"] = pd.to_datetime(df["created_at"])
        st.plotly_chart(px.line(df,x="created_at",y="equity",title=f"{title} equity"),use_container_width=True)
    positions = rows("SELECT symbol,quantity,entry_price,current_price,quantity*current_price AS value,(current_price/NULLIF(entry_price,0)-1)*100 AS pnl_pct FROM positions WHERE market=%s", (market,))
    st.dataframe(pd.DataFrame(positions),use_container_width=True,hide_index=True) if positions else st.caption("No open simulated positions.")

with tabs[0]:
    left,right=st.columns(2)
    with left: pit("cash","💵 Cash Market")
    with right: pit("crypto","₿ Crypto Market")
    ce=portfolio_equity("cash")["equity"]; cr=portfolio_equity("crypto")["equity"]
    st.markdown(f"### Current leader: **{'Cash Market' if ce>cr else 'Crypto Market' if cr>ce else 'Tie'}**")
with tabs[1]:
    market=st.radio("Market",["cash","crypto"],horizontal=True)
    signals=rows("SELECT s.* FROM signals s INNER JOIN (SELECT symbol,MAX(id) max_id FROM signals WHERE market=%s GROUP BY symbol) x ON s.id=x.max_id ORDER BY s.score DESC",(market,))
    if signals:
        df=pd.DataFrame(signals); st.dataframe(df[["symbol","action","price","score","confidence","created_at"]],use_container_width=True,hide_index=True)
        symbol=st.selectbox("Inspect",df["symbol"].tolist()); chosen=next(x for x in signals if x["symbol"]==symbol)
        try: st.info(json.loads(chosen.get("details") or "{}").get("reason",""))
        except Exception: pass
    else: st.info("Start the worker to generate signals.")
with tabs[2]:
    sig=rows("SELECT s.symbol,s.market,s.score,s.action,s.price FROM signals s INNER JOIN (SELECT market,symbol,MAX(id) max_id FROM signals GROUP BY market,symbol)x ON s.id=x.max_id")
    if sig:
        df=pd.DataFrame(sig); st.plotly_chart(px.treemap(df,path=["market","symbol"],values="price",color="score",range_color=[0,1]),use_container_width=True)
    else: st.info("Heat map appears after the first worker scan.")
with tabs[3]:
    for name,result in collect_all().items():
        with st.expander(name):
            st.write(f"Provider: **{result.provider}**"); st.write(result.message)
            if result.records: st.dataframe(pd.DataFrame(result.records),use_container_width=True)
with tabs[4]:
    for market in ("cash","crypto"):
        a=portfolio_analytics(market); st.subheader(market.title())
        c=st.columns(4); c[0].metric("Sharpe",f"{a['sharpe']:.2f}"); c[1].metric("Max drawdown",f"{a['max_drawdown']*100:.2f}%"); c[2].metric("Closed trades",a["closed_trades"]); c[3].metric("Win rate",f"{a['win_rate']:.1f}%")
with tabs[5]:
    market=st.selectbox("Backtest market",["cash","crypto"]); symbol=st.selectbox("Symbol",list(WATCHLISTS[market]))
    if st.button("Run backtest"):
        result=run_backtest(symbol,get_history(symbol,"2y","1d"),STARTING_BALANCE)
        if result.get("error"): st.error(result["error"])
        else:
            c=st.columns(3); c[0].metric("Ending equity",f"${result['ending_equity']:.2f}"); c[1].metric("Return",f"{result['return_pct']:.2f}%"); c[2].metric("Trades",result["trades"]); st.line_chart(result["equity_curve"])
with tabs[6]:
    trades=rows("SELECT * FROM trades ORDER BY id DESC LIMIT 500"); alerts=rows("SELECT * FROM alerts ORDER BY id DESC LIMIT 100")
    st.dataframe(pd.DataFrame(trades),use_container_width=True,hide_index=True) if trades else st.info("No simulated trades yet.")
    if alerts: st.subheader("Alerts"); st.dataframe(pd.DataFrame(alerts),use_container_width=True,hide_index=True)
with tabs[7]:
    st.subheader("Data providers")
    for name,enabled in api_status().items(): st.write("✅" if enabled else "➖",name)
    st.subheader("Railway commands"); st.code("streamlit run app.py --server.address 0.0.0.0 --server.port $PORT"); st.code("python stock_worker.py"); st.code("python crypto_worker.py")
    st.caption("Paper trading only. No guaranteed returns or real brokerage execution.")
