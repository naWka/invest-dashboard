#!/usr/bin/env python3
"""
Калькулятор покупки ETF по Инвестиционному плану v3.0
Использование: python buy_calculator.py [--amount СУММА]
Читает данные из ../data/portfolio.json, рассчитывает оптимальные покупки.
"""

import json
import math
import os
import sys
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_PATH = os.path.join(SCRIPT_DIR, "..", "data", "portfolio.json")

TARGET = {"SWRD": 0.70, "EIMI": 0.15, "USSC": 0.15}
ETF_ORDER = ["SWRD", "EIMI", "USSC"]


def load_portfolio():
    with open(PORTFOLIO_PATH, "r") as f:
        return json.load(f)


def save_portfolio(data):
    with open(PORTFOLIO_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def calculate_purchase(holdings: dict, prices: dict, cash: float, amount: float):
    """
    Рассчитывает оптимальные покупки по алгоритму из Части 3 плана.

    Returns: dict с ключами buy_orders, new_holdings, remaining_cash, deviations
    """
    # Шаг 1: текущая стоимость
    current_values = {}
    for etf in ETF_ORDER:
        current_values[etf] = holdings.get(etf, {}).get("shares", 0) * prices[etf]

    portfolio_current = sum(current_values.values())

    # Шаг 2: целевая стоимость после покупки
    portfolio_future = portfolio_current + amount
    targets = {etf: portfolio_future * TARGET[etf] for etf in ETF_ORDER}

    # Шаг 3: дефициты
    deficits = {etf: targets[etf] - current_values[etf] for etf in ETF_ORDER}

    # Шаг 4: покупки в порядке наибольшего дефицита
    sorted_etfs = sorted(ETF_ORDER, key=lambda e: deficits[e], reverse=True)

    remaining = amount
    buy_orders = {etf: 0 for etf in ETF_ORDER}

    for etf in sorted_etfs:
        if deficits[etf] <= 0:
            continue

        max_shares = math.floor(min(deficits[etf], remaining) / prices[etf])
        if max_shares > 0:
            buy_orders[etf] = max_shares
            remaining -= max_shares * prices[etf]

    # Попробовать купить ещё, если остаток позволяет
    for etf in sorted_etfs:
        if remaining < prices[etf]:
            continue
        extra = math.floor(remaining / prices[etf])
        if extra > 0:
            buy_orders[etf] += extra
            remaining -= extra * prices[etf]

    # Новое состояние
    new_holdings = {}
    new_values = {}
    for etf in ETF_ORDER:
        new_shares = holdings.get(etf, {}).get("shares", 0) + buy_orders[etf]
        new_holdings[etf] = new_shares
        new_values[etf] = new_shares * prices[etf]

    new_total = sum(new_values.values())

    deviations = {}
    for etf in ETF_ORDER:
        actual_pct = (new_values[etf] / new_total * 100) if new_total > 0 else 0
        target_pct = TARGET[etf] * 100
        deviations[etf] = {
            "actual": round(actual_pct, 1),
            "target": target_pct,
            "deviation": round(actual_pct - target_pct, 1)
        }

    return {
        "buy_orders": buy_orders,
        "costs": {etf: round(buy_orders[etf] * prices[etf], 2) for etf in ETF_ORDER},
        "total_spent": round(amount - remaining, 2),
        "remaining_cash": round(remaining, 2),
        "new_holdings": new_holdings,
        "new_values": {etf: round(v, 2) for etf, v in new_values.items()},
        "new_total": round(new_total, 2),
        "deviations": deviations,
        "deficits": {etf: round(v, 2) for etf, v in deficits.items()}
    }


def print_result(result, prices):
    print("\n" + "=" * 60)
    print("  РЕКОМЕНДАЦИЯ К ПОКУПКЕ")
    print("=" * 60)

    print(f"\n{'ETF':<8} {'Дефицит':>10} {'Купить шт.':>12} {'Сумма':>10}")
    print("-" * 44)
    for etf in ETF_ORDER:
        d = result["deficits"][etf]
        s = result["buy_orders"][etf]
        c = result["costs"][etf]
        marker = " ←" if s > 0 else ""
        print(f"{etf:<8} ${d:>9.2f} {s:>12} ${c:>9.2f}{marker}")

    print(f"\n💰 Потрачено: ${result['total_spent']:.2f}")
    print(f"💵 Остаток (кэш): ${result['remaining_cash']:.2f}")

    print(f"\n{'─' * 60}")
    print(f"  ПОРТФЕЛЬ ПОСЛЕ ПОКУПКИ")
    print(f"{'─' * 60}")
    print(f"\n{'ETF':<8} {'Штук':>6} {'Стоимость':>12} {'Доля':>8} {'Цель':>8} {'Откл.':>8}")
    print("-" * 54)
    for etf in ETF_ORDER:
        sh = result["new_holdings"][etf]
        val = result["new_values"][etf]
        dev = result["deviations"][etf]
        status = "✅" if abs(dev["deviation"]) <= 2 else "⚠️" if abs(dev["deviation"]) <= 5 else "❌"
        print(f"{etf:<8} {sh:>6} ${val:>11.2f} {dev['actual']:>7.1f}% {dev['target']:>7.0f}% {dev['deviation']:>+7.1f}% {status}")

    print(f"\n📊 Итого портфель: ${result['new_total']:.2f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Калькулятор покупки ETF")
    parser.add_argument("--amount", type=float, help="Сумма для покупки (USD)")
    parser.add_argument("--apply", action="store_true", help="Сохранить покупку в portfolio.json")
    args = parser.parse_args()

    data = load_portfolio()
    holdings = data["holdings"]
    prices = data["prices"]
    cash = data["cash_usd"]

    # Показать текущее состояние
    print("\n📋 Текущий портфель:")
    total = 0
    for etf in ETF_ORDER:
        sh = holdings[etf]["shares"]
        p = prices[etf]
        val = sh * p
        total += val
        print(f"  {etf}: {sh} шт. × ${p} = ${val:.2f}")
    print(f"  💵 Кэш: ${cash:.2f}")
    print(f"  📊 Итого: ${total + cash:.2f}")

    amount = args.amount
    if amount is None:
        try:
            amount = float(input("\nСумма для покупки ($): "))
        except (ValueError, EOFError):
            print("Ошибка: введите число")
            sys.exit(1)

    result = calculate_purchase(holdings, prices, cash, amount)
    print_result(result, prices)

    if args.apply:
        for etf in ETF_ORDER:
            old_shares = data["holdings"][etf]["shares"]
            bought = result["buy_orders"][etf]
            if bought > 0:
                old_avg = data["holdings"][etf]["avg_price"]
                new_avg = (old_shares * old_avg + bought * prices[etf]) / (old_shares + bought)
                data["holdings"][etf]["shares"] = old_shares + bought
                data["holdings"][etf]["avg_price"] = round(new_avg, 2)

                data["transactions"].append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "buy",
                    "etf": etf,
                    "shares": bought,
                    "price": prices[etf],
                    "total": round(bought * prices[etf], 2)
                })

        data["cash_usd"] = round(cash - result["total_spent"] + result["remaining_cash"], 2)
        data["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_portfolio(data)
        print("✅ Портфель обновлён в portfolio.json\n")


if __name__ == "__main__":
    main()
