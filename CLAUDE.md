# CLAUDE.md — Portfolio Monitor Agent
## Context for AI Assistants

This file gives Claude (or any AI assistant) complete, accurate context on this
project so it can make updates without needing lengthy re-explanation.
Last updated: March 2026.

---

## What This Project Does

An automated stock + options portfolio monitoring agent that runs every 30 minutes
on weekdays during US market hours (9:30am–4:00pm EST) via GitHub Actions.
No PC required — runs entirely in the cloud.

Each run:
1. Reads portfolio, watchlist, price levels, and wheel positions from Google Sheets
2. Fetches live price + RSI data from Twelve Data API
3. Evaluates stock signals (% gain/loss, RSI, chart level proximity)
4. Evaluates wheel strategy positions via Tastytrade OAuth2 API
5. Gets a short Claude AI narrative summary (3 sentences, under 800 chars)
6. Posts a formatted multi-message report to Discord

---

## File Structure

```
portfolio-monitor/
├── CLAUDE.md                        ← You are here
├── SETUP_GUIDE.md                   ← Step-by-step setup for first-time configuration
├── main.py                          ← Orchestrator — runs all agents in sequence
├── config.py                        ← All settings and environment variable loading
├── sheets_reader.py                 ← Reads all 4 Google Sheet tabs
├── price_fetcher.py                 ← Fetches price + RSI from Twelve Data API
├── signal_evaluator.py              ← Evaluates stock signals, returns alerts[]
├── options_fetcher.py               ← Tastytrade OAuth2 auth + option chains + Black-Scholes delta
├── wheel_evaluator.py               ← Wheel strategy logic → recommendations[]
├── claude_analyst.py                ← Calls Anthropic API for short narrative summary
├── discord_alerter.py               ← Formats and posts report to Discord (auto-chunks long msgs)
├── requirements.txt                 ← Python dependencies
└── .github/workflows/main.yml       ← GitHub Actions cron schedule
```

---

## Architecture / Data Flow

```
main.py (Orchestrator)
    │
    ├── sheets_reader.py     →  Google Sheets (4 tabs → portfolio, watchlist, levels, wheel)
    ├── price_fetcher.py     →  Twelve Data API (price + RSI for all symbols)
    ├── signal_evaluator.py  →  Stock signal rules → alerts[]
    ├── options_fetcher.py   →  Tastytrade OAuth2 API (chains + local delta calc)
    ├── wheel_evaluator.py   →  Phase-based wheel logic → recommendations[]
    ├── claude_analyst.py    →  Anthropic API claude-sonnet-4-6 (3-sentence summary)
    └── discord_alerter.py   →  Webhook → multiple Discord messages (auto-split at 1900 chars)
```

---

## Google Sheets Structure (4 tabs)

All tabs are read via a Google service account. The sheet must be shared with
the service account's `client_email` address or all reads will return 403/404.

### Tab 1: `Portfolio`
Tracks stock positions for P&L, RSI monitoring, and price alerts.
| Symbol | Entry Price | Shares | Alert % Threshold | Account |

- `Alert % Threshold` — triggers an alert if price moves this % from entry
- `Account` — informational only (e.g. "E-trade Rollover"), not used in logic

### Tab 2: `Watchlist`
Stocks to monitor for RSI signals only. Not tracked for P&L.
| Symbol | Alert % Threshold |

- `Alert % Threshold` column exists but is currently unused — RSI thresholds
  are global values set in `config.py` (RSI_OVERBOUGHT, RSI_OVERSOLD)

### Tab 3: `Levels`
Key price levels for proximity alerts.
| Symbol | Level Price | Type | Notes |

- `Type` accepts any string. `Support` and `Resistance` get special emoji in Discord.
  Other valid examples: TP1, TP2, Breakeven, Gap Fill
- Symbols can overlap with Portfolio and Wheel tabs — that is intentional

### Tab 4: `Wheel`
Tracks active wheel strategy positions.
| Symbol | Phase | Strike | Expiration | Contracts | Premium Collected | Cost Basis | Notes |

- Phase must be exactly one of (case-sensitive):
  - `Watching`  — no position open, scanning for a CSP entry
  - `CSP Open`  — have an open cash-secured put
  - `Assigned`  — got assigned shares, ready to find next CC
  - `CC Open`   — currently selling a covered call on assigned shares

- Expiration — must be YYYY-MM-DD format in PLAIN TEXT (not a date cell).
  In Google Sheets: Format → Number → Plain Text BEFORE entering the date,
  or Sheets will auto-convert it and break the date parser.

- Strike — the strike price as a number (e.g. 25)
- Premium Collected — per-share price received (e.g. 0.40, NOT $80 total)
- Cost Basis — effective cost per share after subtracting premiums collected
- Contracts — number of contracts (1 contract = 100 shares)

---

## Wheel Strategy Logic

