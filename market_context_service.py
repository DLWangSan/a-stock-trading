#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""为组合级 AI 分析构建市场情绪快照。"""

from datetime import datetime
from statistics import median

from data_fetchers import get_realtime_data
from four_lights_strategy import fetch_liquid_a_share_snapshot


def build_market_sentiment_context() -> str:
    index_specs = [
        ('上证指数', 'sh000001'),
        ('深证成指', 'sz399001'),
        ('创业板指', 'sz399006'),
    ]
    index_rows = []
    index_changes = []
    for name, code in index_specs:
        try:
            quote = get_realtime_data(code) or {}
            change = quote.get('change_percent')
            index_rows.append(
                f"- {name}: {quote.get('current_price', '缺失')} "
                f"({f'{change:+.2f}%' if change is not None else '涨跌幅缺失'})"
            )
            if change is not None:
                index_changes.append(float(change))
        except Exception:
            index_rows.append(f'- {name}: 数据缺失')

    breadth_text = '高流动性样本宽度数据缺失'
    breadth_ratio = None
    try:
        snapshot = fetch_liquid_a_share_snapshot(pages=3)
        changes = [
            float(item['changepercent'])
            for item in snapshot
            if item.get('changepercent') not in (None, '')
        ]
        advancers = sum(1 for change in changes if change > 0)
        decliners = sum(1 for change in changes if change < 0)
        breadth_ratio = advancers / max(decliners, 1)
        breadth_text = (
            f"成交额前{len(changes)}只样本: 上涨{advancers}只, 下跌{decliners}只, "
            f"涨跌家数比{breadth_ratio:.2f}, 中位涨跌幅{median(changes):+.2f}%"
        )
    except Exception:
        pass

    limit_text = '涨跌停情绪数据缺失'
    try:
        import akshare as ak

        date_text = datetime.now().strftime('%Y%m%d')
        up = ak.stock_zt_pool_em(date=date_text)
        down = ak.stock_dt_pool_em(date=date_text)
        up_count = len(up) if up is not None else 0
        down_count = len(down) if down is not None else 0
        limit_text = f'涨停{up_count}只, 跌停{down_count}只'
    except Exception:
        pass

    average_index = sum(index_changes) / len(index_changes) if index_changes else 0
    if average_index >= 0.5 and (breadth_ratio is None or breadth_ratio >= 1.2):
        regime = '偏强，可考虑正常仓位但避免追高'
    elif average_index <= -0.5 or (breadth_ratio is not None and breadth_ratio < 0.8):
        regime = '偏弱，应降低总仓位并优先处理风险持仓'
    else:
        regime = '震荡，控制节奏并按个股强弱调仓'

    return '\n'.join([
        '【市场情绪快照】',
        *index_rows,
        f'- 市场宽度: {breadth_text}',
        f'- 涨跌停情绪: {limit_text}',
        f'- 环境判断: {regime}',
        '- 数据仅使用当前时点可获得的信息，不得据此虚构未来走势。',
    ])
