#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""尾盘隔夜超短策略：尾盘买入，默认次日竞价/开盘卖出。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from data_fetchers import get_daily_kline
from four_lights_strategy import (
    _number,
    _session_progress,
    fetch_liquid_a_share_snapshot,
)
from technical_indicators import calculate_indicators


def _is_main_board(code: str) -> bool:
    return code.startswith(('00', '60')) and not code.startswith(('688', '8', '4'))


def _limit_threshold(code: str) -> float:
    if code.startswith(('300', '688')):
        return 0.195
    return 0.095


def _has_limit_memory(daily, code: str, lookback: int = 5) -> Dict[str, Any]:
    if daily is None or len(daily) < lookback + 1:
        return {'has_memory': False, 'recent_limit_days': 0, 'last_limit_ago': None}
    threshold = _limit_threshold(code)
    recent = daily.tail(lookback + 1).copy()
    closes = recent['close'].astype(float)
    prev = closes.shift(1)
    limit_flags = (closes / prev - 1) >= threshold
    # 只看过去 lookback 日，不含当日未收盘确认
    historical = limit_flags.iloc[:-1]
    recent_limit_days = int(historical.sum())
    last_limit_ago = None
    if recent_limit_days:
        reversed_flags = list(reversed(historical.tolist()))
        last_limit_ago = reversed_flags.index(True) + 1
    return {
        'has_memory': recent_limit_days > 0,
        'recent_limit_days': recent_limit_days,
        'last_limit_ago': last_limit_ago,
    }


def _preselect_overnight(rows: List[Dict[str, Any]], limit: int = 40) -> List[Dict[str, Any]]:
    candidates = []
    for row in rows:
        code = str(row.get('code') or '').zfill(6)
        name = str(row.get('name') or '')
        price = _number(row.get('trade'))
        change = _number(row.get('changepercent'))
        amount = _number(row.get('amount'))
        turnover = _number(row.get('turnoverratio'))
        circulating_market_cap = _number(row.get('nmc'))  # 万元
        if (
            not code.isdigit()
            or len(code) != 6
            or not _is_main_board(code)
            or not price
            or 'ST' in name.upper()
            or '退' in name
            or amount is None
            or amount < 250_000_000
            or change is None
            or not (2.5 <= change <= 6.0)
            or turnover is None
            or not (3.5 <= turnover <= 12.0)
            or circulating_market_cap is None
            or not (500_000 <= circulating_market_cap <= 3_500_000)
        ):
            continue
        pre_score = (
            max(0, 10 - abs(change - 4) * 2)
            + max(0, 8 - abs(turnover - 7) * 0.8)
            + min(amount / 200_000_000, 8)
            + max(0, 5 - abs(circulating_market_cap / 10000 - 120) / 40)
        )
        candidates.append({
            'code': code,
            'name': name,
            'current_price': price,
            'change_percent': change,
            'amount': amount,
            'volume': _number(row.get('volume')),
            'turnover_rate': turnover,
            'circulating_market_cap_wan': circulating_market_cap,
            '_pre_score': pre_score,
        })
    candidates.sort(key=lambda item: item['_pre_score'], reverse=True)
    return candidates[:limit]


