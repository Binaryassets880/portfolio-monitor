# ============================================================
# config.py — All your settings live here
# ============================================================

import os

# --- API Keys ---
CLAUDE_API_KEY       = os.getenv("CLAUDE_API_KEY",       "paste-your-claude-key-here")
TWELVE_DATA_API_KEY  = os.getenv("TWELVE_DATA_API_KEY",  "paste-your-twelve-data-key-here")
DISCORD_WEBHOOK_URL  = os.getenv("DISCORD_WEBHOOK_URL",  "paste-your-discord-webhook-url-here")

# --- Tastytrade ---
TASTYTRADE_USERNAME = os.getenv("TASTYTRADE_USERNAME", "")
TASTYTRADE_PASSWORD = os.getenv("TASTYTRADE_PASSWORD", "")

# --- Google Sheets ---
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "paste-your-sheet-id-here")
PORTFOLIO_TAB   = "Portfolio"
WATCHLIST_TAB   = "Watchlist"
LEVELS_TAB      = "Levels"
WHEEL_TAB       = "Wheel"  # ← NEW

# --- RSI Signal Thresholds ---
RSI_OVERBOUGHT = 70
RSI_OVERSOLD   = 30

# --- Price Level Proximity ---
LEVEL_PROXIMITY_PCT = 1.0  # Alert when within 1% of a chart level

# --- Wheel Strategy Settings ---
WHEEL_DELTA_MIN = 0.20   # Minimum delta target for CSP/CC
WHEEL_DELTA_MAX = 0.25   # Maximum delta target for CSP/CC
WHEEL_MIN_DTE   = 21     # Minimum days to expiration to consider
WHEEL_MAX_DTE   = 60     # Maximum days to expiration to consider
