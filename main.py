# ============================================================
# main.py — The Orchestrator: runs all agents in sequence
# ============================================================
# This is the file that GitHub Actions will execute every 30 min.
# Run this locally to test: python main.py

import sheets_reader
import price_fetcher
import signal_evaluator
import claude_analyst
import discord_alerter

def run():
    print("=" * 50)
    print("📈 Portfolio Monitor Agent Starting...")
    print("=" * 50)

    # ── Step 1: Read your Google Sheets data ────────────────
    print("\n[1/5] Reading Google Sheets...")
    try:
        portfolio = sheets_reader.read_portfolio()
        watchlist = sheets_reader.read_watchlist()
        levels    = sheets_reader.read_levels()
        print(f"  ✓ {len(portfolio)} portfolio positions, {len(watchlist)} watchlist items, {len(levels)} price levels")
    except Exception as e:
        print(f"  ✗ Failed to read Google Sheets: {e}")
        return

    # ── Step 2: Get all unique symbols we need data for ─────
    all_symbols = list(set(
        [s["symbol"] for s in portfolio] +
        [s["symbol"] for s in watchlist] +
        [l["symbol"] for l in levels]
    ))
    print(f"\n[2/5] Fetching market data for: {', '.join(all_symbols)}")
    
    try:
        market_data = price_fetcher.get_all_data(all_symbols)
        print(f"  ✓ Market data fetched")
    except Exception as e:
        print(f"  ✗ Failed to fetch market data: {e}")
        return

    # ── Step 3: Run signal checks ───────────────────────────
    print("\n[3/5] Evaluating signals...")
    alerts = signal_evaluator.check_signals(portfolio, watchlist, levels, market_data)
    print(f"  ✓ {len(alerts)} alert(s) triggered")
    for a in alerts:
        print(f"    [{a['urgency']}] {a['message']}")

    # ── Step 4: Get Claude's analysis ───────────────────────
    print("\n[4/5] Getting Claude's analysis...")
    try:
        claude_summary = claude_analyst.get_claude_analysis(portfolio, market_data, alerts)
        print(f"  ✓ Analysis received")
    except Exception as e:
        print(f"  ✗ Claude analysis failed: {e}")
        claude_summary = "Claude analysis unavailable this cycle."

    # ── Step 5: Send to Discord ─────────────────────────────
    print("\n[5/5] Sending Discord report...")
    try:
        discord_alerter.send_alert_report(alerts, claude_summary, portfolio, market_data)
        print("  ✓ Report sent to Discord!")
    except Exception as e:
        print(f"  ✗ Discord send failed: {e}")

    print("\n✅ Done!\n")

if __name__ == "__main__":
    run()
