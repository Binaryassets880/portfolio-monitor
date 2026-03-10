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

    # ── Build position summary ───────────────────────────────
    position_summary = []
    for stock in portfolio:
        symbol = stock["symbol"]
        data   = market_data.get(symbol, {})
        if data.get("price"):
            entry   = stock["entry"]
            current = data["price"]
            pct     = ((current - entry) / entry * 100) if entry else 0
            rsi     = data.get("rsi", "N/A")
            rsi_display = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
            position_summary.append(
                f"- {symbol}: Entry ${entry:.2f} | Current ${current:.2f} | "
                f"{'▲' if pct >= 0 else '▼'}{abs(pct):.1f}% | RSI: {rsi_display}"
            )

    # ── Build alert summary ──────────────────────────────────
    alert_summary = [a["message"] for a in alerts] if alerts else ["No alerts triggered."]

    # ── Build wheel summary ──────────────────────────────────
    wheel_text = ""
    if wheel_recommendations:
        wheel_lines = []
        for rec in wheel_recommendations:
            wheel_lines.append(f"- [{rec['phase']}] {rec['symbol']}: {rec['message']}")
        wheel_text = f"""
WHEEL STRATEGY POSITIONS:
{chr(10).join(wheel_lines)}
"""

    # ── Build prompt ─────────────────────────────────────────
    prompt = f"""You are a portfolio monitoring assistant specializing in the wheel options strategy.
Review the snapshot below and give brief, actionable advice.

CURRENT STOCK POSITIONS:
{chr(10).join(position_summary) if position_summary else "No positions loaded."}

TRIGGERED ALERTS:
{chr(10).join(alert_summary)}
{wheel_text}
Please provide:
1. A 2-3 sentence overall portfolio health summary
2. Top 1-2 actions to consider RIGHT NOW (be specific — include strike/expiration if relevant)
3. Anything to watch in the next session

Rules:
- Be concise and direct, no fluff
- For wheel positions, factor in delta targets (0.20-0.25), premium quality, and proximity to support/resistance
- Flag any ITM options as urgent
- The trader uses the wheel strategy: sells CSPs on stocks they want to own, sells CCs after assignment"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text
