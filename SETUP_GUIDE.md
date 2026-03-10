# 📈 Portfolio Monitor Agent — Setup Guide

Follow these steps in order. It looks like a lot, but each step is simple.
Total setup time: ~30–45 minutes.

---

## What You're Building

A system that runs automatically every 30 minutes during market hours (M–F, 9:30am–4pm EST) and sends you a Discord report with:
- Price & RSI updates on your positions
- Alerts when RSI is overbought/oversold
- Alerts when price is near your chart levels
- A plain-English summary from Claude

---

## Step 1: Set Up Your Google Sheet

1. Create a new Google Sheet
2. Create **3 tabs** named exactly:
   - `Portfolio`
   - `Watchlist`
   - `Levels`

**Portfolio tab — add these column headers in Row 1:**
| Symbol | Entry Price | Shares | Alert % Threshold |
|--------|-------------|--------|-------------------|
| AAPL   | 150.00      | 10     | 5                 |
| TSLA   | 220.00      | 5      | 7                 |

> `Alert % Threshold` = how far from your entry price before you get alerted (e.g., 5 = alert when up or down 5%)

**Watchlist tab — add these column headers in Row 1:**
| Symbol | Alert % Threshold |
|--------|-------------------|
| NVDA   | 3                 |
| META   | 3                 |

**Levels tab — add these column headers in Row 1:**
| Symbol | Level Price | Type       | Notes              |
|--------|-------------|------------|--------------------|
| AAPL   | 175.00      | Resistance | Previous all-time high |
| AAPL   | 155.00      | Support    | 50-day MA           |

> `Type` must be exactly `Support` or `Resistance`

3. Copy your **Sheet ID** from the URL:
   `https://docs.google.com/spreadsheets/d/` **← THIS LONG STRING →** `/edit`
   Save it — you'll need it later.

---

## Step 2: Set Up Google Sheets API Access

This lets the script read your sheet automatically.

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (name it anything, e.g. "Portfolio Monitor")
3. In the search bar, search for **"Google Sheets API"** and click **Enable**
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → Service Account**
   - Name it anything (e.g. "portfolio-reader")
   - Click through to finish
6. Click on your new service account, go to the **Keys** tab
7. Click **Add Key → Create New Key → JSON** — this downloads a `.json` file
8. Open that `.json` file in a text editor and copy the **entire contents**
   - This becomes your `GOOGLE_CREDENTIALS_JSON` secret
9. Back in your Google Sheet, click **Share** (top right)
   - Paste in the `client_email` from your JSON file
   - Give it **Viewer** access

---

## Step 3: Get a Twelve Data API Key (Free)

1. Go to [https://twelvedata.com](https://twelvedata.com)
2. Click **Sign Up** — create a free account
3. Go to your dashboard and copy your **API Key**

Free tier gives you 800 credits/day. Each price fetch = 1 credit, RSI = 1 credit.
For 10 stocks running every 30 min during market hours: ~260 credits/day. You're fine. ✅

---

## Step 4: Create a Discord Webhook

1. In Discord, open the channel where you want alerts
2. Click the gear icon (⚙️) to edit the channel
3. Go to **Integrations → Webhooks → New Webhook**
4. Give it a name (e.g. "Portfolio Bot") and click **Copy Webhook URL**
5. Save that URL — it's your `DISCORD_WEBHOOK_URL`

---

## Step 5: Set Up GitHub

1. Go to [https://github.com](https://github.com) and create a free account if you don't have one
2. Create a **New Repository** — name it `portfolio-monitor`, set it to **Private**
3. Upload all the files from this project to your repo
   - The easiest way: click **Add file → Upload files** on GitHub and drag all files in
   - Make sure to also upload the `.github/workflows/monitor.yml` file
     (you may need to create the folder structure manually on GitHub)

---

## Step 6: Add Your Secrets to GitHub

This is how GitHub Actions gets your API keys securely (never stored in code).

1. In your GitHub repo, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret** for each of the following:

| Secret Name               | Value                                      |
|---------------------------|---------------------------------------------|
| `CLAUDE_API_KEY`          | Your Anthropic API key                     |
| `TWELVE_DATA_API_KEY`     | Your Twelve Data API key                   |
| `DISCORD_WEBHOOK_URL`     | Your Discord webhook URL                   |
| `GOOGLE_SHEET_ID`         | The Sheet ID from Step 1                   |
| `GOOGLE_CREDENTIALS_JSON` | The entire JSON content from Step 2        |

---

## Step 7: Test It Manually

Before waiting for the schedule to kick in:

1. Go to your GitHub repo
2. Click the **Actions** tab
3. Click **Portfolio Monitor** on the left
4. Click **Run workflow → Run workflow**
5. Watch it run — click into it to see the logs
6. Check your Discord channel for the report!

If something fails, the logs will tell you exactly what went wrong.

---

## Step 8: You're Done! 🎉

From now on, every weekday between 9:30am–4pm EST, the agent will automatically:
1. Read your Google Sheet
2. Fetch prices and RSI
3. Check your signals
4. Ask Claude to analyze it
5. Post a report to Discord

You don't need your PC on. You don't need to do anything.
Just check Discord for alerts.

---

## Customizing Your Settings

All your settings are in `config.py`:

- `RSI_OVERBOUGHT` — default 70 (raise it to reduce false alerts)
- `RSI_OVERSOLD` — default 30 (lower it to reduce false alerts)
- `LEVEL_PROXIMITY_PCT` — default 1.0% (how close to your level triggers an alert)

To change settings after deployment: edit `config.py` in GitHub and commit — it'll take effect on the next run.

---

## Troubleshooting

**"Could not fetch price for X"** — Check your Twelve Data API key is correct in GitHub Secrets

**"GOOGLE_CREDENTIALS_JSON not set"** — Make sure you pasted the full JSON content as the secret

**No Discord messages** — Check your webhook URL is correct. Test it by running the workflow manually.

**Sheet not reading** — Make sure your tab names are exactly `Portfolio`, `Watchlist`, `Levels` and you shared the sheet with the service account email.
