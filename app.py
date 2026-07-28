"""🚀 AI Trading Brain v3 — Real Trading Ready (Binance + Paper)"""
import os, json, time, threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from brain.evolving_brain import EvolvingBrain
from brain.market_pipeline import scan_market, ASSETS
from exchange.binance_trader import is_connected, get_account, get_price, get_all_prices, place_order, get_order_history, place_buy, place_sell, get_open_orders, cancel_order

app = Flask(__name__)
CORS(app)
brain = EvolvingBrain()

TRADING_MODE = "paper"
if is_connected():
    TRADING_MODE = "testnet" if os.environ.get("BINANCE_TESTNET", "true") == "true" else "live"

portfolio = {"cash": 10000.0, "positions": [], "trades": [], "total_pnl": 0.0, "wins": 0, "losses": 0, "max_value": 10000.0, "min_value": 10000.0}
P_PATH = os.path.join(os.path.dirname(__file__), 'data', 'portfolio.json')
os.makedirs(os.path.dirname(P_PATH), exist_ok=True)

def save_pf():
    try:
        with open(P_PATH, 'w') as f: json.dump(portfolio, f, indent=2, default=str)
    except: pass

def load_pf():
    global portfolio
    if os.path.exists(P_PATH):
        try:
            with open(P_PATH) as f: portfolio.update(json.load(f))
        except: pass
load_pf()

def evo_loop():
    while True:
        time.sleep(600)
        try: brain.evolve()
        except: pass
threading.Thread(target=evo_loop, daemon=True).start()

@app.route('/')
def index():
    return jsonify({"name": "AI Trading Brain", "version": "3.0.0", "mode": TRADING_MODE, binance_connected": is_connected(), "brain": brain.get_health()})

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "platform": "AI Trading Brain v3", "runtime": "Python/Flask", "neurons": 50, "generation": brain.generation, "trading_mode": TRADING_MODE, "binance_connected": is_connected(), "timestamp": datetime.utcnow().isoformat()})

@app.route('/api/mode', methods=['GET', 'POST'])
def trading_mode():
    global TRADING_MODE
    if request.method == 'POST':
        data = request.get_json() or {}
        new_mode = data.get("mode", "paper")
        if new_mode in ("paper", "testnet", "live"):
            if new_mode == "live" and not is_connected():
                return jsonify({"error": "Cannot switch to live — Binance API keys not configured", "mode": TRADING_MODE}), 400
            if new_mode in ("testnet", "live") and not is_connected():
                return jsonify({"error": "Binance API keys required for testnet/live trading", "mode": TRADING_MODE}), 400
            TRADING_MODE = new_mode
    return jsonify({"mode": TRADING_MODE, "binance_connected": is_connected()})

@app.route('/api/binance/account')
def binance_account():
    if not is_connected():
        return jsonify({"connected": False, "message": "Set BINANCE_API_KEY and BINANCE_SECRET_KEY env vars"})
    return jsonify(get_account())

@app.route('/api/binance/prices')
def binance_prices():
    return jsonify(get_all_prices())

@app.route('/api/market/scan')
def market_scan(): return jsonify(scan_market(brain))

@app.route('/api/market/price/<symbol>')
def market_price(symbol):
    bs = symbol.replace("-USD", "USDC")
    return jsonify(get_price(bs))

@app.route('/api/portfolio')
def get_portfolio():
    try: prices = fetch_real_prices()
    except:
        try:
            from brain.market_pipeline import fetch_real_prices
            prices = fetch_real_prices()
        except: prices = {}
    holdings = sum(pos["quantity"] * prices.get(pos["symbol"], {}).get("price", pos["entry_price"]) for pos in portfolio["positions"])
    tv = portfolio["cash"] + holdings
    portfolio["max_value"] = max(portfolio["max_value"], tv)
    portfolio["min_value"] = min(portfolio["min_value"], tv)
    dd = ((portfolio["max_value"] - tv) / portfolio["max_value"] * 100) if portfolio["max_value"] > 0 else 0
    tt = portfolio["wins"] + portfolio["losses"]
    wr = (portfolio["wins"] / tt * 100) if tt > 0 else 0
    return jsonify({"cash": round(portfolio["cash"], 2), "holdings_value": round(holdings, 2), "total_value": round(tv, 2), "total_pnl": round(portfolio["total_pnl"], 2), "win_rate": round(wr, 1), "drawdown": round(dd, 2), "trades_total": tt, "wins": portfolio["wins"], "losses": portfolio["losses"], "mode": TRADING_MODE, "positions": portfolio["positions"], "recent_trades": portfolio["trades"][-20:]})
