"""📊 Market data pipeline — Binance API + CoinGecko fallback"""
import requests, random, math, time
from datetime import datetime

COINGECKO = "https://api.coingecko.com/api/v3"
ASSETS = [
    {"symbol": "BTC-USD", "name": "Bitcoin", "coingecko": "bitcoin", "binance": "BTCUSDC"},
    {"symbol": "ETH-USD", "name": "Ethereum", "coingecko": "ethereum", "binance": "ETHUSDC"},
    {"symbol": "SOL-USD", "name": "Solana", "coingecko": "solana", "binance": "SOLUSDC"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "coingecko": "dogecoin", "binance": "DOGEUSDC"},
    {"symbol": "AVAX-USD", "name": "Avalanche", "coingecko": "avalanche-2", "binance": "AVAXUSDC"},
    {"symbol": "LINK-USD", "name": "Chainlink", "coingecko": "chainlink", "binance": "LINKUSDC"},
    {"symbol": "MATIC-USD", "name": "Polygon", "coingecko": "matic-network", "binance": "MATICUSDC"},
    {"symbol": "DOT-USD", "name": "Polkadot", "coingecko": "polkadot", "binance": "DOTUSDC"},
]
FALLBACK = {a["symbol"]: {"price": 0, "change_24h": 0, "source": "simulated"} for a in ASSETS}

def fetch_real_prices():
    """Try Binance first, then CoinGecko, then simulated"""
    # Priority 1: Try Binance public ticker
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5)
        if r.status_code == 200:
            all_data = {p["symbol"]: float(p["price"]) for p in r.json()}
            result = {}
            for a in ASSETS:
                bs = a.get("binance", "")
                price = all_data.get(bs, None)
                if price:
                    result[a["symbol"]] = {"price": price, "change_24h": 0, "source": "binance"}
            if result:
                return result
    except: pass
    
    # Priority 2: CoinGecko
    try:
        ids = ",".join(a["coingecko"] for a in ASSETS)
        r = requests.get(f"{COINGECKO}/simple/price", params={"ids": ids, "vs_currencies": "usd", "include_24hr_change": "true"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {a["symbol"]: {"price": data.get(a["coingecko"], {}).get("usd", 100), "change_24h": data.get(a["coingecko"], {}).get("usd_24h_change", 0) or 0, "source": "coingecko"} for a in ASSETS}
    except: pass
    
    # Priority 3: Simulated
    base = {"BTC-USD": 64000, "ETH-USD": 3400, "SOL-USD": 150, "DOGE-USD": 0.14, "AVAX-USD": 35, "LINK-USD": 14, "MATIC-USD": 0.85, "DOT-USD": 7.5}
    for a in ASSETS:
        sym = a["symbol"]
        if sym not in FALLBACK or FALLBACK[sym]["price"] == 0:
            FALLBACK[sym] = {"price": base.get(sym, 100), "change_24h": 0, "source": "simulated"}
        else:
            old = FALLBACK[sym]["price"]
            FALLBACK[sym] = {"price": max(old + (random.random() - 0.48) * old * 0.02, 0.001), "change_24h": (random.random() - 0.5) * 10, "source": "simulated"}
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
        results.append({"symbol": sym, "name": a["name"], "binance_symbol": a.get("binance", ""), "price": round(pi["price"], 4), "change_24h": round(pi.get("change_24h", 0), 2), "source": pi.get("source", "simulated"), "signal": dec["signal"], "confidence": dec["confidence"], "buy_votes": dec["buy_votes"], "sell_votes": dec["sell_votes"]})
    return {"assets": results, "buy_signals": buy_sig, "sell_signals": sell_sig, "fear_greed": int(brain.confidence * 100), "total": len(results), "timestamp": datetime.utcnow().isoformat()}
