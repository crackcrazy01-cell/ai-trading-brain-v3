"""🚀 AI Trading Brain — Real Trading Ready Flask API"""
import os, json, time, threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from brain.evolving_brain import EvolvingBrain
from brain.market_pipeline import scan_market, ASSETS

app = Flask(__name__)
CORS(app)
brain = EvolvingBrain()

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
    return jsonify({"name": "AI Trading Brain", "version": "3.0.0", "mode": "paper", "brain": brain.get_health()})

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "platform": "AI Trading Brain v3", "runtime": "Python/Flask", "neurons": 50, "generation": brain.generation, "timestamp": datetime.utcnow().isoformat()})

@app.route('/api/market/scan')
def market_scan():
    return jsonify(scan_market(brain))

@app.route('/api/portfolio')
def get_portfolio():
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
    return jsonify({"cash": round(portfolio["cash"], 2), "holdings_value": round(holdings, 2), "total_value": round(tv, 2), "total_pnl": round(portfolio["total_pnl"], 2), "win_rate": round(wr, 1), "drawdown": round(dd, 2), "trades_total": tt, "wins": portfolio["wins"], "losses": portfolio["losses"], "positions": portfolio["positions"], "recent_trades": portfolio["trades"][-20:]})

@app.route('/api/trade', methods=['POST'])
def execute_trade():
    data = request.get_json() or {}
    symbol = data.get("symbol")
    direction = data.get("direction", "buy")
    amount = float(data.get("amount", 100))
    sl_pct = float(data.get("stop_loss", 5))
    tp_pct = float(data.get("take_profit", 15))
    if not symbol: return jsonify({"error": "Symbol required"}), 400
    try:
        from brain.market_pipeline import fetch_real_prices
        price = fetch_real_prices().get(symbol, {}).get("price")
    except: price = None
    if not price:
        asset = next((a for a in ASSETS if a["symbol"] == symbol), None)
        if not asset: return jsonify({"error": "Unknown symbol"}), 400
        price = 100
    if direction == "buy":
        if amount > portfolio["cash"]: return jsonify({"error": "Insufficient cash"}), 400
        qty = amount / price
        portfolio["cash"] -= amount
        pos = {"symbol": symbol, "quantity": round(qty, 8), "entry_price": round(price, 4), "amount": round(amount, 2), "stop_loss": round(price * (1 - sl_pct / 100), 4), "take_profit": round(price * (1 + tp_pct / 100), 4), "opened_at": datetime.utcnow().isoformat()}
        portfolio["positions"].append(pos)
        save_pf()
        return jsonify({"success": True, "action": "buy", "position": pos})
    elif direction == "sell":
        idx = next((i for i, p in enumerate(portfolio["positions"]) if p["symbol"] == symbol), None)
        if idx is None: return jsonify({"error": "No position found"}), 400
        pos = portfolio["positions"].pop(idx)
        rev = pos["quantity"] * price
        pnl = rev - pos["amount"]
        portfolio["cash"] += rev
        portfolio["total_pnl"] += pnl
        if pnl > 0: portfolio["wins"] += 1
        else: portfolio["losses"] += 1
        trade = {"symbol": symbol, "entry_price": pos["entry_price"], "exit_price": round(price, 4), "pnl": round(pnl, 2), "pnl_pct": round(((price - pos["entry_price"]) / pos["entry_price"]) * 100, 2), "type": "win" if pnl > 0 else "loss", "closed_at": datetime.utcnow().isoformat()}
        portfolio["trades"].append(trade)
        portfolio["trades"] = portfolio["trades"][-500:]
        save_pf()
        return jsonify({"success": True, "action": "sell", "trade": trade})

@app.route('/api/portfolio/reset', methods=['POST'])
def reset_portfolio():
    global portfolio
    portfolio = {"cash": 10000.0, "positions": [], "trades": [], "total_pnl": 0.0, "wins": 0, "losses": 0, "max_value": 10000.0, "min_value": 10000.0}
    save_pf()
    return jsonify({"success": True, "message": "Portfolio reset to $10,000"})

@app.route('/api/brain/health')
def brain_health(): return jsonify(brain.get_health())

@app.route('/api/brain/evolve', methods=['POST'])
def force_evolve():
    log = brain.evolve()
    return jsonify({"success": True, "log": log, "health": brain.get_health()})

@app.route('/api/brain/log')
def brain_log(): return jsonify({"generation": brain.generation, "log": brain.evolution_log[-50:]})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