### Phase Behavior
| Phase      | What the Agent Does |
|------------|---------------------|
| Watching   | Scans puts → finds best 0.20–0.25 delta CSP in 21–60 DTE window |
| CSP Open   | Monitors for ITM breach, proximity to strike, expiration countdown |
| Assigned   | Scans calls ABOVE cost basis → finds best CC to sell |
| CC Open    | Monitors for ITM breach (price > strike), expiration countdown |

### Delta Calculation
Delta is computed locally via Black-Scholes — NOT pulled from Tastytrade's
streaming Greeks (which require a websocket, not practical in GitHub Actions):
1. Pull bid/ask from Tastytrade option chain → compute mid price
2. Back-calculate IV from mid price via bisection method (100 iterations)
3. Use IV + inputs → Black-Scholes delta formula

### Candidate Ranking
Options are filtered to target delta range (0.20–0.25), then ranked by:
  annualized_return = (mid_price / strike) × (365 / DTE) × 100
For CC positions: cost_basis is used as the denominator instead of strike.
Top 5 candidates stored; top 3 shown in Discord; top 1 sent to Claude.

### The "Dead Zone" Situation
When assigned shares trade significantly below cost basis (e.g. GLXY at $20.63
with cost basis $27), no CC candidates will be found above cost basis.
This is CORRECT behavior — the system correctly refuses to recommend locking in
a loss. "No CC candidates found above cost basis" means the wheel is stuck and
the trader must decide: wait for recovery, sell a below-basis CC for income, or
close the position at a loss.

---

## Tastytrade API — CRITICAL: OAuth2 Only

⚠️  Username/password session token auth was DEPRECATED December 1, 2025.
The old POST /sessions endpoint no longer works. OAuth2 is now REQUIRED.

### Current Auth Method (options_fetcher.py)
```python
from tastytrade import Session
session = Session(client_secret, refresh_token)
```
No username or password used anywhere. Requires two GitHub secrets:
- TASTYTRADE_CLIENT_SECRET — from your OAuth app in Tastytrade account settings
- TASTYTRADE_REFRESH_TOKEN — from Tastytrade → OAuth Apps → Manage → Create Grant

### Getting the Refresh Token
1. Log into Tastytrade → Settings → API / OAuth Apps
2. Create or open your app → click Manage → Create Grant
3. Copy the refresh token — it is long-lived but not permanent (regenerate if it stops working)

---

## All APIs Summary

| API            | Purpose                  | Auth Method                          | Cost              |
|----------------|--------------------------|--------------------------------------|-------------------|
| Twelve Data    | Stock price + RSI        | API key (config.py)                  | Free (800/day)    |
| Tastytrade     | Options chains           | OAuth2 SDK Session(secret, token)    | Free              |
| Anthropic      | 3-sentence summary       | API key (config.py)                  | ~$0.05/day        |
| Google Sheets  | Portfolio data source    | Service account JSON                 | Free              |
| Discord        | Report delivery          | Webhook URL (config.py)              | Free              |

IMPORTANT: The Anthropic API key is from console.anthropic.com and is billed
separately from a claude.ai subscription. They are completely different products.

---

## GitHub Secrets Required (all 8)

| Secret Name                | Where to Get It |
|----------------------------|-----------------|
| CLAUDE_API_KEY             | console.anthropic.com → API Keys |
| TWELVE_DATA_API_KEY        | twelvedata.com → Dashboard |
| DISCORD_WEBHOOK_URL        | Discord channel → Edit → Integrations → Webhooks |
| GOOGLE_SHEET_ID            | Long ID string from the Google Sheet URL |
| GOOGLE_CREDENTIALS_JSON    | Full JSON content of service account key file |
| TASTYTRADE_CLIENT_ID       | Tastytrade → Settings → OAuth Apps → your app |
| TASTYTRADE_CLIENT_SECRET   | Tastytrade → Settings → OAuth Apps → your app |
| TASTYTRADE_REFRESH_TOKEN   | Tastytrade → OAuth Apps → Manage → Create Grant |

---

## Config Settings (config.py)

```python
WHEEL_DELTA_MIN     = 0.20   # Minimum delta for CSP/CC candidates
WHEEL_DELTA_MAX     = 0.25   # Maximum delta for CSP/CC candidates
WHEEL_MIN_DTE       = 21     # Minimum days to expiration to consider
WHEEL_MAX_DTE       = 60     # Maximum days to expiration to consider
RSI_OVERBOUGHT      = 70     # RSI above this triggers overbought alert
RSI_OVERSOLD        = 30     # RSI below this triggers oversold alert
LEVEL_PROXIMITY_PCT = 1.0    # Alert when price is within 1% of a chart level
```

All values can be changed directly in the GitHub repo — no local setup needed.
Changes take effect on the next scheduled run.

---

## Discord Message Format

