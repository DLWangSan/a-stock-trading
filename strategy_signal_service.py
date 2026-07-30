#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""策略信号保存、分组展示与跨时段验证。"""

import json
import uuid
from datetime import date, datetime, time
from typing import Dict, List, Optional

from data_fetchers import get_realtime_data
from models import CapitalFlowSnapshot, StrategySignal


def get_local_capital_flow_map(db, days: int = 7) -> Dict[str, List[dict]]:
    rows = (
        db.query(CapitalFlowSnapshot)
        .order_by(CapitalFlowSnapshot.trade_date.desc())
        .limit(1000)
        .all()
    )
    result: Dict[str, List[dict]] = {}
    for row in rows:
        bucket = result.setdefault(row.code, [])
        if len(bucket) < days:
            bucket.append({
                'date': row.trade_date,
                'main_net_inflow': row.main_net_inflow,
                'main_net_ratio': row.main_net_ratio,
            })
    return result


def save_capital_flow_snapshots(db, snapshots: List[dict]) -> int:
    saved = 0
    for item in snapshots:
        code = str(item.get('code') or '')
        trade_date = str(item.get('date') or '')[:10]
        if len(code) != 6 or len(trade_date) != 10:
            continue
        row = db.query(CapitalFlowSnapshot).filter(
            CapitalFlowSnapshot.code == code,
            CapitalFlowSnapshot.trade_date == trade_date,
        ).first()
        if row is None:
            row = CapitalFlowSnapshot(code=code, trade_date=trade_date)
            db.add(row)
        row.main_net_inflow = item.get('main_net_inflow')
        row.main_net_ratio = item.get('main_net_ratio')
        row.source = item.get('source')
        saved += 1
    if saved:
        db.commit()
    return saved


def save_strategy_run(db, strategy: str, result: dict) -> str:
    """通用策略扫描快照保存，供跨时段验证。"""
    run_id = str(uuid.uuid4())
    for stock in result.get('stocks') or []:
        lights = stock.get('lights') or stock.get('checks') or {}
        light_count = stock.get('light_count')
        if light_count is None:
            light_count = int(stock.get('pass_count') or sum(1 for enabled in lights.values() if enabled))
        details = dict(stock.get('details') or {})
        if stock.get('sell_plan'):
            details['sell_plan'] = stock['sell_plan']
        if stock.get('holding_horizon'):
            details['holding_horizon'] = stock['holding_horizon']
        db.add(StrategySignal(
            run_id=run_id,
            strategy=strategy,
            scan_session=result.get('session') or 'afternoon',
            code=stock['code'],
            name=stock.get('name'),
            signal_price=float(stock['current_price']),
            score=float(stock.get('score') or 0),
            light_count=int(light_count or 0),
            lights=json.dumps(lights, ensure_ascii=False),
            details=json.dumps(details, ensure_ascii=False),
        ))
    db.commit()
    return run_id


def save_four_lights_run(db, result: dict) -> str:
    return save_strategy_run(db, 'four_lights', result)


def save_overnight_run(db, result: dict) -> str:
    return save_strategy_run(db, 'overnight', result)


def _quote_date(realtime: dict) -> date:
    raw = str(realtime.get('date') or '')
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return datetime.now().date()


def _is_due(signal: StrategySignal, realtime: dict, now: datetime) -> bool:
    quote_day = _quote_date(realtime)
    created_day = signal.created_at.date()
    if signal.scan_session == 'morning':
        return (
            quote_day > created_day
            or (quote_day == created_day and now.time() >= time(14, 30))
        )
    return quote_day > created_day


def validate_pending_signals(db, limit: int = 30) -> int:
    pending = (
        db.query(StrategySignal)
        .filter(StrategySignal.validation_status == 'pending')
        .order_by(StrategySignal.created_at.asc())
        .limit(limit)
        .all()
    )
    now = datetime.now()
    updated = 0
    quote_cache: Dict[str, dict] = {}
    for signal in pending:
        try:
            realtime = quote_cache.get(signal.code)
            if realtime is None:
                realtime = get_realtime_data(signal.code) or {}
                quote_cache[signal.code] = realtime
            price = realtime.get('current_price')
            if price is None or not _is_due(signal, realtime, now):
                continue
            signal.validation_price = float(price)
            signal.validation_return_pct = (
                (signal.validation_price / signal.signal_price - 1) * 100
                if signal.signal_price > 0
                else None
            )
            signal.validation_status = 'validated'
            signal.validated_at = now
            updated += 1
        except Exception:
            continue
    if updated:
        db.commit()
    return updated


def delete_signal_run(db, run_id: str, strategy: Optional[str] = None) -> int:
    """删除一次策略扫描及其全部验证记录，不影响资金流快照。"""
    query = db.query(StrategySignal).filter(StrategySignal.run_id == run_id)
    if strategy:
        query = query.filter(StrategySignal.strategy == strategy)
    deleted = query.delete(synchronize_session=False)
    if deleted:
        db.commit()
    return deleted


def delete_all_signal_runs(db, strategy: str) -> int:
    """清空某一策略的全部历史信号与验证记录。"""
    deleted = (
        db.query(StrategySignal)
        .filter(StrategySignal.strategy == strategy)
        .delete(synchronize_session=False)
    )
    if deleted:
        db.commit()
    return deleted


def list_signal_runs(db, limit_runs: int = 10, strategy: str = 'four_lights') -> List[dict]:
    rows = (
        db.query(StrategySignal)
        .filter(StrategySignal.strategy == strategy)
        .order_by(StrategySignal.created_at.desc(), StrategySignal.id.asc())
        .limit(max(1, limit_runs) * 10)
        .all()
    )
    grouped: Dict[str, dict] = {}
    for row in rows:
        run = grouped.setdefault(row.run_id, {
            'run_id': row.run_id,
            'strategy': row.strategy,
            'session': row.scan_session,
            'created_at': row.created_at.isoformat(),
            'validation_status': 'validated',
            'stocks': [],
        })
        if row.validation_status != 'validated':
            run['validation_status'] = 'pending'
        run['stocks'].append({
            'code': row.code,
            'name': row.name,
            'signal_price': row.signal_price,
            'score': row.score,
            'light_count': row.light_count,
            'lights': json.loads(row.lights or '{}'),
            'details': json.loads(row.details or '{}'),
            'validation_status': row.validation_status,
            'validation_price': row.validation_price,
            'validation_return_pct': row.validation_return_pct,
            'validated_at': row.validated_at.isoformat() if row.validated_at else None,
        })
    return list(grouped.values())[:limit_runs]
