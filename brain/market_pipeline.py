"""📊 Market data pipeline — CoinGecko API + simulated fallback"""
import requests, random, math, time
from datetime import datetime
COINGECKO = "https://api.coingecko.com/api/v3"
ASSETS = [
    {"symbol": "BTC-USD", "name": "Bitcoin", "coingecko": "bitcoin"},
    {"symbol": "ETH-USD", "name": "Ethereum", "coingecko": "ethereum"},
    {"symbol": "SOL-USD", "name": "Solana", "coingecko": "solana"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "coingecko": "dogecoin"},
    {"symbol": "AVAX-USD", "name": "Avalanche", "coingecko": "avalanche-2"},
    {"symbol": "LINK-USD", "name": "Chainlink", "coingecko": "chainlink"},
    {"symbol": "MATIC-USD", "name": "Polygon", "coingecko": "matic-network"},
    {"symbol": "DOT-USD", "name": "Polkadot", "coingecko": "polkadot"},
]
FALLBACK = {a["symbol"]: {"price": 0, "change_24h": 0} for a in ASSETS}

def fetch_real_prices():
    try:
        ids = ",".join(a["coingecko"] for a in ASSETS)
        r = requests.get(f"{COINGECKO}/simple/price", params={"ids": ids, "vs_currencies": "usd", "include_24hr_change": "true"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {a["symbol"]: {"price": data.get(a["coingecko"], {}).get("usd", 100), "change_24h": data.get(a["coingecko"], {}).get("usd_24h_change", 0) or 0} for a in ASSETS}
    except: pass
    base = {"BTC-USD": 64000, "ETH-USD": 3400, "SOL-USD": 150, "DOGE-USD": 0.14, "AVAX-USD": 35, "LINK-USD": 14, "MATIC-USD": 0.85, "DOT-USD": 7.5}
    for a in ASSETS:
        sym = a["symbol"]
        if sym not in FALLBACK or FALLBACK[sym]["price"] == 0:
            FALLBACK[sym] = {"price": base.get(sym, 100), "change_24h": 0}
        else:
            old = FALLBACK[sym]["price"]
            FALLBACK[sym] = {"price": max(old + (random.random() - 0.48) * old * 0.02, 0.001), "change_24h": (random.random() - 0.5) * 10}
    return dict(FALLBACK)

def generate_features(symbol, price_data, brain_conf=0.5):
    rsi = 30 + random.random() * 40
    macd = (random.random() - 0.5) * 2
    bb = (random.random() - 0.5) * 2
    return [(random.random() - 0.5) * 0.02, (random.random() - 0.5) * 0.05, (random.random() - 0.5) * 0.1, (random.random() - 0.5) * 0.2, rsi / 100, macd / 4 + 0.5, bb / 2 + 0.5, random.random(), random.random(), 0.5 + (random.random() - 0.5) * 0.3, 0.5 + (random.random() - 0.5) * 0.3, 0.5 + (random.random() - 0.5) * 0.3, random.random(), random.random(), random.random(), brain_conf - 0.5, math.sin(time.time() / 86400 * math.pi * 2) / 2 + 0.5, math.cos(time.time() / 86400 * math.pi * 2) / 2 + 0.5, random.random(), random.random()]

def scan_market(brain):
    prices = fetch_real_prices()
    results, buy_sig, sell_sig = [], 0, 0
    for a in ASSETS:
        sym = a["symbol"]
        pi = prices.get(sym, {"price": 100, "change_24h": 0})
        feats = generate_features(sym, pi, brain.confidence)
        dec = brain.decide(feats)
        if dec["signal"] == "buy": buy_sig += 1
        elif dec["signal"] == "sell": sell_sig += 1
        results.append({"symbol": sym, "name": a["name"], "price": round(pi["price"], 4), "change_24h": round(pi["change_24h"], 2), "signal": dec["signal"], "confidence": dec["confidence"], "buy_votes": dec["buy_votes"], "sell_votes": dec["sell_votes"]})
    return {"assets": results, "buy_signals": buy_sig, "sell_signals": sell_sig, "fear_greed": int(brain.confidence * 100), "total": len(results), "timestamp": datetime.utcnow().isoformat()}
