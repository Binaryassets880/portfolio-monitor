# ============================================================
# discord_alerter.py — Sends alerts to your Discord channel
# ============================================================

import requests
import config
from datetime import datetime

def send_discord_message(content):
    payload  = {"content": content}
    response = requests.post(config.DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code not in (200, 204):
        print(f"  Discord error: {response.status_code} — {response.text}")

def send_alert_report(alerts, claude_summary, portfolio, market_data,
                      wheel_recommendations=None):
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # ── Header ──────────────────────────────────────────────
    send_discord_message(f"📊 **Portfolio Monitor Report** — {now}")

    # ── Claude's Summary ────────────────────────────────────
    if claude_summary:
        send_discord_message(f"🤖 **Claude's Analysis:**\n{claude_summary}")

    # ── Stock Alerts ─────────────────────────────────────────
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
        send_discord_message("✅ **No stock alerts triggered this cycle.**")

    # ── Wheel Strategy Recommendations ───────────────────────
    if wheel_recommendations:
        # Separate urgent monitors from new opportunities
        monitors = [r for r in wheel_recommendations
                    if r["type"] in ("CSP_MONITOR", "CC_MONITOR")]
        opps     = [r for r in wheel_recommendations
                    if r["type"] in ("CSP_OPPORTUNITY", "CC_OPPORTUNITY")]

        if monitors:
            lines = "\n".join(f"• {r['message']}" for r in monitors)
            send_discord_message(f"⚠️ **WHEEL POSITION ALERTS:**\n{lines}")

        if opps:
            for rec in opps:
                header = f"🎯 **WHEEL OPPORTUNITY — {rec['symbol']} [{rec['phase']}]**"
                body   = rec["message"]

                # Show top 3 candidates in a clean table
                if rec.get("candidates"):
                    body += "\n\n**Top Candidates:**"
                    for i, c in enumerate(rec["candidates"][:3], 1):
                        body += (
                            f"\n{i}. `${c['strike']} {c['option_type']}` exp {c['expiration']} "
                            f"({c['dte']} DTE) | Mid **${c['mid']}** | "
                            f"Δ {c['delta']} | IV {c['iv']}% | "
                            f"Ann. {c['annualized_return']}%"
                        )
                send_discord_message(f"{header}\n{body}")

    # ── Position Snapshot ────────────────────────────────────
    snapshot_lines = []
    for stock in portfolio:
        symbol = stock["symbol"]
        data   = market_data.get(symbol, {})
        price  = data.get("price")
        rsi    = data.get("rsi")
        if price:
            entry   = stock["entry"]
            pct     = ((price - entry) / entry * 100) if entry else 0
            arrow   = "▲" if pct >= 0 else "▼"
            rsi_str = f" | RSI {rsi:.0f}" if rsi else ""
            snapshot_lines.append(f"`{symbol}` ${price:.2f} ({arrow}{abs(pct):.1f}%){rsi_str}")

    if snapshot_lines:
        send_discord_message("📋 **Position Snapshot:**\n" + "\n".join(snapshot_lines))

    send_discord_message("─" * 40)
