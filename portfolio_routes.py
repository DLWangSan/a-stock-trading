#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""持仓管理与交易画像 API。"""

from datetime import datetime

from flask import jsonify, request

from data_fetchers import get_realtime_data
from models import Position, SessionLocal
from portfolio_service import (
    RISK_LEVELS,
    STYLE_META,
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
            market_values = [item['market_value'] for item in rows if item['market_value'] is not None]
            total_market_value = sum(market_values) if market_values else None
            total_profit = total_market_value - total_cost if total_market_value is not None else None
            return jsonify({
                'success': True,
                'data': {
                    'profile': serialize_profile(profile),
                    'positions': rows,
                    'summary': {
                        'position_count': len(rows),
                        'total_cost': total_cost,
                        'total_market_value': total_market_value,
                        'total_profit': total_profit,
                        'total_profit_pct': (
                            total_profit / total_cost * 100
                            if total_profit is not None and total_cost > 0
                            else None
                        ),
                    },
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
            return jsonify({'success': True, 'data': serialize_position(position)})
        except ValueError as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
