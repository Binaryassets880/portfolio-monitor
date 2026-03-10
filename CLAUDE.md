# CLAUDE.md — Portfolio Monitor Agent
## Context for AI Assistants

This file exists to give Claude (or any AI assistant) full context on this project
so it can make accurate updates without needing lengthy re-explanation.

---

## What This Project Does

An automated stock + options portfolio monitoring agent that runs every 30 minutes
on weekdays during US market hours (9:30am–4:00pm EST) via GitHub Actions.
No PC required — runs entirely in the cloud for free.

Each run:
1. Reads portfolio, watchlist, price levels, and wheel positions from Google Sheets
2. Fetches live price + RSI data from Twelve Data API
3. Evaluates stock signals (% gain/loss, RSI, chart level proximity)
4. Evaluates wheel strategy positions via Tastytrade options chain API
5. Gets Claude AI narrative summary
6. Posts formatted report to Discord

---

## File Structure

```
portfolio-monitor/
├── CLAUDE.md                        ← You are here
├── SETUP_GUIDE.md                   ← Step-by-step setup instructions
├── main.py                          ← Orchestrator — runs all agents in sequence
├── config.py                        ← All settings and environment variable loading
├── sheets_reader.py                 ← Reads all 4 Google Sheet tabs
├── price_fetcher.py                 ← Fetches price + RSI from Twelve Data API
├── signal_evaluator.py              ← Evaluates stock signals, returns alerts[]
├── options_fetcher.py               ← Tastytrade auth + option chain + delta calc
├── wheel_evaluator.py               ← Wheel strategy logic (CSP/CC recommendations)
├── claude_analyst.py                ← Calls Anthropic API for narrative summary
├── discord_alerter.py               ← Formats and posts report to Discord
├── requirements.txt                 ← Python dependencies
└── .github/workflows/main.yml       ← GitHub Actions schedule
```

---

## Architecture

```
main.py (Orchestrator)
    │
    ├── sheets_reader.py     →  Google Sheets (portfolio, watchlist, levels, wheel)
    ├── price_fetcher.py     →  Twelve Data API (price + RSI)
    ├── signal_evaluator.py  →  Stock signal rules → alerts[]
    ├── options_fetcher.py   →  Tastytrade API (option chains + delta calc)
    ├── wheel_evaluator.py   →  Wheel strategy logic → recommendations[]
    ├── claude_analyst.py    →  Anthropic API (narrative summary)
    └── discord_alerter.py   →  Discord webhook (formatted report)
```

---

## Google Sheets Structure (4 tabs)

### Tab 1: `Portfolio`
| Symbol | Entry Price | Shares | Alert % Threshold |

### Tab 2: `Watchlist`
| Symbol | Alert % Threshold |

### Tab 3: `Levels`
| Symbol | Level Price | Type (Support/Resistance) | Notes |

### Tab 4: `Wheel`
| Symbol | Phase | Strike | Expiration | Contracts | Premium Collected | Cost Basis | Notes |

**Phase values (must be exact):**
- `Watching` — no position open, scanning for CSP entry
- `CSP Open` — currently have an open cash-secured put
- `Assigned` — got assigned shares, ready to sell CC
- `CC Open` — currently selling a covered call

**Expiration format:** `YYYY-MM-DD`

---

## Wheel Strategy Logic

### Delta Targeting
- Target: 0.20–0.25 delta (configurable in config.py)
- Delta calculated via Black-Scholes using mid-price to back-calculate IV
- Scans all expirations between WHEEL_MIN_DTE (21) and WHEEL_MAX_DTE (60)
- Ranks candidates by annualized premium return

### Phase Behavior
| Phase | Agent Action |
|-------|-------------|
| Watching | Scans puts across expirations → finds best 0.20-0.25 delta CSP |
| CSP Open | Monitors for ITM breach, proximity alerts, expiration countdown |
| Assigned | Confirms assignment, scans calls above cost basis → finds best CC |
| CC Open | Monitors for ITM breach (call above strike), expiration countdown |

