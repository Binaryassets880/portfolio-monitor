# ============================================================
# discord_alerter.py — Sends alerts to your Discord channel
# ============================================================

import requests
import config
from datetime import datetime

def send_discord_message(content):
    """Send a plain message to Discord."""
    payload = {"content": content}
    response = requests.post(config.DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code not in (200, 204):
        print(f"  Discord error: {response.status_code} — {response.text}")

def send_alert_report(alerts, claude_summary, portfolio, market_data):
    """
    Formats and sends a full report to Discord.
    Uses Discord embeds for a clean look.
    """
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # ── Header ──────────────────────────────────────────────
    send_discord_message(f"📊 **Portfolio Monitor Report** — {now}")

    # ── Claude's Summary ────────────────────────────────────
    if claude_summary:
        send_discord_message(f"🤖 **Claude's Analysis:**\n{claude_summary}")

    # ── Alerts ──────────────────────────────────────────────
    if alerts:
        high   = [a for a in alerts if a["urgency"] == "HIGH"]
        medium = [a for a in alerts if a["urgency"] == "MEDIUM"]
        low    = [a for a in alerts if a["urgency"] == "LOW"]

        if high:
            lines = "\n".join(f"• {a['message']}" for a in high)
            send_discord_message(f"🔴 **HIGH PRIORITY ALERTS:**\n{lines}")
        
        if medium:
            lines = "\n".join(f"• {a['message']}" for a in medium)
            send_discord_message(f"🟡 **MEDIUM PRIORITY:**\n{lines}")
        
        if low:
            lines = "\n".join(f"• {a['message']}" for a in low)
            send_discord_message(f"🟢 **FYI / WATCHLIST:**\n{lines}")
    else:
        send_discord_message("✅ **No alerts triggered this cycle.** All positions within normal range.")

    # ── Position Snapshot ───────────────────────────────────
    snapshot_lines = []
    for stock in portfolio:
        symbol = stock["symbol"]
        data   = market_data.get(symbol, {})
        price  = data.get("price")
        rsi    = data.get("rsi")
        
        if price:
            entry  = stock["entry"]
            pct    = ((price - entry) / entry * 100) if entry else 0
            arrow  = "▲" if pct >= 0 else "▼"
            rsi_str = f" | RSI {rsi:.0f}" if rsi else ""
            snapshot_lines.append(f"`{symbol}` ${price:.2f} ({arrow}{abs(pct):.1f}%){rsi_str}")
    
    if snapshot_lines:
        send_discord_message("📋 **Position Snapshot:**\n" + "\n".join(snapshot_lines))

    send_discord_message("─" * 40)
