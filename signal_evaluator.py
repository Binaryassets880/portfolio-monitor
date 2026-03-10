# ============================================================
# signal_evaluator.py — Checks your rules and generates alerts
# ============================================================

import config

def check_signals(portfolio, watchlist, levels, market_data):
    """
    Runs all signal checks and returns a list of alerts.
    Each alert is a dict describing what triggered.
    """
    alerts = []

    # --------------------------------------------------------
    # 1. Check Portfolio positions — % gain/loss from entry
    # --------------------------------------------------------
    for stock in portfolio:
        symbol = stock["symbol"]
        entry  = stock["entry"]
        data   = market_data.get(symbol)
        
        if not data or data["price"] is None or entry == 0:
            continue
        
        current_price = data["price"]
        pct_change = ((current_price - entry) / entry) * 100
        threshold  = stock["alert_pct"]
        
        if abs(pct_change) >= threshold:
            direction = "UP" if pct_change > 0 else "DOWN"
            alerts.append({
                "type":    "GAIN_LOSS",
                "symbol":  symbol,
                "message": f"{symbol} is {direction} {abs(pct_change):.1f}% from your entry of ${entry:.2f} (now ${current_price:.2f})",
                "urgency": "HIGH" if abs(pct_change) >= threshold * 2 else "MEDIUM",
            })

    # --------------------------------------------------------
    # 2. Check Watchlist — % daily move alert
    # --------------------------------------------------------
    # For watchlist items, we flag large intraday moves
    for stock in watchlist:
        symbol = stock["symbol"]
        data   = market_data.get(symbol)
        
        if not data or data["price"] is None:
            continue
        
        # Note: Twelve Data's free tier doesn't include prev close in price endpoint
        # We use RSI as a proxy signal for watchlist items instead
        rsi = data.get("rsi")
        if rsi:
            if rsi >= config.RSI_OVERBOUGHT:
                alerts.append({
                    "type":    "RSI_WATCHLIST",
                    "symbol":  symbol,
                    "message": f"👀 WATCHLIST — {symbol} RSI is {rsi:.1f} (OVERBOUGHT above {config.RSI_OVERBOUGHT}). Consider watching for entry.",
                    "urgency": "LOW",
                })
            elif rsi <= config.RSI_OVERSOLD:
                alerts.append({
                    "type":    "RSI_WATCHLIST",
                    "symbol":  symbol,
                    "message": f"👀 WATCHLIST — {symbol} RSI is {rsi:.1f} (OVERSOLD below {config.RSI_OVERSOLD}). Potential buy opportunity.",
                    "urgency": "LOW",
                })

    # --------------------------------------------------------
    # 3. Check RSI for Portfolio positions
    # --------------------------------------------------------
    for stock in portfolio:
        symbol = stock["symbol"]
        data   = market_data.get(symbol)
        
        if not data or data.get("rsi") is None:
            continue
        
        rsi = data["rsi"]
        
        if rsi >= config.RSI_OVERBOUGHT:
            alerts.append({
                "type":    "RSI_PORTFOLIO",
                "symbol":  symbol,
                "message": f"📈 {symbol} RSI hit {rsi:.1f} — OVERBOUGHT (above {config.RSI_OVERBOUGHT}). Consider taking profits.",
                "urgency": "HIGH",
            })
        elif rsi <= config.RSI_OVERSOLD:
            alerts.append({
                "type":    "RSI_PORTFOLIO",
                "symbol":  symbol,
                "message": f"📉 {symbol} RSI hit {rsi:.1f} — OVERSOLD (below {config.RSI_OVERSOLD}). Possible reversal coming.",
                "urgency": "MEDIUM",
            })

    # --------------------------------------------------------
    # 4. Check Chart-Based Price Levels (from your Levels tab)
    # --------------------------------------------------------
    for level in levels:
        symbol      = level["symbol"]
        level_price = level["price"]
        level_type  = level["type"]
        notes       = level["notes"]
        data        = market_data.get(symbol)
        
        if not data or data["price"] is None:
            continue
        
        current_price = data["price"]
        proximity_pct = abs((current_price - level_price) / level_price) * 100
        
        if proximity_pct <= config.LEVEL_PROXIMITY_PCT:
            emoji = "🛡️" if level_type == "Support" else "🚧"
            note_text = f" ({notes})" if notes else ""
            alerts.append({
                "type":    "PRICE_LEVEL",
                "symbol":  symbol,
                "message": f"{emoji} {symbol} is within {proximity_pct:.2f}% of your {level_type} level at ${level_price:.2f}{note_text}. Current: ${current_price:.2f}",
                "urgency": "HIGH",
            })

    return alerts
