#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""独立于涨停池的全市场“四灯共振”策略。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import os
import time
from threading import Lock
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from data_fetchers import get_daily_kline, get_money_flow, get_money_flow_history
from technical_indicators import calculate_indicators


SINA_MARKET_URL = (
    'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/'
    'Market_Center.getHQNodeData'
)
_FLOW_CACHE: Dict[str, tuple] = {}
_FLOW_CACHE_LOCK = Lock()


def _number(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if pd.notna(number) else None
    except (TypeError, ValueError):
        return None


def _session_progress(now: datetime) -> float:
    """返回当日已完成交易时长比例，用于早盘量比折算。"""
    minutes = now.hour * 60 + now.minute
    if minutes < 570:
        return 0.05
    if minutes <= 690:
        return max(0.05, (minutes - 570) / 240)
    if minutes < 780:
        return 0.5
    if minutes <= 900:
        return min(1.0, (120 + minutes - 780) / 240)
    return 1.0


def _get_tushare_capital_flow(code: str) -> List[dict]:
    """可选备用源：配置 TUSHARE_TOKEN 后获取最近5个交易日主力净流入。"""
    token = (os.environ.get('TUSHARE_TOKEN') or '').strip()
    if not token:
        return []
    suffix = 'SH' if code.startswith(('5', '6', '9')) else 'SZ'
    try:
        response = requests.post(
            'http://api.tushare.pro',
            json={
                'api_name': 'moneyflow',
                'token': token,
                'params': {
                    'ts_code': f'{code}.{suffix}',
                    'start_date': (datetime.now() - timedelta(days=15)).strftime('%Y%m%d'),
                    'end_date': datetime.now().strftime('%Y%m%d'),
                },
                'fields': 'trade_date,net_mf_amount',
            },
            timeout=15,
        )
        payload = response.json()
        data = payload.get('data') or {}
        fields = data.get('fields') or []
        rows = data.get('items') or []
        date_index = fields.index('trade_date')
        amount_index = fields.index('net_mf_amount')
        return [
            {
                'date': datetime.strptime(str(row[date_index]), '%Y%m%d').strftime('%Y-%m-%d'),
                'main_net_inflow': _number(row[amount_index]),
                'main_net_ratio': None,
            }
            for row in rows[:5]
            if _number(row[amount_index]) is not None
        ]
    except Exception:
        return []


def _get_capital_flow(code: str, local_history: Optional[List[dict]] = None) -> dict:
    """历史资金优先；短时缓存并重试，失败时降级到当日资金。"""
    now_ts = time.time()
    with _FLOW_CACHE_LOCK:
        cached = _FLOW_CACHE.get(code)
        if cached and now_ts - cached[0] < 300:
            return cached[1]

    history = []
    for attempt in range(2):
        history = get_money_flow_history(code, days=5) or []
        if history:
            break
        if attempt == 0:
            time.sleep(0.2)

    source = 'history_5d' if history else 'unavailable'
    if not history:
        history = _get_tushare_capital_flow(code)
        if history:
            source = 'tushare_5d'
    # 本地累计必须凑满5个交易日才可称为5日资金，避免把单日快照误标为5日。
    if not history and local_history and len(local_history) >= 5:
        history = local_history[:5]
        source = 'local_history'

    today = {}
    if not history:
        try:
            today = get_money_flow(code) or {}
        except Exception:
            today = {}
    result = {
        'history': history,
        'today': today,
        'source': source if history else ('today_fallback' if today else 'unavailable'),
    }
    with _FLOW_CACHE_LOCK:
        _FLOW_CACHE[code] = (now_ts, result)
    return result


def fetch_liquid_a_share_snapshot(pages: int = 3) -> List[Dict[str, Any]]:
    """从全A股中按成交额获取流动性最高的一批候选。"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'http://finance.sina.com.cn',
    }

    def fetch_page(page: int) -> List[Dict[str, Any]]:
        response = requests.get(
            SINA_MARKET_URL,
            params={
                'page': page,
                'num': 100,
                'sort': 'amount',
                'asc': 0,
                'node': 'hs_a',
                'symbol': '',
                '_s_r_a': 'page',
            },
            timeout=15,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    with ThreadPoolExecutor(max_workers=min(3, pages)) as executor:
        page_rows = list(executor.map(fetch_page, range(1, pages + 1)))
    rows = [item for page in page_rows for item in page]
    deduped = {str(item.get('code')): item for item in rows if item.get('code')}
    return list(deduped.values())


def _preselect(rows: List[Dict[str, Any]], limit: int = 30) -> List[Dict[str, Any]]:
    candidates = []
    for row in rows:
        code = str(row.get('code') or '').zfill(6)
        name = str(row.get('name') or '')
        price = _number(row.get('trade'))
        change = _number(row.get('changepercent'))
        amount = _number(row.get('amount'))
        turnover = _number(row.get('turnoverratio'))
        circulating_market_cap = _number(row.get('nmc'))  # 新浪单位：万元
        if (
            not code.isdigit()
            or len(code) != 6
            or not price
            or 'ST' in name.upper()
            or '退' in name
            or amount is None
            or amount < 200_000_000
            or change is None
            or not (-3 <= change <= 7)
            or turnover is None
            or not (1 <= turnover <= 20)
            or (circulating_market_cap is not None and circulating_market_cap < 300_000)
        ):
            continue
        pre_score = (
            min(amount / 100_000_000, 20)
            + max(0, 8 - abs(change - 2))
            + max(0, 8 - abs(turnover - 7) * 0.6)
        )
        candidates.append({
            'code': code,
            'name': name,
            'current_price': price,
            'change_percent': change,
            'amount': amount,
            'volume': _number(row.get('volume')),
            'turnover_rate': turnover,
            'pe': _number(row.get('per')),
            'pb': _number(row.get('pb')),
            'circulating_market_cap_wan': circulating_market_cap,
            '_pre_score': pre_score,
        })
    candidates.sort(key=lambda item: item['_pre_score'], reverse=True)
    return candidates[:limit]


def _analyze_candidate(
    candidate: Dict[str, Any],
    now: datetime,
    local_history: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    lights = {
        'trend': False,
        'momentum': False,
        'volume': False,
        'capital': False,
    }
    details: Dict[str, Any] = {}
    reasons: List[str] = []
    risks: List[str] = []

    try:
        daily = get_daily_kline(candidate['code'], count=90)
        if daily is None or len(daily) < 25:
            raise ValueError('日K数据不足')
        daily = calculate_indicators(daily)
        latest = daily.iloc[-1]
        close = candidate['current_price']
        ma5 = _number(latest.get('MA5'))
        ma10 = _number(latest.get('MA10'))
        ma20 = _number(latest.get('MA20'))
        rsi = _number(latest.get('RSI14'))
        dif = _number(latest.get('MACD_DIF'))
        dea = _number(latest.get('MACD_DEA'))
        closes = daily['close'].dropna()
        return_5d = (
            (close / float(closes.iloc[-6]) - 1) * 100
            if len(closes) >= 6 and float(closes.iloc[-6]) > 0
            else None
        )
        avg_volume = _number(daily['volume'].tail(20).mean())
        projected_volume = (candidate.get('volume') or 0) / _session_progress(now)
        projected_volume_ratio = projected_volume / avg_volume if avg_volume else None

        lights['trend'] = bool(
            ma5 and ma10 and ma20 and close > ma5 > ma10 > ma20
            and dif is not None and dea is not None and dif >= dea
        )
        lights['momentum'] = bool(
            rsi is not None and 50 <= rsi <= 75
            and return_5d is not None and 0 < return_5d <= 18
            and -1.5 <= candidate['change_percent'] <= 6
        )
        lights['volume'] = bool(
            candidate['amount'] >= 300_000_000
            and 2 <= candidate['turnover_rate'] <= 15
            and projected_volume_ratio is not None
            and 1.1 <= projected_volume_ratio <= 3.5
        )
        details.update({
            'ma5': round(ma5, 3) if ma5 is not None else None,
            'ma10': round(ma10, 3) if ma10 is not None else None,
            'ma20': round(ma20, 3) if ma20 is not None else None,
            'macd_dif': round(dif, 4) if dif is not None else None,
            'macd_dea': round(dea, 4) if dea is not None else None,
            'rsi14': round(rsi, 2) if rsi is not None else None,
            'return_5d': round(return_5d, 2) if return_5d is not None else None,
            'projected_volume_ratio': (
                round(projected_volume_ratio, 2)
                if projected_volume_ratio is not None
                else None
            ),
        })
    except Exception as exc:
        risks.append(f'技术数据不足: {str(exc)[:60]}')

    try:
        flow_data = _get_capital_flow(candidate['code'], local_history)
        flows = flow_data['history']
        values = [
            item.get('main_net_inflow')
            for item in flows
            if item.get('main_net_inflow') is not None
        ]
        cumulative = sum(values) if values else None
        positive_days = sum(1 for value in values if value > 0)
        today_inflow = _number(flow_data['today'].get('main_net_inflow'))
        today_ratio = _number(flow_data['today'].get('main_net_ratio'))
        if flow_data['source'] in {'history_5d', 'tushare_5d', 'local_history'}:
            lights['capital'] = bool(cumulative is not None and cumulative > 0 and positive_days >= 3)
        elif flow_data['source'] == 'today_fallback':
            lights['capital'] = bool(
                today_inflow is not None and today_inflow > 0
                and today_ratio is not None and today_ratio >= 3
            )
            risks.append('5日资金暂缺，资金灯使用当日主力净流入降级判断')
        else:
            risks.append('主力资金接口暂时不可用')
        details['main_net_inflow_5d_wan'] = round(cumulative, 2) if cumulative is not None else None
        details['main_inflow_positive_days'] = positive_days
        details['main_net_inflow_today_wan'] = (
            round(today_inflow, 2) if today_inflow is not None else None
        )
        details['main_net_ratio_today'] = (
            round(today_ratio, 2) if today_ratio is not None else None
        )
        details['capital_data_source'] = flow_data['source']
        snapshot_records = [
            {
                'code': candidate['code'],
                'date': item.get('date'),
                'main_net_inflow': item.get('main_net_inflow'),
                'main_net_ratio': item.get('main_net_ratio'),
                'source': flow_data['source'],
            }
            for item in flows
        ]
        if not snapshot_records and today_inflow is not None:
            snapshot_records.append({
                'code': candidate['code'],
                'date': now.strftime('%Y-%m-%d'),
                'main_net_inflow': today_inflow,
                'main_net_ratio': today_ratio,
                'source': 'today_fallback',
            })
    except Exception as exc:
        risks.append(f'资金数据不足: {str(exc)[:60]}')

    light_labels = {
        'trend': '趋势灯',
        'momentum': '动量灯',
        'volume': '量价灯',
        'capital': '资金灯',
    }
    for key, enabled in lights.items():
        if enabled:
            reasons.append(f"{light_labels[key]}点亮")
        else:
            risks.append(f"{light_labels[key]}未点亮")

    light_count = sum(1 for enabled in lights.values() if enabled)
    score = light_count * 20
    score += min(candidate['amount'] / 500_000_000, 1) * 5
    score += max(0, 5 - abs(candidate['change_percent'] - 2))
    score += max(0, 5 - abs(candidate['turnover_rate'] - 7) * 0.5)
    score = round(min(100, score), 1)

    return {
        **{key: value for key, value in candidate.items() if not key.startswith('_')},
        'lights': lights,
        'light_count': light_count,
        'score': score,
        'details': details,
        'score_reasons': reasons,
        'risk_flags': risks[:4],
        '_capital_snapshots': snapshot_records if 'snapshot_records' in locals() else [],
    }


def scan_four_lights(
    session: str = 'auto',
    top_n: int = 5,
    local_capital_flows: Optional[Dict[str, List[dict]]] = None,
) -> dict:
    now = datetime.now()
    resolved_session = (
        'morning' if now.hour < 12 else 'afternoon'
    ) if session == 'auto' else session
    if resolved_session not in {'morning', 'afternoon'}:
        raise ValueError('session 必须是 auto、morning 或 afternoon')

    snapshot = fetch_liquid_a_share_snapshot(pages=3)
    preselected = _preselect(snapshot, limit=30)
    with ThreadPoolExecutor(max_workers=min(6, len(preselected) or 1)) as executor:
        analyzed = list(executor.map(
            lambda item: _analyze_candidate(
                item,
                now,
                (local_capital_flows or {}).get(item['code']),
            ),
            preselected,
        ))
    capital_snapshots = [
        snapshot
        for item in analyzed
        for snapshot in item.pop('_capital_snapshots', [])
    ]
    analyzed.sort(
        key=lambda item: (item['light_count'], item['score']),
        reverse=True,
    )
    candidates = [item for item in analyzed if item['light_count'] >= 2][:top_n]
    if not candidates:
        candidates = analyzed[:top_n]
    for index, item in enumerate(candidates, start=1):
        item['rank'] = index
        item['actionable'] = item['light_count'] >= 3
        item['recommended'] = item['actionable']

    return {
        'strategy': 'four_lights',
        'description': '全市场高流动性股票中筛选趋势、动量、量价、资金四灯共振',
        'strategy_style': 'short_ultra',
        'holding_horizon': '1至5个交易日',
        'session': resolved_session,
        'scan_time': now.isoformat(),
        'universe_count': len(snapshot),
        'preselected_count': len(preselected),
        'count': len(candidates),
        'actionable_count': sum(1 for item in candidates if item['actionable']),
        'stocks': candidates,
        '_capital_snapshots': capital_snapshots,
    }
