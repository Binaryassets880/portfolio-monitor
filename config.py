# ============================================================
# config.py — All your settings live here
# ============================================================
# Fill in your API keys and preferences below.
# Never share this file publicly (it contains secrets).
# When deploying to GitHub, these will be stored as
# GitHub Secrets instead (the setup guide explains this).

import os

# --- API Keys ---
# These will be loaded from environment variables when running in GitHub Actions.
# For local testing, you can temporarily paste your keys directly here.

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "paste-your-claude-key-here")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "paste-your-twelve-data-key-here")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "paste-your-discord-webhook-url-here")

# --- Google Sheets ---
# The ID is the long string in your Google Sheet URL:
# https://docs.google.com/spreadsheets/d/  THIS PART  /edit
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "paste-your-sheet-id-here")

# Tab names in your Google Sheet (change if you rename them)
PORTFOLIO_TAB = "Portfolio"
WATCHLIST_TAB = "Watchlist"
LEVELS_TAB    = "Levels"

# --- Signal Thresholds ---
# RSI: alert when a stock is overbought (too high) or oversold (too low)
RSI_OVERBOUGHT = 70   # Alert when RSI goes above this
RSI_OVERSOLD   = 30   # Alert when RSI goes below this

# Price Levels: alert when price is within this % of a key level you've set
LEVEL_PROXIMITY_PCT = 1.0  # e.g. 1.0 = alert when within 1% of your level

# --- Schedule ---
# These control when the agent runs (handled in GitHub Actions)
# Just here for reference — market hours are 9:30am–4:00pm EST
MARKET_OPEN_HOUR  = 9
MARKET_CLOSE_HOUR = 16
