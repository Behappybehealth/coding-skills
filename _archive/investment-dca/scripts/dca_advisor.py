#!/usr/bin/env python3
"""
Daily DCA advisor for S&P 500, Nasdaq 100, and Gold.

This script fetches recent market data from Yahoo Finance's public chart endpoint,
computes simple valuation/momentum/risk signals, recommends a daily allocation in
CNY, and keeps a local simulation ledger under ~/.claude/investment-dca/.

It is an educational decision-support model, not financial advice.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ASSETS = {
    "sp500": {
        "name": "标普500",
        "symbol": "^GSPC",
        "base_weight": 0.45,
        "min_weight": 0.25,
        "max_weight": 0.60,
        "risk_level": "中高",
        "proxy_note": "可用宽基标普500 ETF/QDII/互联互通产品替代，注意汇率、溢价和费率。",
    },
    "nasdaq100": {
        "name": "纳指100",
        "symbol": "^NDX",
        "base_weight": 0.35,
        "min_weight": 0.15,
        "max_weight": 0.55,
        "risk_level": "高",
        "proxy_note": "可用纳指100 ETF/QDII/LOF 等替代，波动大，注意溢价和限购。",
    },
    "gold": {
        "name": "黄金",
        "symbol": "GC=F",
        "base_weight": 0.20,
        "min_weight": 0.10,
        "max_weight": 0.35,
        "risk_level": "中",
        "proxy_note": "可用黄金ETF、积存金或实物金替代，注意买卖价差和保管成本。",
    },
}

DATA_DIR = Path.home() / ".claude" / "investment-dca"
LEDGER_FILE = DATA_DIR / "portfolio.json"
CSV_FILE = DATA_DIR / "daily_records.csv"


@dataclass
class Quote:
    key: str
    name: str
    symbol: str
    currency: str
    price: float
    prev_close: float
    day_change_pct: float
    closes: List[float]
    timestamps: List[int]


@dataclass
class Metrics:
    ma20: Optional[float]
    ma60: Optional[float]
    ma120: Optional[float]
    ma200: Optional[float]
    rsi14: Optional[float]
    pct_from_252_high: Optional[float]
    pct_from_252_low: Optional[float]
    percentile_252: Optional[float]
    annual_vol: Optional[float]
    signal: float
    signal_label: str
    signal_reason: str


def fetch_json(url: str, timeout: int = 20) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 dca-advisor"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_chart(symbol: str, range_: str = "1y", interval: str = "1d") -> Dict[str, Any]:
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range={range_}&interval={interval}&includePrePost=false"
    data = fetch_json(url)
    chart = data.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo Finance error for {symbol}: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise RuntimeError(f"No chart data returned for {symbol}")
    return results[0]


def fetch_quote(key: str, cfg: Dict[str, Any]) -> Quote:
    result = fetch_chart(cfg["symbol"])
    meta = result.get("meta", {})
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes_raw = quote.get("close") or []
    closes = [float(x) for x in closes_raw if x is not None and x > 0]
    if not closes:
        raise RuntimeError(f"No close prices for {cfg['symbol']}")
    price = float(meta.get("regularMarketPrice") or closes[-1])
    prev_close = float(meta.get("chartPreviousClose") or (closes[-2] if len(closes) > 1 else closes[-1]))
    if len(closes) >= 2 and closes[-1] != price:
        prev_close = closes[-1]
    day_change_pct = (price / prev_close - 1) * 100 if prev_close else 0.0
    return Quote(
        key=key,
        name=cfg["name"],
        symbol=cfg["symbol"],
        currency=meta.get("currency", "USD"),
        price=price,
        prev_close=prev_close,
        day_change_pct=day_change_pct,
        closes=closes,
        timestamps=timestamps,
    )


def fetch_usdcny() -> float:
    try:
        result = fetch_chart("CNY=X", range_="5d")
        meta = result.get("meta", {})
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = [float(x) for x in quote.get("close", []) if x is not None and x > 0]
        return float(meta.get("regularMarketPrice") or closes[-1])
    except Exception:
        return 7.20


def avg(xs: Iterable[float]) -> Optional[float]:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) <= period:
        return None
    gains: List[float] = []
    losses: List[float] = []
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def annual_vol(closes: List[float]) -> Optional[float]:
    if len(closes) < 31:
        return None
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    recent = returns[-60:] if len(returns) >= 60 else returns
    if len(recent) < 20:
        return None
    mean = sum(recent) / len(recent)
    var = sum((x - mean) ** 2 for x in recent) / (len(recent) - 1)
    return math.sqrt(var) * math.sqrt(252) * 100


def compute_metrics(q: Quote) -> Metrics:
    closes = q.closes
    price = q.price
    ma20 = avg(closes[-20:]) if len(closes) >= 20 else None
    ma60 = avg(closes[-60:]) if len(closes) >= 60 else None
    ma120 = avg(closes[-120:]) if len(closes) >= 120 else None
    ma200 = avg(closes[-200:]) if len(closes) >= 200 else None
    rsi14 = rsi(closes, 14)
    window = closes[-252:] if len(closes) >= 30 else closes
    hi = max(window)
    lo = min(window)
    pct_from_high = (price / hi - 1) * 100 if hi else None
    pct_from_low = (price / lo - 1) * 100 if lo else None
    percentile = (price - lo) / (hi - lo) if hi > lo else 0.5
    vol = annual_vol(closes)

    # Signal: positive means invest more today; negative means invest less.
    signal = 0.0
    reasons: List[str] = []

    if percentile <= 0.20:
        signal += 0.22
        reasons.append("接近一年低位")
    elif percentile <= 0.35:
        signal += 0.12
        reasons.append("低于一年中位区间")
    elif percentile >= 0.85:
        signal -= 0.18
        reasons.append("接近一年高位")
    elif percentile >= 0.70:
        signal -= 0.08
        reasons.append("处在偏高区间")

    if ma200:
        dist200 = price / ma200 - 1
        if dist200 <= -0.12:
            signal += 0.20
            reasons.append("显著低于200日均线")
        elif dist200 <= -0.05:
            signal += 0.10
            reasons.append("低于200日均线")
        elif dist200 >= 0.18:
            signal -= 0.16
            reasons.append("显著高于200日均线")
        elif dist200 >= 0.08:
            signal -= 0.08
            reasons.append("高于200日均线")

    if rsi14 is not None:
        if rsi14 < 30:
            signal += 0.12
            reasons.append("RSI超卖")
        elif rsi14 > 72:
            signal -= 0.12
            reasons.append("RSI偏热")

    if q.day_change_pct <= -2.5:
        signal += 0.08
        reasons.append("当日大跌")
    elif q.day_change_pct >= 2.5:
        signal -= 0.06
        reasons.append("当日大涨")

    if vol is not None and vol > 35:
        signal -= 0.05
        reasons.append("近期波动较高")

    signal = max(-0.35, min(0.35, signal))
    if signal >= 0.18:
        label = "加倍投入"
    elif signal >= 0.06:
        label = "适度多投"
    elif signal <= -0.18:
        label = "明显少投"
    elif signal <= -0.06:
        label = "适度少投"
    else:
        label = "常规定投"

    return Metrics(
        ma20=ma20,
        ma60=ma60,
        ma120=ma120,
        ma200=ma200,
        rsi14=rsi14,
        pct_from_252_high=pct_from_high,
        pct_from_252_low=pct_from_low,
        percentile_252=percentile,
        annual_vol=vol,
        signal=signal,
        signal_label=label,
        signal_reason="、".join(reasons) if reasons else "估值/趋势信号中性",
    )


def load_ledger() -> Dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LEDGER_FILE.exists():
        with LEDGER_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cash_cny": 0.0,
        "positions": {key: {"units": 0.0, "cost_cny": 0.0} for key in ASSETS},
        "records": [],
    }


def save_ledger(ledger: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    tmp.replace(LEDGER_FILE)


def append_csv(record: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    exists = CSV_FILE.exists()
    fields = [
        "date", "amount_cny", "invested_cny", "portfolio_value_cny", "total_cost_cny",
        "profit_cny", "return_pct", "annualized_return_pct", "xirr_pct", "allocation_json"
    ]
    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in fields})


def normalize_weights(raw: Dict[str, float]) -> Dict[str, float]:
    clipped = {
        k: max(ASSETS[k]["min_weight"], min(ASSETS[k]["max_weight"], v))
        for k, v in raw.items()
    }
    total = sum(clipped.values())
    return {k: v / total for k, v in clipped.items()}


def recommend_weights(metrics: Dict[str, Metrics]) -> Dict[str, float]:
    raw = {}
    for key, cfg in ASSETS.items():
        raw[key] = cfg["base_weight"] + metrics[key].signal

    # If both US equity buckets are hot, shift part of the excess to gold/cash-like defense.
    if metrics["sp500"].signal < -0.10 and metrics["nasdaq100"].signal < -0.10:
        raw["gold"] += 0.08
    # If risk assets are in drawdown but gold is very hot, still reserve some for equities.
    if metrics["gold"].signal < -0.15 and (metrics["sp500"].signal > 0.10 or metrics["nasdaq100"].signal > 0.10):
        raw["gold"] -= 0.05

    return normalize_weights(raw)


def leverage_note(metrics: Dict[str, Metrics]) -> str:
    sp = metrics["sp500"]
    ndx = metrics["nasdaq100"]
    deep_drawdown = (
        (sp.pct_from_252_high is not None and sp.pct_from_252_high <= -18) or
        (ndx.pct_from_252_high is not None and ndx.pct_from_252_high <= -25)
    )
    trend_repair = (sp.ma200 and sp.ma60 and sp.ma60 >= sp.ma200 * 0.97) or (ndx.ma200 and ndx.ma60 and ndx.ma60 >= ndx.ma200 * 0.97)
    if deep_drawdown and trend_repair:
        return "若你能承受高波动，可只用总资金的5%~10%做低杠杆/分批网格试探；不要融资满仓，不要日内追涨。"
    if deep_drawdown:
        return "出现深度回撤，但趋势未确认修复；优先增加普通定投，不建议急于上杠杆。"
    return "当前不建议使用杠杆；长期定投阶段应把杠杆视为极端低位、严格限额的工具。"


def portfolio_value(ledger: Dict[str, Any], quotes: Dict[str, Quote], usdcny: float) -> Tuple[float, float, float]:
    value = float(ledger.get("cash_cny", 0.0))
    cost = 0.0
    for key in ASSETS:
        pos = ledger.get("positions", {}).get(key, {})
        units = float(pos.get("units", 0.0))
        cost += float(pos.get("cost_cny", 0.0))
        value += units * quotes[key].price * usdcny
    profit = value - cost
    return value, cost, profit


def annualized_return(return_pct: float, days: int) -> float:
    if days <= 1:
        return 0.0
    r = return_pct / 100
    if r <= -0.999:
        return -100.0
    return ((1 + r) ** (365 / days) - 1) * 100


def parse_record_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def xnpv(rate: float, cashflows: List[Tuple[datetime, float]]) -> float:
    first_date = cashflows[0][0]
    return sum(
        amount / ((1 + rate) ** ((date - first_date).days / 365.0))
        for date, amount in cashflows
    )


def xirr(cashflows: List[Tuple[datetime, float]]) -> Optional[float]:
    cashflows = [(date, amount) for date, amount in cashflows if amount]
    if len(cashflows) < 2:
        return None
    if min(date for date, _ in cashflows) == max(date for date, _ in cashflows):
        return None
    if not any(amount < 0 for _, amount in cashflows) or not any(amount > 0 for _, amount in cashflows):
        return None

    low = -0.999999
    high = 1.0
    low_npv = xnpv(low, cashflows)
    high_npv = xnpv(high, cashflows)
    for _ in range(80):
        if low_npv == 0:
            return low * 100
        if high_npv == 0:
            return high * 100
        if low_npv * high_npv < 0:
            break
        high *= 2
        if high > 1_000_000:
            return None
        high_npv = xnpv(high, cashflows)
    else:
        return None

    for _ in range(100):
        mid = (low + high) / 2
        mid_npv = xnpv(mid, cashflows)
        if abs(mid_npv) < 1e-7:
            return mid * 100
        if low_npv * mid_npv <= 0:
            high = mid
            high_npv = mid_npv
        else:
            low = mid
            low_npv = mid_npv
    return ((low + high) / 2) * 100


def portfolio_xirr(ledger: Dict[str, Any], current_value: float, as_of: str) -> Optional[float]:
    cashflows: List[Tuple[datetime, float]] = []
    for record in ledger.get("records", []):
        date = parse_record_date(record.get("date"))
        invested = float(record.get("invested_cny") or record.get("amount_cny") or 0.0)
        if date and invested:
            cashflows.append((date, -invested))
    as_of_date = parse_record_date(as_of)
    if as_of_date and current_value:
        cashflows.append((as_of_date, current_value))
    return xirr(cashflows)


def fmt_money(x: float) -> str:
    return f"¥{x:,.2f}"


def fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x:+.2f}%"


def fmt_num(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x:,.2f}"


def fmt_units(x: float) -> str:
    if abs(x) >= 1:
        return f"{x:,.4f}"
    if abs(x) >= 0.0001:
        return f"{x:,.6f}"
    return f"{x:,.8f}"


def fmt_plain_pct(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x:.2f}%"


def monthly_budget_status(ledger: Dict[str, Any], monthly_budget: float, today: str) -> Dict[str, Any]:
    today_dt = parse_record_date(today) or datetime.now()
    next_month = (
        datetime(today_dt.year + 1, 1, 1)
        if today_dt.month == 12
        else datetime(today_dt.year, today_dt.month + 1, 1)
    )
    remaining_days = max(1, (next_month.date() - today_dt.date()).days)
    month_prefix = today[:7]
    invested_this_month = 0.0
    for record in ledger.get("records", []):
        if str(record.get("date", "")).startswith(month_prefix):
            invested_this_month += float(record.get("invested_cny") or record.get("amount_cny") or 0.0)
    remaining_budget = max(0.0, monthly_budget - invested_this_month)
    return {
        "month": month_prefix,
        "monthly_budget_cny": monthly_budget,
        "invested_this_month_cny": invested_this_month,
        "remaining_budget_cny": remaining_budget,
        "remaining_days_in_month": remaining_days,
        "daily_reference_cny": remaining_budget / remaining_days,
    }


def build_position_rows(ledger: Dict[str, Any], quotes: Dict[str, Quote], usdcny: float, total_value: float) -> List[Dict[str, Any]]:
    rows = []
    for key, cfg in ASSETS.items():
        pos = ledger.get("positions", {}).get(key, {})
        units = float(pos.get("units", 0.0))
        cost = float(pos.get("cost_cny", 0.0))
        value = units * quotes[key].price * usdcny
        profit = value - cost
        rows.append({
            "key": key,
            "name": cfg["name"],
            "symbol": quotes[key].symbol,
            "units": units,
            "cost_cny": cost,
            "price": quotes[key].price,
            "value_cny": value,
            "profit_cny": profit,
            "return_pct": (profit / cost * 100) if cost else 0.0,
            "weight_pct": (value / total_value * 100) if total_value else 0.0,
        })
    return rows


def print_position_section(
    periods: int,
    cost: float,
    value: float,
    profit: float,
    return_pct: float,
    ann_pct: float,
    xirr_pct: Optional[float],
    rows: List[Dict[str, Any]],
    last_record: Optional[Dict[str, Any]],
    recorded: bool,
    record_requested: bool,
) -> None:
    print("## 5. 累计持仓结果完整表")
    record_status = "已写入今日模拟成交" if recorded else "本次未写入"
    record_hint = "—" if record_requested else "认可本日建议后，可追加 --record 写入模拟组合"
    print("| 类别 | 项目 | 代码/日期 | 期数 | 持有份额 | 最新价(USD) | 成本(CNY) | 市值(CNY) | 盈亏/投入(CNY) | 收益率 | 年化收益 | XIRR/仓位 | 状态/备注 |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    print(
        f"| **组合总览** | **合计** | — | **{periods}** | — | — | **{fmt_money(cost)}** | "
        f"**{fmt_money(value)}** | **{fmt_money(profit)}** | **{fmt_pct(return_pct)}** | "
        f"**{fmt_pct(ann_pct)}** | **{fmt_pct(xirr_pct)}** | {record_status}；{record_hint} |"
    )
    if last_record:
        print(
            f"| 最近记录 | 当期模拟买入 | {last_record.get('date', 'N/A')} | {periods} | — | — | "
            f"{fmt_money(float(last_record.get('total_cost_cny', 0.0)))} | "
            f"{fmt_money(float(last_record.get('portfolio_value_cny', 0.0)))} | "
            f"{fmt_money(float(last_record.get('invested_cny', 0.0)))} | "
            f"{fmt_pct(float(last_record.get('return_pct', 0.0)))} | "
            f"{fmt_pct(float(last_record.get('annualized_return_pct', 0.0)))} | "
            f"{fmt_pct(last_record.get('xirr_pct'))} | 最近一次本地成交快照 |"
        )
    else:
        print("| 最近记录 | 暂无本地模拟成交 | — | 0 | — | — | ¥0.00 | ¥0.00 | ¥0.00 | N/A | N/A | N/A | 使用 --record 后开始累计 |")
    for row in rows:
        print(
            f"| 持仓明细 | {row['name']} | {row['symbol']} | {periods} | {fmt_units(row['units'])} | "
            f"{fmt_num(row['price'])} | {fmt_money(row['cost_cny'])} | {fmt_money(row['value_cny'])} | "
            f"{fmt_money(row['profit_cny'])} | {fmt_pct(row['return_pct'])} | — | {fmt_plain_pct(row['weight_pct'])} | — |"
        )


def today_local() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Daily DCA advisor for SP500/Nasdaq100/Gold")
    p.add_argument("amount", nargs="?", type=float, default=1500.0, help="今日计划定投金额，人民币，默认1500")
    p.add_argument("--monthly", type=float, default=30000.0, help="每月可投资金额，人民币，默认30000")
    p.add_argument("--record", action="store_true", help="将今日建议按模拟成交写入本地组合记录")
    p.add_argument("--reset", action="store_true", help="清空本地模拟组合记录")
    p.add_argument("--json", action="store_true", help="输出机器可读JSON")
    p.add_argument("--section5", action="store_true", help="只输出第5部分：累计持仓结果完整表格")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.reset:
        if LEDGER_FILE.exists():
            LEDGER_FILE.unlink()
        if CSV_FILE.exists():
            CSV_FILE.unlink()
        print(f"已重置本地记录：{DATA_DIR}")
        return 0

    errors: List[str] = []
    quotes: Dict[str, Quote] = {}
    for key, cfg in ASSETS.items():
        try:
            quotes[key] = fetch_quote(key, cfg)
        except Exception as e:
            errors.append(str(e))

    if len(quotes) != len(ASSETS):
        print("无法取得完整行情数据。", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 2

    usdcny = fetch_usdcny()
    metrics = {key: compute_metrics(q) for key, q in quotes.items()}
    weights = recommend_weights(metrics)

    ledger = load_ledger()
    today = today_local()
    month_status = monthly_budget_status(ledger, args.monthly, today)
    effective_amount = min(args.amount, month_status["remaining_budget_cny"])
    allocations = {key: round(effective_amount * weights[key], 2) for key in ASSETS}

    # Fix rounding drift.
    drift = round(effective_amount - sum(allocations.values()), 2)
    if drift:
        biggest = max(allocations, key=allocations.get)
        allocations[biggest] = round(allocations[biggest] + drift, 2)

    if effective_amount < args.amount:
        errors.append(
            f"本自然月剩余预算 {fmt_money(month_status['remaining_budget_cny'])} 低于本次输入金额 {fmt_money(args.amount)}，建议金额已按剩余预算封顶。"
        )

    before_value, before_cost, before_profit = portfolio_value(ledger, quotes, usdcny)
    record = None

    if args.record:
        date = today_local()
        # Avoid accidental duplicate recording for the same date unless user edits ledger manually.
        if any(r.get("date") == date for r in ledger.get("records", [])):
            errors.append(f"今天 {date} 已经记录过一次；为避免重复买入，本次只给建议未写入。")
        else:
            for key, cny in allocations.items():
                usd = cny / usdcny
                units = usd / quotes[key].price
                pos = ledger["positions"].setdefault(key, {"units": 0.0, "cost_cny": 0.0})
                pos["units"] = float(pos.get("units", 0.0)) + units
                pos["cost_cny"] = float(pos.get("cost_cny", 0.0)) + cny
            after_value, after_cost, after_profit = portfolio_value(ledger, quotes, usdcny)
            days = max(1, len(ledger.get("records", [])) + 1)
            ret_pct = (after_profit / after_cost * 100) if after_cost else 0.0
            ann = annualized_return(ret_pct, days)
            record = {
                "date": date,
                "amount_cny": args.amount,
                "invested_cny": sum(allocations.values()),
                "portfolio_value_cny": after_value,
                "total_cost_cny": after_cost,
                "profit_cny": after_profit,
                "return_pct": ret_pct,
                "annualized_return_pct": ann,
                "allocation_json": json.dumps(allocations, ensure_ascii=False),
            }
            ledger.setdefault("records", []).append(record)
            record["xirr_pct"] = portfolio_xirr(ledger, after_value, date)
            save_ledger(ledger)
            append_csv(record)

    value, cost, profit = portfolio_value(ledger, quotes, usdcny)
    periods = len(ledger.get("records", []))
    return_pct = (profit / cost * 100) if cost else 0.0
    ann_pct = annualized_return(return_pct, max(1, periods)) if periods else 0.0
    xirr_pct = portfolio_xirr(ledger, value, today_local()) if periods else None
    position_rows = build_position_rows(ledger, quotes, usdcny, value)
    last_record = ledger.get("records", [])[-1] if ledger.get("records") else None

    result = {
        "date": today,
        "amount_cny": args.amount,
        "effective_amount_cny": effective_amount,
        "monthly_budget_cny": args.monthly,
        "monthly_budget_status": month_status,
        "usdcny": usdcny,
        "quotes": {k: quotes[k].__dict__ | {"closes": [], "timestamps": []} for k in ASSETS},
        "metrics": {k: metrics[k].__dict__ for k in ASSETS},
        "weights": weights,
        "allocations_cny": allocations,
        "portfolio": {
            "periods": periods,
            "value_cny": value,
            "cost_cny": cost,
            "profit_cny": profit,
            "return_pct": return_pct,
            "annualized_return_pct": ann_pct,
            "xirr_pct": xirr_pct,
        },
        "leverage_note": leverage_note(metrics),
        "errors": errors,
        "recorded": record is not None,
        "data_dir": str(DATA_DIR),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.section5:
        print_position_section(periods, cost, value, profit, return_pct, ann_pct, xirr_pct, position_rows, last_record, record is not None, args.record)
        return 0

    print("# 每日定投建议：标普500 / 纳指100 / 黄金")
    print()
    print(f"日期：{result['date']}  |  输入金额：{fmt_money(args.amount)}  |  今日建议金额：{fmt_money(effective_amount)}  |  月度可投资额：{fmt_money(args.monthly)}")
    print(f"自然月进度：本月已投 {fmt_money(month_status['invested_this_month_cny'])}，剩余 {fmt_money(month_status['remaining_budget_cny'])}，剩余 {month_status['remaining_days_in_month']} 天，日均参考 {fmt_money(month_status['daily_reference_cny'])}")
    print(f"参考汇率：USD/CNY ≈ {usdcny:.4f}")
    print()
    print("## 今日建议分配")
    for key, cfg in ASSETS.items():
        w = weights[key] * 100
        print(f"- {cfg['name']}：{fmt_money(allocations[key])}（{w:.1f}%）— {metrics[key].signal_label}；{metrics[key].signal_reason}")
    print()
    print("## 行情与信号")
    print("| 标的 | 最新价 | 日涨跌 | 20日线 | 60日线 | 200日线 | RSI14 | 距一年高点 | 年化波动 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for key, cfg in ASSETS.items():
        q = quotes[key]
        m = metrics[key]
        print(
            f"| {cfg['name']} ({q.symbol}) | {fmt_num(q.price)} | {fmt_pct(q.day_change_pct)} | "
            f"{fmt_num(m.ma20)} | {fmt_num(m.ma60)} | {fmt_num(m.ma200)} | {fmt_num(m.rsi14)} | "
            f"{fmt_pct(m.pct_from_252_high)} | {fmt_pct(m.annual_vol)} |"
        )
    print()
    print("## 资金策略")
    print(f"- 按自然月口径，本月预算 {fmt_money(args.monthly)}，已记录投入 {fmt_money(month_status['invested_this_month_cny'])}，剩余预算 {fmt_money(month_status['remaining_budget_cny'])}；本次建议按 {fmt_money(effective_amount)} 执行。")
    print(f"- 自然月剩余 {month_status['remaining_days_in_month']} 天，剩余预算折算日均约 {fmt_money(month_status['daily_reference_cny'])}；后续可随行情在日均参考上方或下方浮动。")
    print("- 当单一标的进入“加倍投入/适度多投”时，可从自然月剩余预算中额外加仓；当进入“明显少投”时，少投部分留作现金弹药。")
    print("- 单日加仓上限建议：普通日不超过日预算的1.5倍；深度回撤且非系统性流动性危机时，不超过2.0倍，并分3~5天执行。")
    print(f"- 杠杆提示：{result['leverage_note']}")
    print("- 若要加入其他品种，优先考虑：中长期美债/货币基金作为现金管理，或全球股票/红利低波资产降低单一科技暴露；不要因为短期排名追逐主题赛道。")
    print()
    print_position_section(periods, cost, value, profit, return_pct, ann_pct, xirr_pct, position_rows, last_record, record is not None, args.record)
    print()
    print("## 风险提示")
    print("本模型只用于定投纪律和仓位辅助，不保证收益，不构成个性化投资建议。指数、期货和汇率数据可能延迟；实际交易请以你的券商/基金平台报价、费率、溢价和税务规则为准。")
    if errors:
        print()
        print("## 提示")
        for e in errors:
            print(f"- {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