def _analyze_overnight(candidate: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    reasons: List[str] = []
    risks: List[str] = []
    details: Dict[str, Any] = {}
    checks = {
        'gain_band': False,
        'liquidity': False,
        'limit_memory': False,
        'above_ma5': False,
        'volume_active': False,
    }

    try:
        daily = get_daily_kline(candidate['code'], count=60)
        if daily is None or len(daily) < 20:
            raise ValueError('日K数据不足')
        daily = calculate_indicators(daily)
        latest = daily.iloc[-1]
        ma5 = _number(latest.get('MA5'))
        close = candidate['current_price']
        avg_volume = _number(daily['volume'].tail(20).mean())
        projected_volume = (candidate.get('volume') or 0) / _session_progress(now)
        projected_volume_ratio = projected_volume / avg_volume if avg_volume else None
        memory = _has_limit_memory(daily, candidate['code'], lookback=5)

        checks['gain_band'] = 2.5 <= candidate['change_percent'] <= 6.0
        checks['liquidity'] = (
            candidate['amount'] >= 250_000_000
            and 3.5 <= candidate['turnover_rate'] <= 12.0
        )
        checks['limit_memory'] = bool(memory['has_memory'])
        checks['above_ma5'] = bool(ma5 and close >= ma5)
        checks['volume_active'] = bool(
            projected_volume_ratio is not None and projected_volume_ratio >= 1.0
        )

        details.update({
            'ma5': round(ma5, 3) if ma5 is not None else None,
            'projected_volume_ratio': (
                round(projected_volume_ratio, 2) if projected_volume_ratio is not None else None
            ),
            'recent_limit_days': memory['recent_limit_days'],
            'last_limit_ago': memory['last_limit_ago'],
            'circulating_market_cap_yi': round(candidate['circulating_market_cap_wan'] / 10000, 1),
        })

        if checks['gain_band']:
            reasons.append('当日涨幅落在隔夜优选区间')
        else:
            risks.append('涨幅不在2.5%-6%优选带')
        if checks['liquidity']:
            reasons.append('成交额与换手具备隔夜承接')
        else:
            risks.append('流动性或换手偏离超短偏好')
        if checks['limit_memory']:
            ago = memory['last_limit_ago']
            reasons.append(f'近5日有涨停记忆（约{ago}日前）' if ago else '近5日有涨停记忆')
        else:
            risks.append('近5日无涨停记忆')
        if checks['above_ma5']:
            reasons.append('现价站上MA5')
        else:
            risks.append('现价跌破MA5')
        if checks['volume_active']:
            reasons.append('量能活跃')
        else:
            risks.append('量能偏弱')
    except Exception as exc:
        risks.append(f'技术数据不足: {str(exc)[:60]}')

    pass_count = sum(1 for enabled in checks.values() if enabled)
    score = pass_count * 16
    score += max(0, 8 - abs(candidate['change_percent'] - 4) * 2)
    score += max(0, 6 - abs(candidate['turnover_rate'] - 7) * 0.7)
    score += min(candidate['amount'] / 400_000_000, 1) * 6
    score = round(min(100, score), 1)

    actionable = pass_count >= 4 and checks.get('limit_memory') and checks.get('gain_band')
    return {
        **{key: value for key, value in candidate.items() if not key.startswith('_')},
        'checks': checks,
        'pass_count': pass_count,
        'score': score,
        'details': details,
        'score_reasons': reasons,
        'risk_flags': risks[:4],
        'actionable': actionable,
        'recommended': actionable,
        'sell_plan': '次日集合竞价或开盘优先卖出；高开冲高乏力立即减仓，低开弱势直接止损',
        'holding_horizon': '隔夜至次日早盘',
    }


def scan_overnight(top_n: int = 5) -> dict:
    """扫描适合尾盘买入、次日卖出的隔夜候选。"""
    now = datetime.now()
    snapshot = fetch_liquid_a_share_snapshot(pages=4)
    preselected = _preselect_overnight(snapshot, limit=40)
    with ThreadPoolExecutor(max_workers=min(6, len(preselected) or 1)) as executor:
        analyzed = list(executor.map(lambda item: _analyze_overnight(item, now), preselected))

    analyzed.sort(key=lambda item: (item['pass_count'], item['score']), reverse=True)
    candidates = [item for item in analyzed if item['pass_count'] >= 3][:top_n]
    if not candidates:
        candidates = analyzed[:top_n]
    for index, item in enumerate(candidates, start=1):
        item['rank'] = index

    afternoon_ready = now.hour > 14 or (now.hour == 14 and now.minute >= 20)
    return {
        'strategy': 'overnight',
        'description': '尾盘筛选隔夜强势票，默认次日竞价/开盘卖出',
        'strategy_style': 'overnight_ultra',
        'holding_horizon': '隔夜至次日早盘',
        'session': 'afternoon',
        'scan_time': now.isoformat(),
        'afternoon_ready': afternoon_ready,
        'timing_note': (
            '当前已进入尾盘观察窗口，更适合执行隔夜计划'
            if afternoon_ready
            else '当前偏早，结果可作观察；真正执行建议14:20后复核'
        ),
        'universe_count': len(snapshot),
        'preselected_count': len(preselected),
        'count': len(candidates),
        'actionable_count': sum(1 for item in candidates if item['actionable']),
        'stocks': candidates,
        'rules': {
            'gain_band': '当日涨幅 2.5%–6%',
            'liquidity': '成交额≥2.5亿，换手 3.5%–12%，流通市值约50–350亿',
            'limit_memory': '近5个交易日出现过涨停记忆',
            'structure': '现价≥MA5，预计量比≥1.0',
            'exit': '次日竞价或开盘优先卖出',
        },
    }
