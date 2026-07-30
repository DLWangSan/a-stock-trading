#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""持仓、交易画像及 AI 上下文服务。"""

from datetime import datetime
from typing import Optional

from data_fetchers import get_realtime_data
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

# A股卖出手续费：万五，单笔最低5元
SELL_FEE_RATE = 0.0005
SELL_FEE_MIN = 5.0


def calc_sell_fee(price: float, quantity: int) -> float:
    """计算卖出手续费：成交额 * 万五，最低5元。"""
    amount = float(price) * int(quantity)
    if amount <= 0:
        return 0.0
    return round(max(amount * SELL_FEE_RATE, SELL_FEE_MIN), 2)


def apply_sell_trade(db, position: Position, quantity: int, price: float) -> dict:
    """
    执行卖出：
    - 扣减总持仓与今日可卖
    - 剩余持仓成本价不变
    - 现金增加 = 成交额 - 手续费
    - 卖光则删除持仓
    """
    quantity = int(quantity)
    price = float(price)
    if quantity <= 0:
        raise ValueError('卖出数量必须大于0')
    if price <= 0:
        raise ValueError('卖出价格必须大于0')
    if quantity > position.available_quantity:
        raise ValueError(f'卖出数量不能超过今日可卖 {position.available_quantity} 股')
    if quantity > position.quantity:
        raise ValueError(f'卖出数量不能超过总持仓 {position.quantity} 股')

    profile = get_or_create_profile(db)
    code = position.code
    name = position.name
    avg_cost = position.avg_cost
    gross = round(price * quantity, 2)
    fee = calc_sell_fee(price, quantity)
    net = round(gross - fee, 2)
    cost_basis = round(avg_cost * quantity, 2)
    realized_pnl = round(net - cost_basis, 2)

    remaining_qty = position.quantity - quantity
    remaining_available = position.available_quantity - quantity
    deleted = False
    if remaining_qty <= 0:
        db.delete(position)
        deleted = True
    else:
        position.quantity = remaining_qty
        position.available_quantity = remaining_available

    profile.available_cash = round(max(0.0, (profile.available_cash or 0.0) + net), 2)
    db.commit()
    if not deleted:
        db.refresh(position)
    db.refresh(profile)

    return {
        'deleted': deleted,
        'position': None if deleted else serialize_position(position),
        'trade': {
            'code': code,
            'name': name,
            'quantity': quantity,
            'price': price,
            'gross_amount': gross,
            'fee_rate': SELL_FEE_RATE,
            'fee_min': SELL_FEE_MIN,
            'fee': fee,
            'net_amount': net,
            'cost_basis': cost_basis,
            'realized_pnl': realized_pnl,
            'remaining_quantity': 0 if deleted else remaining_qty,
            'available_cash': profile.available_cash,
        },
    }


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
        'available_cash': profile.available_cash or 0,
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


def build_portfolio_snapshot(db) -> dict:
    """获取含实时价格、仓位比例和账户汇总的组合快照。"""
    profile = get_or_create_profile(db)
    positions = db.query(Position).order_by(Position.updated_at.desc()).all()
    rows = []
    for position in positions:
        try:
            realtime = get_realtime_data(position.code)
        except Exception:
            realtime = None
        rows.append(serialize_position(position, realtime))

    total_cost = sum(item['cost_value'] for item in rows)
    known_market_value = sum(
        item['market_value'] for item in rows if item['market_value'] is not None
    )
    market_data_complete = all(item['market_value'] is not None for item in rows)
    available_cash = max(0.0, profile.available_cash or 0.0)
    total_assets = available_cash + known_market_value
    total_profit = known_market_value - total_cost if market_data_complete else None
    total_position_pct = (
        known_market_value / total_assets * 100 if total_assets > 0 else 0.0
    )
    max_position_value = total_assets * profile.max_total_position_pct / 100
    remaining_position_capacity = max(0.0, max_position_value - known_market_value)

    for item in rows:
        item['position_pct'] = (
            item['market_value'] / total_assets * 100
            if item['market_value'] is not None and total_assets > 0
            else None
        )

    return {
        'profile': profile,
        'positions': rows,
        'summary': {
            'position_count': len(rows),
            'total_cost': total_cost,
            'total_market_value': known_market_value if rows else 0.0,
            'market_data_complete': market_data_complete,
            'total_profit': total_profit,
            'total_profit_pct': (
                total_profit / total_cost * 100
                if total_profit is not None and total_cost > 0
                else None
            ),
            'available_cash': available_cash,
            'total_assets': total_assets,
            'total_position_pct': total_position_pct,
            'remaining_position_capacity': remaining_position_capacity,
            'available_for_new_position': min(available_cash, remaining_position_capacity),
        },
    }


