# ============================================================
# wheel_evaluator.py — Evaluates wheel positions and generates
#                      CSP/CC recommendations
# ============================================================

import options_fetcher
import config
from datetime import datetime, date

def evaluate_wheel_positions(wheel_positions, market_data, session):
    """
    Processes each row in your Wheel tab and returns recommendations.

    Phase logic:
      - "Watching"  → Find best CSP to open
      - "CSP Open"  → Monitor existing put position
      - "Assigned"  → You were assigned shares, suggest next CC
      - "CC Open"   → Monitor existing covered call position

    Returns a list of recommendation dicts.
    """
    recommendations = []

    for position in wheel_positions:
        symbol    = position["symbol"]
        phase     = position["phase"]
        data      = market_data.get(symbol, {})
        price     = data.get("price")

        if not price:
            print(f"    No price data for {symbol}, skipping wheel evaluation")
            continue

        print(f"  Evaluating {symbol} [{phase}] @ ${price:.2f}")

        # ── WATCHING: Find best CSP to sell ─────────────────
        if phase == "Watching":
            rec = _evaluate_watching(position, price, session)
            if rec:
                recommendations.append(rec)

        # ── CSP OPEN: Monitor existing put ──────────────────
        elif phase == "CSP Open":
            rec = _evaluate_csp_open(position, price)
            if rec:
                recommendations.append(rec)

        # ── ASSIGNED: Was assigned shares, find best CC ──────
        elif phase == "Assigned":
            rec = _evaluate_assigned(position, price, session)
            if rec:
                recommendations.append(rec)

        # ── CC OPEN: Monitor existing covered call ───────────
        elif phase == "CC Open":
            rec = _evaluate_cc_open(position, price)
            if rec:
                recommendations.append(rec)

    return recommendations


# ── Phase Evaluators ─────────────────────────────────────────

def _evaluate_watching(position, current_price, session):
    """Looking for a good CSP entry point."""
    symbol = position["symbol"]

    candidates = options_fetcher.find_best_wheel_option(
        session  = session,
        symbol         = symbol,
        current_price  = current_price,
        option_type    = "P",
        target_delta_min = config.WHEEL_DELTA_MIN,
        target_delta_max = config.WHEEL_DELTA_MAX,
        min_dte          = config.WHEEL_MIN_DTE,
        max_dte          = config.WHEEL_MAX_DTE,
    )

    if not candidates:
        return {
            "symbol":  symbol,
            "phase":   "Watching",
            "type":    "NO_CANDIDATES",
            "message": f"⚪ {symbol} [WATCHING] — No CSP candidates found in {config.WHEEL_MIN_DTE}–{config.WHEEL_MAX_DTE} DTE range at {config.WHEEL_DELTA_MIN}–{config.WHEEL_DELTA_MAX} delta.",
            "urgency": "LOW",
            "candidates": [],
        }

    best = candidates[0]
    return {
        "symbol":  symbol,
        "phase":   "Watching",
        "type":    "CSP_OPPORTUNITY",
        "message": (
            f"🟢 {symbol} [WATCHING] — Best CSP: "
            f"${best['strike']} Put exp {best['expiration']} "
            f"({best['dte']} DTE) | Mid ${best['mid']} | "
            f"Delta {best['delta']} | IV {best['iv']}% | "
            f"Ann. Return {best['annualized_return']}%"
        ),
        "urgency":    "MEDIUM",
        "candidates": candidates,
    }


def _evaluate_csp_open(position, current_price):
    """Monitoring an open CSP position."""
    symbol        = position["symbol"]
    strike        = position.get("strike", 0)
    expiration    = position.get("expiration", "")
    premium_paid  = position.get("premium_collected", 0)  # Premium you collected
    notes         = position.get("notes", "")

    alerts = []

    # Check if price is approaching the strike (going ITM)
    if strike > 0:
        pct_to_strike = ((current_price - strike) / current_price) * 100
        if current_price < strike:
            alerts.append(
                f"⚠️ {symbol} CSP at ${strike} is IN THE MONEY! "
                f"Current: ${current_price:.2f} (${abs(current_price - strike):.2f} ITM). "
                f"Consider rolling down/out or preparing for assignment."
            )
        elif pct_to_strike < 3:
            alerts.append(
                f"🟡 {symbol} CSP at ${strike} is getting close — "
                f"only {pct_to_strike:.1f}% OTM. Current: ${current_price:.2f}"
            )

    # Check expiration proximity
    if expiration:
        try:
            exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            dte = (exp_date - date.today()).days
            if dte <= 7 and current_price > strike:
                alerts.append(
                    f"✅ {symbol} CSP expires in {dte} day(s) — "
                    f"looking good! Consider closing early to lock in profit."
                )
            elif dte <= 3:
                alerts.append(
                    f"⏰ {symbol} CSP expires in {dte} day(s) — expiration approaching!"
                )
        except ValueError:
            pass

    if not alerts:
        return None  # No alerts needed, position is healthy

    return {
        "symbol":  symbol,
        "phase":   "CSP Open",
        "type":    "CSP_MONITOR",
        "message": "\n".join(alerts),
        "urgency": "HIGH" if any("IN THE MONEY" in a for a in alerts) else "MEDIUM",
        "candidates": [],
    }


