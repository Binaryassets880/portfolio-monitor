# ============================================================
# sheets_reader.py — Reads your portfolio data from Google Sheets
# ============================================================

import gspread
from google.oauth2.service_account import Credentials
import json
import os
import config

def get_sheets_client():
    """Connect to Google Sheets using your service account credentials."""
    # The credentials JSON is stored as a GitHub Secret (see setup guide)
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS_JSON environment variable not set.")
    
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def read_portfolio():
    """
    Read your Portfolio tab.
    Expected columns: Symbol | Entry Price | Shares | Alert % Threshold
    Returns a list of dicts.
    """
    client = get_sheets_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    worksheet = sheet.worksheet(config.PORTFOLIO_TAB)
    rows = worksheet.get_all_records()  # Reads header row automatically
    
    portfolio = []
    for row in rows:
        if row.get("Symbol"):  # Skip empty rows
            portfolio.append({
                "symbol":    row["Symbol"].upper().strip(),
                "entry":     float(row.get("Entry Price", 0)),
                "shares":    float(row.get("Shares", 0)),
                "alert_pct": float(row.get("Alert % Threshold", 5.0)),  # Default 5%
            })
    return portfolio

def read_watchlist():
    """
    Read your Watchlist tab.
    Expected columns: Symbol | Alert % Threshold
    Returns a list of dicts.
    """
    client = get_sheets_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    worksheet = sheet.worksheet(config.WATCHLIST_TAB)
    rows = worksheet.get_all_records()
    
    watchlist = []
    for row in rows:
        if row.get("Symbol"):
            watchlist.append({
                "symbol":    row["Symbol"].upper().strip(),
                "alert_pct": float(row.get("Alert % Threshold", 3.0)),  # Default 3%
            })
    return watchlist

def read_levels():
    """
    Read your Levels tab (your chart-based price levels).
    Expected columns: Symbol | Level Price | Type | Notes
    Type should be: Support or Resistance
    Returns a list of dicts.
    """
    client = get_sheets_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    worksheet = sheet.worksheet(config.LEVELS_TAB)
    rows = worksheet.get_all_records()
    
    levels = []
    for row in rows:
        if row.get("Symbol") and row.get("Level Price"):
            levels.append({
                "symbol": row["Symbol"].upper().strip(),
                "price":  float(row["Level Price"]),
                "type":   row.get("Type", "Level").strip(),    # Support / Resistance
                "notes":  row.get("Notes", "").strip(),
            })
    return levels