def build_ai_portfolio_context(db, code: Optional[str] = None) -> str:
    """生成给 LLM 使用的确定性持仓/风格上下文。"""
    snapshot = build_portfolio_snapshot(db)
    profile = snapshot['profile']
    profile_data = serialize_profile(profile)
    positions = snapshot['positions']
    summary = snapshot['summary']

    lines = [
        '【用户交易上下文】',
        f"交易风格: {profile_data['style_label']} ({profile_data['holding_horizon']})",
        f"风险偏好: {profile.risk_level}",
        f"分析重点: {profile_data['focus']}",
        f"单票最大仓位: {profile.max_single_position_pct:.1f}%",
        f"总仓位上限: {profile.max_total_position_pct:.1f}%",
        f"默认止损/止盈: {profile.default_stop_loss_pct:.1f}% / {profile.default_take_profit_pct:.1f}%",
        f"允许日内做T: {'是' if profile.allow_intraday_t else '否'}",
        '【账户资金（勿混淆）】',
        f"可用现金(账户现金余额): {summary['available_cash']:.2f}元",
        f"持仓市值: {summary['total_market_value']:.2f}元",
        f"估算总资产(=可用现金+持仓市值): {summary['total_assets']:.2f}元",
        f"当前总仓位: {summary['total_position_pct']:.1f}%",
        f"总仓位上限下剩余容量: {summary['remaining_position_capacity']:.2f}元",
        (
            f"受总仓位约束后的可新开仓额度(=min(可用现金, 剩余容量)): "
            f"{summary['available_for_new_position']:.2f}元"
        ),
        '注意: “可新开仓额度”不是可用现金；可用现金以“可用现金(账户现金余额)”为准。',
    ]
    if not summary['market_data_complete']:
        lines.append('注意: 部分持仓实时行情缺失，组合市值与仓位为不完整估算。')
    if profile.notes:
        lines.append(f"用户补充: {profile.notes}")

    if not positions:
        lines.append('当前没有已录入持仓。请以观察/建仓建议为主，不要虚构持仓数量。')
    else:
        lines.append('当前持仓:')
        for item in positions:
            opened_at = datetime.fromisoformat(item['opened_at']) if item['opened_at'] else None
            holding_days = (datetime.now() - opened_at).days if opened_at else None
            days_text = f'{holding_days}天' if holding_days is not None else '未知'
            target_mark = ' [当前分析标的]' if code and item['code'] == code else ''
            lines.append(
                f"- {item['name']}({item['code']}){target_mark}: 总持仓{item['quantity']}股, "
                f"今日可卖{item['available_quantity']}股, 成本{item['avg_cost']:.2f}, "
                f"现价{item['current_price'] if item['current_price'] is not None else '缺失'}, "
                f"浮盈亏{item['profit_pct'] if item['profit_pct'] is not None else '缺失'}%, "
                f"仓位{item['position_pct'] if item['position_pct'] is not None else '缺失'}%, "
                f"持有{days_text}, 目标价{item['target_price'] if item['target_price'] is not None else '未设'}, "
                f"止损价{item['stop_loss_price'] if item['stop_loss_price'] is not None else '未设'}"
            )
            if item['thesis']:
                lines.append(f"  持仓逻辑: {item['thesis']}")
        if code and not any(item['code'] == code for item in positions):
            lines.append(f'当前分析标的 {code} 尚未持有，应按新开仓约束计算。')

    lines.extend([
        '输出要求:',
        '- 给出明确动作：买入/加仓/持有/减仓/清仓/做T/暂不交易。',
        '- 必须给出价格区间、建议数量或仓位、止损、止盈、建议有效期和失效条件。',
        '- A股实行T+1；做T卖出数量不得超过“今日可卖”数量。',
        '- 明确不等于强制交易；证据不足时可暂不交易，但必须写出等待的触发条件。',
    ])
    return '\n'.join(lines)
