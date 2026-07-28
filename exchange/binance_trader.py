"""🔗 Binance Trading Module — Real & Testnet support with paper fallback"""
import os, json, time, hmac, hashilib, urllib.parse
from datetime import datetime
import requests

# ---- CONFIG ----
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
USE_TESTNET = os.environ.get("BINANCE_TESTNET", "true").lower() == "true"

BASE_URL = "https://testnet.binance.vision" if USE_TESTNET else "https://api.binance.com"
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
ORDER_LOG = os.path.join(DATA_DIR, 'orders.json')
os.makedirs(DATA_DIR, exist_ok=True)

# ---- ORDER TRACKING ----
orders = []

def load_orders():
    global orders
    if os.path.exists(ORDER_LOG):
        try:
            with open(ORDER_LOG) as f:
                orders = json.load(f)
        except: pass

def save_orders():
    try:
        with open(ORDER_LOG, 'w') as f:
            json.dump(orders[-200:], f, indent=2, default=str)
    except: pass

load_orders()

# ---- AUTH HELPERS ----
def _sign_params(params):
    query = urllib.parse.urlencode(params)
    signature = hmac.new(BINANCE_SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    return query + "&signature=" + signature

def _headers():
    return {"X-MBX-APIKEY": BINANCE_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}

def is_connected():
    return bool(BINANCE_API_KEY and BINANCE_SECRET_KEY)

# ---- ACCOUNT ----
def get_account():
    if not is_connected():
        return {"error": "Binance API keys not configured", "mode": "paper"}
    try:
        ts = int(time.time() * 1000)
        params = {"timestamp": ts, "recvWindow": 5000}
        signed = _sign_params(params)
        r = requests.get(f"{BASE_URL}/api/v3/account?{signed}", headers=_headers(), timeout=15)
        if r.status_code == 200:
            data = r.json()
            balances = [{"asset": b["asset"], "free": float(b["free"]), "locked": float(b["locked"])} for b in data.get("balances", []) if float(b["free"]) > 0 or float(b["locked"]) > 0]
            return {"mode": "testnet" if USE_TESTNET else "live", "account_type": data.get("accountType", "SPOT"), "can_trade": data.get("canTrade", True), "balances": balances, "connected": True}
        return {"error": f"Binance error {r.status_code}", "mode": "paper"}
    except Exception as e:
        return {"error": str(e), "mode": "paper"}

# ---- MARKET DATA ----
def get_price(symbol="BTCUSDC"):
    """Get current price from Binance (fallback to simulated)"""
    try:
        r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol}, timeout=10)
        if r.status_code == 200:
            return {"symbol": symbol, "price": float(r.json()["price"]), "source": "binance"}
    except: pass
    fallback = {"BTCUSDC": 64000, "ETHUSDC": 3400, "SOLUSDC": 150, "DOGEUSDC": 0.14, "AVAXUSDC": 35, "LINKUSDC": 14, "MATICUSDC": 0.85, "DOTUSDC": 7.5}
    import random
    price = fallback.get(symbol, 100)
    return {"symbol": symbol, "price": price * (1 + (random.random() - 0.5) * 0.02), "source": "simulated"}

def get_all_prices(symbols=None):
    if symbols is None:
        symbols = ["BTCUSDC", "ETHUSDC", "SOLUSDC", "DOGEUSDC", "AVAXUSDC", "LINKUSDC", "MATICUSDC", "DOTUSDC"]
    try:
        r = requests.get(f"{BASE_URL}/api/v3/ticker/price", timeout=10)
        if r.status_code == 200:
            all_data = {p["symbol"]: float(p["price"]) for p in r.json()}
            return {s: {"price": all_data.get(s, 0), "source": "binance"} for s in symbols if s in all_data}
    except: pass
    import random
    base = {"BTCUSDC": 64000, "ETHUSDC": 3400, "SOLUSDC": 150, "DOGEUSDC": 0.14, "AVAXUSDC": 35, "LINKUSDC": 14, "MATICUSDC": 0.85, "DOTUSDC": 7.5}
    return {s: {"price": base.get(s, 100) * (1 + (random.random() - 0.5) * 0.02), "source": "simulated"} for s in (symbols or base.keys())}

# ---- TRADING ----
def place_order(symbol, side, quantity, order_type="MARKET", stop_loss_pct=None, take_profit_pct=None):
    ts = datetime.utcnow().isoformat()
    price_info = get_price(symbol)
    price = price_info["price"]
    
    if is_connected():
        try:
            params = {"symbol": symbol, "side": side.upper(), "type": order_type.upper(), "quantity": round(quantity, 6), "timestamp": int(time.time() * 1000)}
            if order_type.upper() == "LIMIT":
                params["price"] = round(price, 2)
                params["timeInForce"] = "GTC"
            signed = _sign_params(params)
            r = requests.post(f"{BASE_URL}/api/v3/order?{signed}", headers=_headers(), timeout=15)
            if r.status_code == 200:
                data = r.json()
                order = {"order_id": data["orderId"], "symbol": symbol, "side": side.upper(), "qty": quantity, "price": price, "status": data["status"], "type": "real", "exchange": "binance", "testnet": USE_TESTNET, "timestamp": ts}
                orders.append(order)
                save_orders()
                return {"success": True, "order": order, "mode": "testnet" if USE_TESTNET else "live"}
            return {"success": False, "error": f"Binance: {r.text}", "mode": "testnet" if USE_TESTNET else "live"}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "paper"}
    
    order = {"order_id": f"paper_{len(orders)+1}_{int(time.time())}", "symbol": symbol, "side": side.upper(), "qty": quantity, "price": price, "status": "FILLED", "type": "paper", "exchange": "simulated", "timestamp": ts, "stop_loss": stop_loss_pct, "take_profit": take_profit_pct}
    orders.append(order)
    save_orders()
    return {"success": True, "order": order, "mode": "paper"}

def place_buy(symbol, quantity, **kwargs):
    return place_order(symbol, "BUY", quantity, **kwargs)

def place_sell(symbol, quantity, **kwargs):
    return place_order(symbol, "SELL", quantity, **kwargs)

def get_open_orders(symbol=None):
    if is_connected():
        try:
            params = {"timestamp": int(time.time() * 1000)}
            if symbol: params["symbol"] = symbol
            signed = _sign_params(params)
            r = requests.get(f"{BASE_URL}/api/v3/openOrders?{signed}", headers=_headers(), timeout=15)
            if r.status_code == 200: return r.json()
        except: pass
    return [o for o in orders if o["status"] not in ("FILLED", "CANCELLED")]

def cancel_order(symbol, order_id):
    if is_connected():
        try:
            params = {"symbol": symbol, "orderId": order_id, "timestamp": int(time.time() * 1000)}
            signed = _sign_params(params)
            r = requests.delete(f"{BASE_URL}/api/v3/order?{signed}", headers=_headers(), timeout=15)
            if r.status_code == 200: return {"success": True, "binance": r.json()}
        except: pass
    for o in orders:
        if str(o["order_id"]) == str(order_id):
            o["status"] = "CANCELLED"
            save_orders()
            return {"success": True, "order": o}
    return {"success": False, "error": "Order not found"}

def get_order_history(symbol=None, limit=50):
    if is_connected():
        try:
            params = {"timestamp": int(time.time() * 1000), "limit": limit}
            if symbol: params["symbol"] = symbol
            signed = _sign_params(params)
            r = requests.get(f"{BASE_URL}/api/v3/allOrders?{signed}", headers=_headers(), timeout=15)
            if r.status_code == 200: return r.json()
        except: pass
    return orders[-limit:]