### Annualized Return Calculation
`(mid_price / strike) × (365 / DTE) × 100`
For CC: uses cost_basis as denominator instead of strike

---

## Options API — Tastytrade

- **Auth:** POST `/sessions` with username/password → returns `session-token`
- **Option chain:** GET `/option-chains/{symbol}` with `?expiration-date=YYYY-MM-DD`
- **Expirations:** GET `/option-chains/{symbol}/option-expirations`
- **Base URL:** `https://api.tastytrade.com`
- **Session token:** passed in `Authorization` header

Delta is calculated locally via Black-Scholes (not from Tastytrade directly):
1. Get bid/ask from chain → calculate mid price
2. Use bisection to back-calculate IV from mid price
3. Use IV + other inputs to calculate delta via Black-Scholes

---

## APIs Used

| API | Purpose | Auth Method | Cost |
|-----|---------|-------------|------|
| Twelve Data | Stock price + RSI | API key | Free (800 credits/day) |
| Tastytrade | Options chains | Username + password | Free (account required) |
| Anthropic Claude | Narrative analysis | API key | ~$0.05/day |
| Google Sheets | Portfolio data | Service account JSON | Free |
| Discord | Alerts delivery | Webhook URL | Free |

---

## GitHub Secrets Required

| Secret Name | Description |
|-------------|-------------|
| `CLAUDE_API_KEY` | From console.anthropic.com (separate from claude.ai) |
| `TWELVE_DATA_API_KEY` | From twelvedata.com |
| `DISCORD_WEBHOOK_URL` | From Discord channel → Integrations → Webhooks |
| `GOOGLE_SHEET_ID` | Long ID string from Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | Full JSON content of service account key |
| `TASTYTRADE_USERNAME` | Tastytrade login email |
| `TASTYTRADE_PASSWORD` | Tastytrade password |

---

## User Context

- **Python level:** Beginner — keep all code simple and heavily commented
- **Strategy:** Wheel (CSP → assignment → CC → repeat)
- **Delta target:** 0.20–0.25 (flexible, can adjust in config.py)
- **DTE preference:** Flexible (21–60 DTE range, agent picks best)
- **Brokers:** Tastytrade (for options API), Robinhood/Etrade (no API)
- **Data:** Google Sheets for all position tracking
- **Alerts:** Discord only
- **Deployment:** GitHub Actions only (no local server)
- **API constraint:** Free tier limits — avoid high-frequency API calls

---

## Config Settings (config.py)

```python
WHEEL_DELTA_MIN = 0.20   # Change to adjust delta target floor
WHEEL_DELTA_MAX = 0.25   # Change to adjust delta target ceiling
WHEEL_MIN_DTE   = 21     # Minimum DTE to consider
WHEEL_MAX_DTE   = 60     # Maximum DTE to consider
RSI_OVERBOUGHT  = 70
RSI_OVERSOLD    = 30
LEVEL_PROXIMITY_PCT = 1.0
```

---

## Known Issues / History

- RSI f-string formatting bug: use `rsi_display` variable instead of inline format spec
- Discord 401: webhook URL must start with `https://discord.com/api/webhooks/...`
- Google Sheets 404: sheet must be shared with service account client_email
- Claude API is separate from claude.ai — requires console.anthropic.com credits
- Tastytrade API endpoint paths may need adjustment based on actual API responses —
  check error messages carefully if chain fetch fails

---

## How to Add New Features

### New signal type → add to `signal_evaluator.py`
Return dict with keys: `type`, `symbol`, `message`, `urgency` (HIGH/MEDIUM/LOW)

### New wheel phase → add elif block in `wheel_evaluator.py`
Follow the same pattern as existing phase evaluators

### New sheet column → update `sheets_reader.py` reader function

### Change DTE/delta range → edit `config.py` values directly on GitHub

### Add new broker API → create `{broker}_fetcher.py`, import in `main.py`
