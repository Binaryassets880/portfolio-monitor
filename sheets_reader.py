# ============================================================
# sheets_reader.py — Reads your portfolio data from Google Sheets
# ============================================================

import gspread
from google.oauth2.service_account import Credentials
import json
import os
import config

def get_sheets_client():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS_JSON environment variable not set.")
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def read_portfolio():
    """
    Portfolio tab columns:
    Symbol | Entry Price | Shares | Alert % Threshold
    """
    client = get_sheets_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    rows = sheet.worksheet(config.PORTFOLIO_TAB).get_all_records()
    portfolio = []
    for row in rows:
        if row.get("Symbol"):
            portfolio.append({
                "symbol":    row["Symbol"].upper().strip(),
                "entry":     float(row.get("Entry Price", 0)),
                "shares":    float(row.get("Shares", 0)),
                "alert_pct": float(row.get("Alert % Threshold", 5.0)),
            })
    return portfolio

def read_watchlist():
    """
    Watchlist tab columns:
    Symbol | Alert % Threshold
    """
    client = get_sheets_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    rows = sheet.worksheet(config.WATCHLIST_TAB).get_all_records()
    watchlist = []
    for row in rows:
        if row.get("Symbol"):
            watchlist.append({
                "symbol":    row["Symbol"].upper().strip(),
                "alert_pct": float(row.get("Alert % Threshold", 3.0)),
            })
    return watchlist

def read_levels():
    """
    Levels tab columns:
    Symbol | Level Price | Type | Notes
    """
    client = get_sheets_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    rows = sheet.worksheet(config.LEVELS_TAB).get_all_records()
    levels = []
    for row in rows:
        if row.get("Symbol") and row.get("Level Price"):
            levels.append({
                "symbol": row["Symbol"].upper().strip(),
                "price":  float(row["Level Price"]),
                "type":   row.get("Type", "Level").strip(),
                "notes":  row.get("Notes", "").strip(),
            })
    return levels

def read_wheel():
    """
    Wheel tab columns:
    Symbol | Phase | Strike | Expiration | Contracts | Premium Collected | Cost Basis | Notes

    Phase must be one of:
      Watching   — looking for CSP entry
      CSP Open   — currently have an open CSP
      Assigned   — got assigned shares
      CC Open    — currently selling a covered call

    Expiration format: YYYY-MM-DD
    """
    client = get_sheets_client()
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)

    try:
        worksheet = sheet.worksheet(config.WHEEL_TAB)
    except Exception:
        print("  Note: No 'Wheel' tab found in Google Sheet. Skipping wheel evaluation.")
        return []

    rows = worksheet.get_all_records()
    wheel = []
    for row in rows:
        if row.get("Symbol") and row.get("Phase"):
            wheel.append({
                "symbol":            row["Symbol"].upper().strip(),
                "phase":             row["Phase"].strip(),
                "strike":            float(row.get("Strike", 0) or 0),
                "expiration":        str(row.get("Expiration", "")).strip(),
                "contracts":         int(row.get("Contracts", 1) or 1),
                "premium_collected": float(row.get("Premium Collected", 0) or 0),
                "cost_basis":        float(row.get("Cost Basis", 0) or 0),
                "notes":             str(row.get("Notes", "")).strip(),
            })
    return wheel
