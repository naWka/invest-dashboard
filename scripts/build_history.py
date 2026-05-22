#!/usr/bin/env python3
"""
Генератор data/history.json — таймсерия стоимости портфеля + cost basis + бенчмарк.

Бенчмарк = 100% SWRD с теми же датами и суммами покупок, что у реального портфеля.
Если зелёная линия портфеля на графике выше синей линии бенчмарка — выбранная
аллокация 70/15/15 обгоняет «чистый» MSCI World, и наоборот.

Использование:
    python scripts/build_history.py
"""
import json
import os
import ssl
import time
import urllib.request
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
PORTFOLIO_PATH = os.path.join(ROOT, "data", "portfolio.json")
HISTORY_PATH = os.path.join(ROOT, "data", "history.json")

TICKERS = {"SWRD": "SWRD.L", "EIMI": "EIMI.L", "USSC": "USSC.L"}
ETFS = ["SWRD", "EIMI", "USSC"]


def fetch_yahoo_history(symbol: str, period1: int, period2: int) -> list[tuple[str, float]]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?period1={period1}&period2={period2}&interval=1d"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        d = json.load(r)
    res = d["chart"]["result"][0]
    out = []
    for ts, close in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if close is None:
            continue
        out.append((time.strftime("%Y-%m-%d", time.gmtime(ts)), round(close, 4)))
    return out


def build():
    with open(PORTFOLIO_PATH) as f:
        p = json.load(f)

    txs = sorted(p["transactions"], key=lambda t: (t["date"], t.get("time", "")))
    if not txs:
        print("No transactions, nothing to build.")
        return
    first_date = txs[0]["date"]

    # Yahoo range: от за 2 дня до первой транзакции до завтра
    start_ts = int(time.mktime(time.strptime(first_date, "%Y-%m-%d"))) - 2 * 86400
    end_ts = int(time.time()) + 86400

    prices_by_date: dict[str, dict[str, float]] = {}
    for etf, sym in TICKERS.items():
        series = fetch_yahoo_history(sym, start_ts, end_ts)
        prices_by_date[etf] = {d: c for d, c in series}
        print(f"  {etf}: {len(series)} pts, {series[0][0]} → {series[-1][0]}")

    all_days = sorted(set().union(*[set(d.keys()) for d in prices_by_date.values()]))

    tx_by_date: dict[str, list] = defaultdict(list)
    for t in txs:
        tx_by_date[t["date"]].append(t)

    shares = {e: 0 for e in ETFS}
    invested = 0.0
    bench_shares = 0.0
    last_known = {e: None for e in ETFS}

    series = []
    for day in all_days:
        for e in ETFS:
            if day in prices_by_date[e]:
                last_known[e] = prices_by_date[e][day]
        for t in tx_by_date.get(day, []):
            shares[t["etf"]] += t["shares"]
            invested += t["total"]
            swrd_px = prices_by_date["SWRD"].get(day) or last_known["SWRD"]
            if swrd_px:
                bench_shares += t["total"] / swrd_px

        pv = sum(shares[e] * last_known[e] for e in ETFS if last_known[e])
        swrd_px = last_known["SWRD"]
        bv = bench_shares * swrd_px if swrd_px else 0.0

        series.append({
            "date": day,
            "portfolio": round(pv, 2),
            "invested": round(invested, 2),
            "benchmark": round(bv, 2),
            "pnl": round(pv - invested, 2),
            "pnl_pct": round((pv / invested - 1) * 100, 2) if invested else 0.0,
        })

    out = {
        "updated": series[-1]["date"],
        "tickers": TICKERS,
        "benchmark_note": "100% SWRD с теми же cash flow (DCA)",
        "series": series,
    }
    with open(HISTORY_PATH, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    last = series[-1]
    print(f"\nSaved {HISTORY_PATH}")
    print(f"  Days: {len(series)}")
    print(f"  Latest: {last['date']}  "
          f"portfolio=${last['portfolio']:,.2f}  "
          f"invested=${last['invested']:,.2f}  "
          f"benchmark=${last['benchmark']:,.2f}  "
          f"P/L {last['pnl']:+,.2f} ({last['pnl_pct']:+.2f}%)")


if __name__ == "__main__":
    build()
