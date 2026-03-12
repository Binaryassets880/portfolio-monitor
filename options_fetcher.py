# ============================================================
# options_fetcher.py — Pulls options chain data from Tastytrade
# ============================================================
# Uses Tastytrade's OAuth2 API via the official tastytrade SDK.
# Auth requires: CLIENT_SECRET + REFRESH_TOKEN (stored as GitHub Secrets)

import os
import asyncio
import numpy as np
from scipy.stats import norm
from datetime import date
from tastytrade import Session
from tastytrade.instruments import get_option_chain

import config

# ── Authentication ───────────────────────────────────────────

def get_session():
    """
    Create a Tastytrade OAuth session using your credentials.
    The SDK auto-refreshes the access token every 15 minutes behind the scenes.
    You only need client_secret + refresh_token — no username/password.
    """
    client_secret = os.getenv("TASTYTRADE_CLIENT_SECRET")
    refresh_token = os.getenv("TASTYTRADE_REFRESH_TOKEN")

    if not client_secret or not refresh_token:
        raise Exception(
            "TASTYTRADE_CLIENT_SECRET or TASTYTRADE_REFRESH_TOKEN "
            "environment variables not set."
        )

    session = Session(client_secret, refresh_token)
    print("  ✓ Tastytrade OAuth session established")
    return session


# ── Black-Scholes Delta Calculation ─────────────────────────

def calculate_iv_from_price(option_price, stock_price, strike, tte_years,
                             risk_free_rate, option_type):
    """Back-calculate implied volatility from market price using bisection."""
    if option_price <= 0 or tte_years <= 0:
        return None
    low, high = 0.01, 5.0
    for _ in range(100):
        mid = (low + high) / 2.0
        bs_price = black_scholes_price(stock_price, strike, tte_years,
                                       risk_free_rate, mid, option_type)
        if bs_price is None:
            return None
        if abs(bs_price - option_price) < 0.001:
            return mid
        if bs_price < option_price:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def black_scholes_price(S, K, T, r, sigma, option_type):
    """Calculate theoretical option price using Black-Scholes."""
    if T <= 0 or sigma <= 0:
        return None
    try:
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if option_type == "P":
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        return max(price, 0)
    except Exception:
        return None


def calculate_delta(S, K, T, r, sigma, option_type):
    """Calculate delta. Returns absolute value (0.0 to 1.0)."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return None
    try:
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        if option_type == "C":
            return round(norm.cdf(d1), 4)
        else:
            return round(abs(norm.cdf(d1) - 1), 4)
    except Exception:
        return None


# ── Main Function: Find Best Option for Wheel ────────────────

async def _find_best_async(session, symbol, current_price, option_type,
                            cost_basis, target_delta_min, target_delta_max,
                            min_dte, max_dte, risk_free_rate):
    """Async inner function — fetches chain and scores candidates."""
    today = date.today()
    candidates = []

    # get_option_chain returns a dict: { expiration_date: [contracts] }
    chain = await get_option_chain(session, symbol)

    # Filter to expirations in our DTE window
    target_exps = {
        exp: contracts for exp, contracts in chain.items()
        if min_dte <= (exp - today).days <= max_dte
    }

    if not target_exps:
        print(f"    No expirations in {min_dte}–{max_dte} DTE window for {symbol}")
        return []

    print(f"    Scanning {len(target_exps)} expiration(s) for {symbol} ({option_type})...")

    for exp_date, contracts in target_exps.items():
        dte = (exp_date - today).days
        tte_years = dte / 365.0

        for contract in contracts:
            try:
                # Skip the wrong option type (P=put, C=call)
                if contract.option_type.value != option_type:
                    continue

                strike = float(contract.strike_price)
                bid    = float(contract.bid or 0)
                ask    = float(contract.ask or 0)

                if strike <= 0 or bid <= 0:
                    continue

                # For CC: skip strikes at or below cost basis
                if option_type == "C" and cost_basis and strike <= cost_basis:
                    continue

                mid_price = (bid + ask) / 2.0

                # Calculate IV from mid price, then delta from IV
                iv = calculate_iv_from_price(mid_price, current_price, strike,
                                             tte_years, risk_free_rate, option_type)
                if not iv:
                    continue

                delta = calculate_delta(current_price, strike, tte_years,
                                        risk_free_rate, iv, option_type)
                if delta is None:
                    continue

                # Only keep options in target delta range
                if not (target_delta_min <= delta <= target_delta_max):
                    continue

                # Annualized return: (premium / strike) * (365 / DTE)
                basis = cost_basis if (option_type == "C" and cost_basis) else strike
                ann_return = (mid_price / basis) * (365.0 / dte) * 100

                candidates.append({
                    "symbol":            symbol,
                    "option_type":       "PUT" if option_type == "P" else "CALL",
                    "strike":            strike,
                    "expiration":        exp_date.strftime("%b %d, %Y"),
                    "dte":               dte,
                    "bid":               round(bid, 2),
                    "ask":               round(ask, 2),
                    "mid":               round(mid_price, 2),
                    "delta":             delta,
                    "iv":                round(iv * 100, 1),
                    "annualized_return": round(ann_return, 1),
                })

            except (ValueError, TypeError, ZeroDivisionError, AttributeError):
                continue

    # Sort best annualized return first, return top 5
    candidates.sort(key=lambda x: -x["annualized_return"])
    return candidates[:5]


def find_best_wheel_option(session, symbol, current_price,
                            option_type,
                            cost_basis=None,
                            target_delta_min=0.20,
                            target_delta_max=0.25,
                            min_dte=21,
                            max_dte=60,
                            risk_free_rate=0.045):
    """
    Synchronous wrapper — wheel_evaluator.py calls this directly.
    Uses a new event loop each time to avoid "Event loop is closed" errors
    on Windows when called multiple times in sequence.
    """
    # Create a fresh event loop for each call to avoid Windows asyncio issues
    # where asyncio.run() closes the loop and subsequent calls fail
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _find_best_async(
                session, symbol, current_price, option_type,
                cost_basis, target_delta_min, target_delta_max,
                min_dte, max_dte, risk_free_rate
            )
        )
    finally:
        loop.close()
