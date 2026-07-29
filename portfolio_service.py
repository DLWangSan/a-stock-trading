#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""持仓、交易画像及 AI 上下文服务。"""

from datetime import datetime
from typing import Optional

from models import Position, TradingProfile


STYLE_META = {
    'ultra_short': {
        'label': '超短线',
        'horizon': '盘中至2个交易日',
        'focus': '真实分钟量价、VWAP、盘口强弱、板块情绪与即时止损',
    },
    'short': {
        'label': '短线',
        'horizon': '3至20个交易日',
        'focus': '趋势、量价、资金、题材持续性与关键支撑阻力',
    },
    'medium': {
        'label': '中线',
        'horizon': '1至6个月',
        'focus': '日周趋势、盈利变化、行业景气与估值修复',
    },
    'long': {
        'label': '长线',
        'horizon': '6个月以上',
        'focus': '商业质量、长期盈利、估值安全边际与投资逻辑',
    },
}

RISK_LEVELS = {'conservative', 'balanced', 'aggressive'}


def get_or_create_profile(db) -> TradingProfile:
    profile = db.query(TradingProfile).filter(TradingProfile.id == 1).first()
    if profile:
        return profile
    profile = TradingProfile(id=1)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def serialize_profile(profile: TradingProfile) -> dict:
    meta = STYLE_META.get(profile.style, STYLE_META['short'])
    return {
        'style': profile.style,
        'style_label': meta['label'],
        'holding_horizon': meta['horizon'],
        'focus': meta['focus'],
        'risk_level': profile.risk_level,
        'max_single_position_pct': profile.max_single_position_pct,
        'max_total_position_pct': profile.max_total_position_pct,
        'default_stop_loss_pct': profile.default_stop_loss_pct,
        'default_take_profit_pct': profile.default_take_profit_pct,
        'allow_intraday_t': profile.allow_intraday_t,
        'notes': profile.notes or '',
        'updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
    }


def serialize_position(position: Position, realtime: Optional[dict] = None) -> dict:
    current_price = realtime.get('current_price') if realtime else None
    market_value = current_price * position.quantity if current_price is not None else None
    cost_value = position.avg_cost * position.quantity
    profit = market_value - cost_value if market_value is not None else None
    profit_pct = (
        (current_price - position.avg_cost) / position.avg_cost * 100
        if current_price is not None and position.avg_cost > 0
        else None
    )
    return {
        'id': position.id,
        'code': position.code,
        'name': (realtime or {}).get('name') or position.name or position.code,
        'quantity': position.quantity,
        'available_quantity': position.available_quantity,
        'avg_cost': position.avg_cost,
        'opened_at': position.opened_at.isoformat() if position.opened_at else None,
        'target_price': position.target_price,
        'stop_loss_price': position.stop_loss_price,
        'thesis': position.thesis or '',
        'notes': position.notes or '',
        'current_price': current_price,
        'change_percent': (realtime or {}).get('change_percent'),
        'market_value': market_value,
        'cost_value': cost_value,
        'profit': profit,
        'profit_pct': profit_pct,
        'updated_at': position.updated_at.isoformat() if position.updated_at else None,
    }


def build_ai_portfolio_context(db, code: Optional[str] = None) -> str:
    """生成给 LLM 使用的确定性持仓/风格上下文。"""
    profile = get_or_create_profile(db)
    profile_data = serialize_profile(profile)
    query = db.query(Position)
    if code:
        query = query.filter(Position.code == code)
    positions = query.order_by(Position.updated_at.desc()).all()

    lines = [
        '【用户交易上下文】',
        f"交易风格: {profile_data['style_label']} ({profile_data['holding_horizon']})",
        f"风险偏好: {profile.risk_level}",
        f"分析重点: {profile_data['focus']}",
        f"单票最大仓位: {profile.max_single_position_pct:.1f}%",
        f"总仓位上限: {profile.max_total_position_pct:.1f}%",
        f"默认止损/止盈: {profile.default_stop_loss_pct:.1f}% / {profile.default_take_profit_pct:.1f}%",
        f"允许日内做T: {'是' if profile.allow_intraday_t else '否'}",
    ]
    if profile.notes:
        lines.append(f"用户补充: {profile.notes}")

    if not positions:
        lines.append('当前标的未录入持仓。请以观察/建仓建议为主，不要虚构持仓数量。')
    else:
        lines.append('当前持仓:')
        for p in positions:
            holding_days = (datetime.now() - p.opened_at).days if p.opened_at else None
            days_text = f'{holding_days}天' if holding_days is not None else '未知'
            lines.append(
                f"- {p.name or p.code}({p.code}): 总持仓{p.quantity}股, "
                f"今日可卖{p.available_quantity}股, 成本{p.avg_cost:.2f}, 持有{days_text}, "
                f"目标价{p.target_price if p.target_price is not None else '未设'}, "
                f"止损价{p.stop_loss_price if p.stop_loss_price is not None else '未设'}"
            )
            if p.thesis:
                lines.append(f"  持仓逻辑: {p.thesis}")

    lines.extend([
        '输出要求:',
        '- 给出明确动作：买入/加仓/持有/减仓/清仓/做T/暂不交易。',
        '- 必须给出价格区间、建议数量或仓位、止损、止盈、建议有效期和失效条件。',
        '- A股实行T+1；做T卖出数量不得超过“今日可卖”数量。',
        '- 明确不等于强制交易；证据不足时可暂不交易，但必须写出等待的触发条件。',
    ])
    return '\n'.join(lines)
