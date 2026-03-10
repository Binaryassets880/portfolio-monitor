# ============================================================
# claude_analyst.py — Sends data to Claude for smart analysis
# ============================================================

import anthropic
import config

def get_claude_analysis(portfolio, market_data, alerts):
    """
    Sends your portfolio snapshot and triggered alerts to Claude.
    Claude returns a plain-English summary with recommendations.
    """
    client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)

    position_summary = []
    for stock in portfolio:
        symbol = stock["symbol"]
        data   = market_data.get(symbol, {})
        if data.get("price"):
            entry   = stock["entry"]
            current = data["price"]
            pct     = ((current - entry) / entry * 100) if entry else 0
            rsi = data.get("rsi", "N/A")
            rsi_display = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
            position_summary.append(
                f"- {symbol}: Entry ${entry:.2f} | Current ${current:.2f} | "
                f"{'▲' if pct >= 0 else '▼'}{abs(pct):.1f}% | RSI: {rsi_display}"
            )

    alert_summary = [a["message"] for a in alerts] if alerts else ["No alerts triggered this cycle."]

    prompt = f"""You are a portfolio monitoring assistant. Review the following snapshot and alerts, 
then provide a brief, actionable summary for the trader.

CURRENT POSITIONS:
{chr(10).join(position_summary) if position_summary else "No positions loaded."}

TRIGGERED ALERTS THIS CYCLE:
{chr(10).join(alert_summary)}

Please provide:
1. A 2-3 sentence overall portfolio health summary
2. The top 1-2 actions the trader should consider RIGHT NOW (if any)
3. Anything to keep an eye on in the next session

Keep it concise and direct. No fluff. The trader is busy."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text
