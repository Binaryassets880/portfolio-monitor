# ============================================================
# main.py — The Orchestrator
# ============================================================

import sheets_reader
import price_fetcher
import signal_evaluator
import claude_analyst
import discord_alerter
import options_fetcher
import wheel_evaluator

def run():
    print("=" * 50)
    print("📈 Portfolio Monitor Agent Starting...")
    print("=" * 50)

    # ── Step 1: Read Google Sheets ───────────────────────────
    print("\n[1/6] Reading Google Sheets...")
    try:
        portfolio = sheets_reader.read_portfolio()
        watchlist = sheets_reader.read_watchlist()
        levels    = sheets_reader.read_levels()
        wheel     = sheets_reader.read_wheel()
        print(f"  ✓ {len(portfolio)} portfolio | {len(watchlist)} watchlist | "
              f"{len(levels)} levels | {len(wheel)} wheel positions")
    except Exception as e:
        print(f"  ✗ Failed to read Google Sheets: {e}")
        return

    # ── Step 2: Fetch Market Data ────────────────────────────
    all_symbols = list(set(
        [s["symbol"] for s in portfolio] +
        [s["symbol"] for s in watchlist] +
        [l["symbol"] for l in levels]    +
        [w["symbol"] for w in wheel]
    ))
    print(f"\n[2/6] Fetching market data for: {', '.join(all_symbols)}")
    try:
        market_data = price_fetcher.get_all_data(all_symbols)
        print("  ✓ Market data fetched")
    except Exception as e:
        print(f"  ✗ Failed to fetch market data: {e}")
        return

    # ── Step 3: Evaluate Stock Signals ──────────────────────
    print("\n[3/6] Evaluating stock signals...")
    alerts = signal_evaluator.check_signals(portfolio, watchlist, levels, market_data)
    print(f"  ✓ {len(alerts)} stock alert(s) triggered")
    for a in alerts:
        print(f"    [{a['urgency']}] {a['message']}")

    # ── Step 4: Evaluate Wheel Positions ────────────────────
    wheel_recommendations = []
    if wheel:
        print("\n[4/6] Evaluating wheel positions via Tastytrade...")
        try:
            session = options_fetcher.get_session()
            wheel_recommendations = wheel_evaluator.evaluate_wheel_positions(
                wheel, market_data, session
            )
            print(f"  ✓ {len(wheel_recommendations)} wheel recommendation(s)")
            for r in wheel_recommendations:
                print(f"    [{r['phase']}] {r['symbol']}: {r['type']}")
        except Exception as e:
            print(f"  ✗ Wheel evaluation failed: {e}")
    else:
        print("\n[4/6] No wheel positions found — skipping options analysis.")

    # ── Step 5: Claude Analysis ──────────────────────────────
    print("\n[5/6] Getting Claude's analysis...")
    try:
        claude_summary = claude_analyst.get_claude_analysis(
            portfolio, market_data, alerts, wheel_recommendations
        )
        print("  ✓ Analysis received")
    except Exception as e:
        print(f"  ✗ Claude analysis failed: {e}")
        claude_summary = "Claude analysis unavailable this cycle."

    # ── Step 6: Send Discord Report ─────────────────────────
    print("\n[6/6] Sending Discord report...")
    try:
        discord_alerter.send_alert_report(
            alerts, claude_summary, portfolio, market_data, wheel_recommendations
        )
        print("  ✓ Report sent to Discord!")
    except Exception as e:
        print(f"  ✗ Discord send failed: {e}")

    print("\n✅ Done!\n")

if __name__ == "__main__":
    run()