def _evaluate_assigned(position, current_price, session):
    """Was assigned shares — find best covered call to sell."""
    symbol      = position["symbol"]
    cost_basis  = position.get("cost_basis", 0)

    if cost_basis <= 0:
        cost_basis = current_price  # Fallback if not set

    profit_if_called = ((cost_basis - current_price) / cost_basis) * 100 if cost_basis > 0 else 0

    assignment_msg = (
        f"📋 {symbol} [ASSIGNED] — You hold shares. "
        f"Cost basis: ${cost_basis:.2f} | Current: ${current_price:.2f} | "
        f"{'Profit' if current_price >= cost_basis else 'Loss'} if called away: "
        f"{abs(profit_if_called):.1f}%\n"
    )

    # Find best CC to sell
    candidates = options_fetcher.find_best_wheel_option(
        session    = session,
        symbol           = symbol,
        current_price    = current_price,
        option_type      = "C",
        cost_basis       = cost_basis,
        target_delta_min = config.WHEEL_DELTA_MIN,
        target_delta_max = config.WHEEL_DELTA_MAX,
        min_dte          = config.WHEEL_MIN_DTE,
        max_dte          = config.WHEEL_MAX_DTE,
    )

    if not candidates:
        message = assignment_msg + f"  No CC candidates found above cost basis (${cost_basis:.2f})"
    else:
        best = candidates[0]
        message = assignment_msg + (
            f"  Best CC: ${best['strike']} Call exp {best['expiration']} "
            f"({best['dte']} DTE) | Mid ${best['mid']} | "
            f"Delta {best['delta']} | Ann. Return {best['annualized_return']}%"
        )

    return {
        "symbol":     symbol,
        "phase":      "Assigned",
        "type":       "CC_OPPORTUNITY",
        "message":    message,
        "urgency":    "MEDIUM",
        "candidates": candidates,
        "cost_basis": cost_basis,   # passed through so claude_analyst can use it
    }


def _evaluate_cc_open(position, current_price):
    """Monitoring an open covered call position."""
    symbol       = position["symbol"]
    strike       = position.get("strike", 0)
    cost_basis   = position.get("cost_basis", 0)
    expiration   = position.get("expiration", "")

    alerts = []

    if strike > 0:
        # Check if CC is going ITM (price rising above strike)
        if current_price > strike:
            alerts.append(
                f"⚠️ {symbol} CC at ${strike} is IN THE MONEY! "
                f"Current: ${current_price:.2f}. "
                f"You may get called away. "
                + (f"Cost basis was ${cost_basis:.2f} — {'profit ✅' if strike >= cost_basis else 'loss ❌'}" 
                   if cost_basis > 0 else "")
            )
        elif current_price > strike * 0.97:
            alerts.append(
                f"🟡 {symbol} CC at ${strike} — price ${current_price:.2f} is within 3% of strike. Watch closely."
            )

    # Expiration proximity
    if expiration:
        try:
            exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            dte = (exp_date - date.today()).days
            if dte <= 7 and current_price < strike:
                alerts.append(
                    f"✅ {symbol} CC expires in {dte} day(s) — "
                    f"looking good! Consider closing early for a quick profit."
                )
            elif dte <= 3:
                alerts.append(f"⏰ {symbol} CC expires in {dte} day(s).")
        except ValueError:
            pass

    if not alerts:
        return None

    return {
        "symbol":    symbol,
        "phase":     "CC Open",
        "type":      "CC_MONITOR",
        "message":   "\n".join(alerts),
        "urgency":   "HIGH" if any("IN THE MONEY" in a for a in alerts) else "MEDIUM",
        "candidates": [],
        "cost_basis": cost_basis,   # passed through so claude_analyst can use it
    }
