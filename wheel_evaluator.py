# ============================================================
# wheel_evaluator.py
# ============================================================

import asyncio
import options_fetcher
import config
from datetime import datetime, date

def evaluate_wheel_positions(wheel_positions, market_data, session):
    """Synchronous entry point — runs all evaluations in one event loop."""
    return asyncio.run(_evaluate_all(wheel_positions, market_data, session))

async def _evaluate_all(wheel_positions, market_data, session):
    """Async — processes all wheel positions in a single event loop."""
    recommendations = []
    for position in wheel_positions:
        symbol = position["symbol"]
        phase  = position["phase"]
        data   = market_data.get(symbol, {})
        price  = data.get("price")

        if not price:
            print(f"    No price data for {symbol}, skipping")
            continue

        print(f"  Evaluating {symbol} [{phase}] @ ${price:.2f}")

        if phase == "Watching":
            rec = await _evaluate_watching(position, price, session)
        elif phase == "CSP Open":
            rec = _evaluate_csp_open(position, price)
        elif phase == "Assigned":
            rec = await _evaluate_assigned(position, price, session)
        elif phase == "CC Open":
            rec = _evaluate_cc_open(position, price)
        else:
            rec = None

        if rec:
            recommendations.append(rec)

    return recommendations


async def _evaluate_watching(position, current_price, session):
    symbol = position["symbol"]
    candidates = await options_fetcher.find_best_wheel_option_async(
        session=session, symbol=symbol, current_price=current_price,
        option_type="P",
        target_delta_min=config.WHEEL_DELTA_MIN,
        target_delta_max=config.WHEEL_DELTA_MAX,
        min_dte=config.WHEEL_MIN_DTE, max_dte=config.WHEEL_MAX_DTE,
    )
    if not candidates:
        return {
            "symbol": symbol, "phase": "Watching", "type": "NO_CANDIDATES",
            "message": f"⚪ {symbol} [WATCHING] — No CSP candidates found in {config.WHEEL_MIN_DTE}–{config.WHEEL_MAX_DTE} DTE at {config.WHEEL_DELTA_MIN}–{config.WHEEL_DELTA_MAX} delta.",
            "urgency": "LOW", "candidates": [],
        }
    best = candidates[0]
    return {
        "symbol": symbol, "phase": "Watching", "type": "CSP_OPPORTUNITY",
        "message": (
            f"🟢 {symbol} [WATCHING] — Best CSP: ${best['strike']} Put exp {best['expiration']} "
            f"({best['dte']} DTE) | Mid ${best['mid']} | Delta {best['delta']} | "
            f"IV {best['iv']}% | Ann. Return {best['annualized_return']}%"
        ),
        "urgency": "MEDIUM", "candidates": candidates,
    }


def _evaluate_csp_open(position, current_price):
    symbol = position["symbol"]
    strike = position.get("strike", 0)
    expiration = position.get("expiration", "")
    alerts = []

    if strike > 0:
        pct_to_strike = ((current_price - strike) / current_price) * 100
        if current_price < strike:
            alerts.append(
                f"⚠️ {symbol} CSP at ${strike} is IN THE MONEY! "
                f"Current: ${current_price:.2f}. Consider rolling or preparing for assignment."
            )
        elif pct_to_strike < 3:
            alerts.append(
                f"🟡 {symbol} CSP at ${strike} is {pct_to_strike:.1f}% OTM — getting close."
            )

    if expiration:
        try:
            exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            dte = (exp_date - date.today()).days
            if dte <= 7 and current_price > strike:
                alerts.append(f"✅ {symbol} CSP expires in {dte} day(s) — consider closing early.")
            elif dte <= 3:
                alerts.append(f"⏰ {symbol} CSP expires in {dte} day(s)!")
        except ValueError:
            pass

    if not alerts:
        return None
    return {
        "symbol": symbol, "phase": "CSP Open", "type": "CSP_MONITOR",
        "message": "\n".join(alerts),
        "urgency": "HIGH" if any("IN THE MONEY" in a for a in alerts) else "MEDIUM",
        "candidates": [],
    }


async def _evaluate_assigned(position, current_price, session):
    symbol     = position["symbol"]
    cost_basis = position.get("cost_basis", 0) or current_price

    profit_if_called = ((cost_basis - current_price) / cost_basis) * 100 if cost_basis > 0 else 0
    assignment_msg = (
        f"📋 {symbol} [ASSIGNED] — Cost basis: ${cost_basis:.2f} | "
        f"Current: ${current_price:.2f} | "
        f"{'Profit' if current_price >= cost_basis else 'Loss'} if called: {abs(profit_if_called):.1f}%\n"
    )

    candidates = await options_fetcher.find_best_wheel_option_async(
        session=session, symbol=symbol, current_price=current_price,
        option_type="C", cost_basis=cost_basis,
        target_delta_min=config.WHEEL_DELTA_MIN,
        target_delta_max=config.WHEEL_DELTA_MAX,
        min_dte=config.WHEEL_MIN_DTE, max_dte=config.WHEEL_MAX_DTE,
    )

    if not candidates:
        message = assignment_msg + f"  No CC candidates found above cost basis (${cost_basis:.2f})"
    else:
        best = candidates[0]
        message = assignment_msg + (
            f"  Best CC: ${best['strike']} Call exp {best['expiration']} "
            f"({best['dte']} DTE) | Mid ${best['mid']} | Delta {best['delta']} | "
            f"Ann. Return {best['annualized_return']}%"
        )

    return {
        "symbol": symbol, "phase": "Assigned", "type": "CC_OPPORTUNITY",
        "message": message, "urgency": "MEDIUM", "candidates": candidates,
    }


def _evaluate_cc_open(position, current_price):
    symbol     = position["symbol"]
    strike     = position.get("strike", 0)
    cost_basis = position.get("cost_basis", 0)
    expiration = position.get("expiration", "")
    alerts = []

    if strike > 0:
        if current_price > strike:
            alerts.append(
                f"⚠️ {symbol} CC at ${strike} is IN THE MONEY! Current: ${current_price:.2f}. "
                + (f"Cost basis ${cost_basis:.2f} — {'profit ✅' if strike >= cost_basis else 'loss ❌'}" if cost_basis > 0 else "")
            )
        elif current_price > strike * 0.97:
            alerts.append(f"🟡 {symbol} CC at ${strike} — price within 3% of strike. Watch closely.")

    if expiration:
        try:
            exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            dte = (exp_date - date.today()).days
            if dte <= 7 and current_price < strike:
                alerts.append(f"✅ {symbol} CC expires in {dte} day(s) — consider closing early.")
            elif dte <= 3:
                alerts.append(f"⏰ {symbol} CC expires in {dte} day(s)!")
        except ValueError:
            pass

    if not alerts:
        return None
    return {
        "symbol": symbol, "phase": "CC Open", "type": "CC_MONITOR",
        "message": "\n".join(alerts),
        "urgency": "HIGH" if any("IN THE MONEY" in a for a in alerts) else "MEDIUM",
        "candidates": [],
    }
