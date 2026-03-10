# ============================================================
# price_fetcher.py — Gets current price and RSI from Twelve Data
# ============================================================

import requests
import config

BASE_URL = "https://api.twelvedata.com"

def get_price(symbol):
    """Fetch the current price for a stock symbol."""
    url = f"{BASE_URL}/price"
    params = {
        "symbol": symbol,
        "apikey": config.TWELVE_DATA_API_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if "price" in data:
        return float(data["price"])
    else:
        print(f"  Warning: Could not fetch price for {symbol}. Response: {data}")
        return None

def get_rsi(symbol, period=14):
    """
    Fetch the current RSI for a stock symbol.
    Period 14 is the standard setting most traders use.
    """
    url = f"{BASE_URL}/rsi"
    params = {
        "symbol":   symbol,
        "interval": "1day",
        "time_period": period,
        "apikey":   config.TWELVE_DATA_API_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    try:
        # Twelve Data returns a list of values — we want the most recent one
        rsi_value = float(data["values"][0]["rsi"])
        return rsi_value
    except (KeyError, IndexError):
        print(f"  Warning: Could not fetch RSI for {symbol}. Response: {data}")
        return None

def get_all_data(symbols):
    """
    Fetch price and RSI for a list of symbols.
    Returns a dict like: { "AAPL": { "price": 182.5, "rsi": 65.3 }, ... }
    """
    results = {}
    for symbol in symbols:
        print(f"  Fetching data for {symbol}...")
        price = get_price(symbol)
        rsi   = get_rsi(symbol)
        results[symbol] = {
            "price": price,
            "rsi":   rsi,
        }
    return results
