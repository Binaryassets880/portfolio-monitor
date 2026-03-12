# ============================================================
# claude_analyst.py — Sends data to Claude for smart analysis
# ============================================================

import anthropic
import config

def get_claude_analysis(portfolio, market_data, alerts, wheel_recommendations=None):
    """
    Sends portfolio snapshot, alerts, and wheel recommendations to Claude.
    Returns a plain-English summary with actionable advice.
    """
    client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)

    # ── Build stock position summary ─────────────────────────
    position_summary = []
    for stock in portfolio:
        symbol  = stock["symbol"]
        entry   = stock.get("entry", 0)
        shares  = stock.get("shares", 0)
        data    = market_data.get(symbol, {})
        price   = data.get("price")
        rsi     = data.get("rsi")

        # Debug: print what we found so we can see any missing data in logs
        print(f"  [claude_analyst] {symbol}: price={price}, rsi={rsi}, entry={entry}")

        if price is not None:
            pct         = ((price - entry) / entry * 100) if entry else 0
            rsi_display = f"{rsi:.1f}" if isinstance(rsi, float) else "N/A"
            position_summary.append(
                f"- {symbol}: Entry ${entry:.2f} | Current ${price:.2f} | "
                f"{'▲' if pct >= 0 else '▼'}{abs(pct):.1f}% | RSI {rsi_display} | "
                f"{int(shares)} shares"
            )
        else:
            # Price was None — still include the position so Claude knows it exists
            position_summary.append(
                f"- {symbol}: Entry ${entry:.2f} | Price unavailable | {int(shares)} shares"
            )

    # ── Build alert summary ──────────────────────────────────
    alert_summary = [a["message"] for a in alerts] if alerts else ["No alerts triggered."]

    # ── Build wheel position summary ─────────────────────────
    # This covers BOTH the narrative for Claude AND the "no candidates" explanations
    wheel_text = ""
    if wheel_recommendations:
        wheel_lines = []
        for rec in wheel_recommendations:
            symbol = rec["symbol"]
            phase  = rec["phase"]
            msg    = rec["message"]

            # Pull a few key fields if they exist on the rec object for extra context
            cost_basis = rec.get("cost_basis", 0)
            data       = market_data.get(symbol, {})
            price      = data.get("price")

            line = f"- [{phase}] {symbol}"
            if cost_basis and price:
                pct_from_cb = ((price - cost_basis) / cost_basis * 100)
                line += (
                    f": Cost basis ${cost_basis:.2f} | Current ${price:.2f} | "
                    f"{'▲' if pct_from_cb >= 0 else '▼'}{abs(pct_from_cb):.1f}% from basis"
                )
            line += f"\n  → {msg}"

            # If there are candidate options, show the top 1 for brevity
            if rec.get("candidates"):
                c = rec["candidates"][0]
                line += (
                    f"\n  Best candidate: ${c['strike']} {c['option_type']} "
                    f"exp {c['expiration']} ({c['dte']} DTE) "
                    f"mid ${c['mid']} | Δ{c['delta']} | {c['annualized_return']}% ann."
                )

            wheel_lines.append(line)

        wheel_text = "\nWHEEL POSITIONS:\n" + "\n".join(wheel_lines)

    # ── Log what we're sending so we can debug "empty portfolio" issues ──
    print(f"  [claude_analyst] Sending {len(position_summary)} stock position(s) to Claude.")
    print(f"  [claude_analyst] Sending {len(wheel_recommendations or [])} wheel rec(s) to Claude.")

    # ── Build prompt ─────────────────────────────────────────
    prompt = f"""You are a concise portfolio monitor for a wheel options trader.
Respond in plain text only. No headers, no markdown, no bullet symbols.
Keep your ENTIRE response under 800 characters.

STOCK POSITIONS:
{chr(10).join(position_summary) if position_summary else "None loaded."}

ALERTS: {"; ".join(alert_summary)}
{wheel_text}

Give me:
1. One sentence on overall health.
2. One sentence on biggest risk or action right now.
3. One sentence on what to watch next session.

Be direct. No fluff. Under 800 characters total."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text
