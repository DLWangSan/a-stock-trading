#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""强势候选股的轻量硬过滤与量化评分。"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import pandas as pd

from data_fetchers import get_daily_kline, get_money_flow_history
from technical_indicators import calculate_indicators


def _limit_time_score(value: Any) -> float:
    text = str(value or '').replace(':', '').zfill(6)
    try:
        minutes = int(text[:2]) * 60 + int(text[2:4])
    except (TypeError, ValueError):
        return 0.0
    # 09:30 满分，11:30 降至 0 分。
    return max(0.0, min(10.0, (690 - minutes) / 12))


def _safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if pd.notna(number) else None
    except (TypeError, ValueError):
        return None


def score_strong_stock(stock: Dict[str, Any]) -> Dict[str, Any]:
    """评分单只候选；任何外部数据失败时降级使用涨停池和实时数据。"""
    score = 0.0
    reasons: List[str] = []
    risks: List[str] = []
    hard_filter_reasons: List[str] = []
    metrics: Dict[str, Any] = {}

    name = str(stock.get('name') or '')
    amount = _safe_float(stock.get('amount'))
    change_percent = _safe_float(stock.get('change_percent'))
    break_count = int(stock.get('break_count') or 0)
    consecutive_days = int(stock.get('consecutive_days') or 0)

    # 1) 封板质量（25分）
    quality_score = _limit_time_score(stock.get('t1_limit_time'))
    quality_score += _limit_time_score(stock.get('t2_limit_time'))
    quality_score += 5 if break_count == 0 else max(0, 5 - break_count * 2.5)
    if 2 <= consecutive_days <= 4:
        quality_score += 2
    score += min(25, quality_score)
    if quality_score >= 18:
        reasons.append('前两日封板时间较早且封板质量较好')
    if break_count:
        risks.append(f'最近炸板{break_count}次')

    # 2) 流动性与当日追高风险（20分）
    if amount is not None:
        if amount >= 500_000_000:
            score += 10
            reasons.append('当日成交额具备较好流动性')
        elif amount >= 200_000_000:
            score += 6
        else:
            hard_filter_reasons.append('成交额低于2亿元')
    else:
        risks.append('成交额缺失')

    if change_percent is not None:
        if -2 <= change_percent <= 5:
            score += 10
        elif 5 < change_percent <= 7:
            score += 4
            risks.append('当日涨幅偏高，注意追高')
        elif change_percent > 7:
            hard_filter_reasons.append('当日涨幅超过7%')
        elif change_percent < -7:
            hard_filter_reasons.append('当日跌幅超过7%')
    else:
        risks.append('实时涨跌幅缺失')

    if 'ST' in name.upper() or '退' in name:
        hard_filter_reasons.append('ST或退市风险标的')
    if break_count >= 2:
        hard_filter_reasons.append('炸板次数不少于2次')

    # 3) 日线趋势与量价（35分）
    try:
        daily = get_daily_kline(str(stock['code']), count=80)
        if daily is not None and len(daily) >= 20:
            daily = calculate_indicators(daily)
            latest = daily.iloc[-1]
            close = _safe_float(latest.get('close'))
            ma5 = _safe_float(latest.get('MA5'))
            ma10 = _safe_float(latest.get('MA10'))
            ma20 = _safe_float(latest.get('MA20'))
            rsi = _safe_float(latest.get('RSI14'))
            dif = _safe_float(latest.get('MACD_DIF'))
            dea = _safe_float(latest.get('MACD_DEA'))
            recent_volume = _safe_float(latest.get('volume'))
            avg_volume = _safe_float(daily['volume'].tail(20).mean()) if 'volume' in daily else None
            volume_ratio = recent_volume / avg_volume if recent_volume and avg_volume else None

            metrics.update({
                'rsi14': round(rsi, 2) if rsi is not None else None,
                'volume_ratio_20d': round(volume_ratio, 2) if volume_ratio is not None else None,
                'ma_bullish': bool(close and ma5 and ma10 and ma20 and close > ma5 > ma10 > ma20),
                'macd_bullish': bool(dif is not None and dea is not None and dif > dea),
            })

            if metrics['ma_bullish']:
                score += 18
                reasons.append('价格与均线呈多头排列')
            elif close and ma20 and close > ma20:
                score += 8
            else:
                risks.append('日线趋势未形成完整多头排列')

            if metrics['macd_bullish']:
                score += 6
            if rsi is not None:
                if 50 <= rsi <= 72:
                    score += 6
                elif rsi > 82:
                    hard_filter_reasons.append('RSI14超过82，短线严重超买')
                elif rsi > 75:
                    risks.append('RSI偏高')
            if volume_ratio is not None:
                if 1.2 <= volume_ratio <= 3:
                    score += 5
                    reasons.append('量能温和放大')
                elif volume_ratio > 5:
                    risks.append('量能异常放大，注意分歧出货')
    except Exception as exc:
        risks.append(f'日线指标获取失败: {str(exc)[:60]}')

    # 4) 近5日资金确认（20分）
    try:
        money_history = get_money_flow_history(str(stock['code']), days=5) or []
        inflows = [
            item.get('main_net_inflow')
            for item in money_history
            if item.get('main_net_inflow') is not None
        ]
        cumulative_inflow = sum(inflows) if inflows else None
        positive_days = sum(1 for value in inflows if value > 0)
        metrics['main_net_inflow_5d_wan'] = round(cumulative_inflow, 2) if cumulative_inflow is not None else None
        metrics['main_inflow_positive_days'] = positive_days
        if cumulative_inflow is not None and cumulative_inflow > 0:
            score += 12
            reasons.append('近5日主力资金累计净流入')
        if positive_days >= 3:
            score += 8
    except Exception as exc:
        risks.append(f'历史资金获取失败: {str(exc)[:60]}')

    score = round(max(0.0, min(100.0, score)), 1)
    eligible = not hard_filter_reasons
    if not eligible:
        score = round(min(score, 59.9), 1)

    return {
        **stock,
        'score': score,
        'eligible': eligible,
        'score_reasons': reasons[:4],
        'risk_flags': risks[:4],
        'hard_filter_reasons': hard_filter_reasons,
        'score_metrics': metrics,
    }


def rank_strong_stocks(stocks: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    if not stocks:
        return []
    with ThreadPoolExecutor(max_workers=min(5, len(stocks))) as executor:
        scored = list(executor.map(score_strong_stock, stocks))
    scored.sort(key=lambda item: (item['eligible'], item['score']), reverse=True)
    recommended = 0
    for index, stock in enumerate(scored, start=1):
        stock['rank'] = index
        stock['recommended'] = stock['eligible'] and recommended < top_n
        if stock['recommended']:
            recommended += 1
    return scored
