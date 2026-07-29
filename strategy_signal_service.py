#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""策略信号保存、分组展示与跨时段验证。"""

import json
import uuid
from datetime import date, datetime, time
from typing import Dict, List

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


def save_four_lights_run(db, result: dict) -> str:
    run_id = str(uuid.uuid4())
    for stock in result.get('stocks') or []:
        db.add(StrategySignal(
            run_id=run_id,
            strategy='four_lights',
            scan_session=result['session'],
            code=stock['code'],
            name=stock.get('name'),
            signal_price=float(stock['current_price']),
            score=float(stock.get('score') or 0),
            light_count=int(stock.get('light_count') or 0),
            lights=json.dumps(stock.get('lights') or {}, ensure_ascii=False),
            details=json.dumps(stock.get('details') or {}, ensure_ascii=False),
        ))
    db.commit()
    return run_id


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


def list_signal_runs(db, limit_runs: int = 10) -> List[dict]:
    rows = (
        db.query(StrategySignal)
        .filter(StrategySignal.strategy == 'four_lights')
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
