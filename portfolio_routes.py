#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""持仓管理与交易画像 API。"""

from datetime import datetime

from flask import jsonify, request

from data_fetchers import get_realtime_data
from models import Position, SessionLocal, Watchlist
from portfolio_service import (
    RISK_LEVELS,
    STYLE_META,
    apply_sell_trade,
    build_portfolio_snapshot,
    get_or_create_profile,
    serialize_position,
    serialize_profile,
)


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        raise ValueError('opened_at 必须是 ISO 日期时间')


def _validate_position_payload(data, existing=None):
    code = str(data.get('code', existing.code if existing else '')).strip()
    if not code.isdigit() or len(code) != 6:
        raise ValueError('股票代码必须是6位数字')

    quantity = int(data.get('quantity', existing.quantity if existing else 0))
    available = int(data.get(
        'available_quantity',
        existing.available_quantity if existing else quantity,
    ))
    avg_cost = float(data.get('avg_cost', existing.avg_cost if existing else 0))
    if quantity < 0 or available < 0 or avg_cost < 0:
        raise ValueError('数量和成本不能为负数')
    if available > quantity:
        raise ValueError('今日可卖数量不能大于总持仓')
    return code, quantity, available, avg_cost


def _sync_positions_to_watchlist(db):
    """持仓必定出现在自选中；移除持仓时保留自选记录。"""
    existing_codes = {
        row[0] for row in db.query(Watchlist.code).all()
    }
    added = 0
    for position in db.query(Position).all():
        if position.code not in existing_codes:
            db.add(Watchlist(code=position.code, name=position.name))
            existing_codes.add(position.code)
            added += 1
    if added:
        db.commit()
    return added


def register_portfolio_routes(app):
    @app.route('/api/trading-profile', methods=['GET', 'PUT'])
    def trading_profile_api():
        db = SessionLocal()
        try:
            profile = get_or_create_profile(db)
            if request.method == 'PUT':
                data = request.get_json(silent=True) or {}
                style = data.get('style', profile.style)
                risk_level = data.get('risk_level', profile.risk_level)
                if style not in STYLE_META:
                    return jsonify({'success': False, 'error': '不支持的交易风格'}), 400
                if risk_level not in RISK_LEVELS:
                    return jsonify({'success': False, 'error': '不支持的风险等级'}), 400

                profile.style = style
                profile.risk_level = risk_level
                for field in [
                    'max_single_position_pct',
                    'max_total_position_pct',
                    'default_stop_loss_pct',
                    'default_take_profit_pct',
                ]:
                    if field in data:
                        value = float(data[field])
                        if value < 0 or value > 100:
                            return jsonify({'success': False, 'error': f'{field} 必须在0到100之间'}), 400
                        setattr(profile, field, value)
                if 'available_cash' in data:
                    available_cash = float(data['available_cash'])
                    if available_cash < 0:
                        return jsonify({'success': False, 'error': 'available_cash 不能为负数'}), 400
                    profile.available_cash = available_cash
                if 'allow_intraday_t' in data:
                    profile.allow_intraday_t = bool(data['allow_intraday_t'])
                if 'notes' in data:
                    profile.notes = str(data['notes']).strip()
                db.commit()
                db.refresh(profile)
            return jsonify({'success': True, 'data': serialize_profile(profile)})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()

    @app.route('/api/portfolio', methods=['GET'])
    def portfolio_api():
        db = SessionLocal()
        try:
            _sync_positions_to_watchlist(db)
            snapshot = build_portfolio_snapshot(db)
            return jsonify({
                'success': True,
                'data': {
                    'profile': serialize_profile(snapshot['profile']),
                    'positions': snapshot['positions'],
                    'summary': snapshot['summary'],
                },
            })
        finally:
            db.close()

    @app.route('/api/portfolio/positions', methods=['POST'])
    def create_position_api():
        db = SessionLocal()
        try:
            data = request.get_json(silent=True) or {}
            code, quantity, available, avg_cost = _validate_position_payload(data)
            if db.query(Position).filter(Position.code == code).first():
                return jsonify({'success': False, 'error': '该股票已在持仓中'}), 409

            name = str(data.get('name') or '').strip()
            if not name:
                realtime = get_realtime_data(code)
                name = (realtime or {}).get('name') or code
            position = Position(
                code=code,
                name=name,
                quantity=quantity,
                available_quantity=available,
                avg_cost=avg_cost,
                opened_at=_parse_datetime(data.get('opened_at')),
                target_price=float(data['target_price']) if data.get('target_price') not in (None, '') else None,
                stop_loss_price=float(data['stop_loss_price']) if data.get('stop_loss_price') not in (None, '') else None,
                thesis=str(data.get('thesis') or '').strip(),
                notes=str(data.get('notes') or '').strip(),
            )
            db.add(position)
            db.commit()
            db.refresh(position)
            _sync_positions_to_watchlist(db)
            return jsonify({'success': True, 'data': serialize_position(position)}), 201
        except ValueError as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()

    @app.route('/api/portfolio/positions/<int:position_id>', methods=['PUT', 'DELETE'])
    def position_item_api(position_id):
        db = SessionLocal()
        try:
            position = db.query(Position).filter(Position.id == position_id).first()
            if not position:
                return jsonify({'success': False, 'error': '持仓不存在'}), 404
            if request.method == 'DELETE':
                db.delete(position)
                db.commit()
                return jsonify({'success': True})

            data = request.get_json(silent=True) or {}
            code, quantity, available, avg_cost = _validate_position_payload(data, position)
            duplicate = db.query(Position).filter(
                Position.code == code,
                Position.id != position.id,
            ).first()
            if duplicate:
                return jsonify({'success': False, 'error': '该股票已在持仓中'}), 409
            position.code = code
            position.quantity = quantity
            position.available_quantity = available
            position.avg_cost = avg_cost
            for field in ['name', 'thesis', 'notes']:
                if field in data:
                    setattr(position, field, str(data[field] or '').strip())
            if 'opened_at' in data:
                position.opened_at = _parse_datetime(data['opened_at'])
            for field in ['target_price', 'stop_loss_price']:
                if field in data:
                    setattr(position, field, float(data[field]) if data[field] not in (None, '') else None)
            db.commit()
            db.refresh(position)
            _sync_positions_to_watchlist(db)
            return jsonify({'success': True, 'data': serialize_position(position)})
        except ValueError as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()

    @app.route('/api/portfolio/positions/<int:position_id>/sell', methods=['POST'])
    def sell_position_api(position_id):
        """卖出持仓：万五手续费、最低5元；回笼现金；成本价对剩余股数不变。"""
        db = SessionLocal()
        try:
            position = db.query(Position).filter(Position.id == position_id).first()
            if not position:
                return jsonify({'success': False, 'error': '持仓不存在'}), 404
            data = request.get_json(silent=True) or {}
            quantity = int(data.get('quantity') or 0)
            price = float(data.get('price') or 0)
            result = apply_sell_trade(db, position, quantity, price)
            return jsonify({'success': True, 'data': result})
        except ValueError as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