The agent sends multiple Discord messages per run (intentionally, not one big message):
1. Header with timestamp
2. Claude's 3-sentence analysis
3. HIGH/MEDIUM/LOW stock alerts (if any), or "No alerts" message
4. Wheel position alerts (ITM warnings, expiration countdowns)
5. Wheel opportunity cards (top 3 candidates per assigned/watching position)
6. Position snapshot (price, % from entry, RSI for each Portfolio stock)
7. Divider line

discord_alerter.py auto-splits any single message exceeding 1900 characters
into multiple messages so Discord's 2000-character hard limit is never hit.

---

## Claude Analysis (claude_analyst.py)

- Model: claude-sonnet-4-6
- max_tokens: 350
- Prompt instructs: plain text only, no markdown headers or bullets, under 800 characters
- Output: 3 sentences (overall health / biggest risk or action / what to watch next session)
- Input to Claude: stock positions with entry/current/RSI, all alerts, wheel recs with cost basis

### Debugging "portfolio is empty" in Claude's response
If Claude says the portfolio is empty, check the GitHub Actions log for lines like:
  [claude_analyst] GLXY: price=20.63, rsi=44.0, entry=26.74
If price=None appears for all symbols, Twelve Data failed that run.
Positions are now always included in the prompt even when price fetch fails.

---

## Known Bugs Fixed — Do Not Reintroduce

| Bug | Fix Applied |
|-----|-------------|
| RSI f-string :.1f on None crashes at runtime | Use separate rsi_display variable with isinstance check |
| if data.get("price") skips stocks at $0.00 | Changed to if price is not None |
| Tastytrade username/password auth → 401 | Switched to OAuth2 SDK Session(secret, token) |
| asyncio.run() "Event loop is closed" on multiple symbols | All wheel evals run inside single asyncio.run(_evaluate_all(...)) |
| Expiration date auto-formatted by Google Sheets | Format column as Plain Text before entering YYYY-MM-DD |
| Discord 2000-char limit error (400 response) | send_discord_message() now auto-chunks at 1900 chars |
| options_fetcher has no attribute find_best_wheel_option | GitHub had old options_fetcher.py — always push all files |
| Google Sheets 403/404 | Sheet not shared with service account client_email |
| Duplicate column key error in get_all_records() | Extra blank columns in Sheet caused key collisions — delete them |

---

## User Context

- Python level: Beginner — keep all code simple and heavily commented
- Strategy: Wheel (sell CSP → get assigned → sell CC → repeat)
- Accounts: E-trade Rollover (main stock holdings), Tastytrade (options), Robinhood
- Tastytrade: used for options API only — OAuth2 required, no username/password
- Deployment: GitHub Actions only — no local server, no Docker, no cron job
- Alerts: Discord only
- Position tracking: Google Sheets (user updates manually)
- API budget: Twelve Data free tier (800 credits/day) — avoid redundant calls

---

## Current Positions (March 2026 — update this section when positions change)

### Portfolio Tab
| Symbol | Entry    | Shares | Account          |
|--------|----------|--------|------------------|
| GLXY   | $26.74   | 1230   | E-trade Rollover |
| CRWV   | $95.5666 | 300    | E-trade Rollover |

### Wheel Tab
| Symbol | Phase    | Strike | Expiration | Contracts | Premium | Cost Basis |
|--------|----------|--------|------------|-----------|---------|------------|
| GLXY   | Assigned | —      | —          | 3*        | —       | $27.00     |
| CRWV   | Assigned | —      | —          | 2         | —       | $95.00     |
| GLXY   | CC Open  | $25    | 2026-03-27 | 2         | $0.40   | $27.00     |

*GLXY Assigned: sheet shows 9 contracts but correct value is 3
 (1230 shares total - 200 covered by CC = ~300 shares remaining = 3 contracts)

### Market Context (March 2026)
Both GLXY ($20.63) and CRWV ($79.87) are trading well below their cost bases.
No CC candidates exist above cost basis for either — correct dead zone behavior.
GLXY CC Open at $25 strike is OTM (current $20.63), expiring 2026-03-27.

---

## How to Extend the Project

### Add a new stock signal type
Edit signal_evaluator.py, return a dict with:
{ "type": str, "symbol": str, "message": str, "urgency": "HIGH"|"MEDIUM"|"LOW" }

### Add a new wheel phase
Add elif phase == "NewPhase": block in wheel_evaluator.py
Return dict with keys: symbol, phase, type, message, urgency, candidates, cost_basis

### Add a new Google Sheet column
Update the relevant reader function in sheets_reader.py and add the new key to
the returned dict. Then use it wherever needed downstream.

### Change delta target or DTE range
Edit values in config.py directly on GitHub — takes effect on next run.

### Add a new brokerage API
Create {broker}_fetcher.py following the pattern of options_fetcher.py,
import it in main.py, and add any new secrets to GitHub → Settings → Secrets → Actions.
