#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API路由模块"""

from flask import jsonify, request
import hashlib
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from datetime import datetime
import json
import re
from data_fetchers import get_realtime_data, get_timeline_data, get_minute_kline, get_daily_kline, get_money_flow, get_money_flow_history, get_money_flow_realtime_kline, get_fundamental_data, get_industry_comparison, get_news_from_stock, get_guba_posts
from technical_indicators import calculate_indicators, get_comprehensive_data, get_comprehensive_data_with_indicators
from data_formatters import format_for_ai, to_json
import requests
from datetime import date, timedelta
from models import get_db, Position, SessionLocal
from db import (
    get_watchlist, add_to_watchlist, remove_from_watchlist, update_watchlist_order,
    get_config, set_config, get_all_configs,
    get_agents, get_agent, create_agent, update_agent, delete_agent,
    get_cached_analysis, save_analysis_cache,
    create_debate_job, update_debate_job, get_debate_job, list_debate_jobs, cancel_debate_job, delete_debate_job
)
from ai_service import AIService
from four_lights_strategy import scan_four_lights
from overnight_strategy import scan_overnight
from market_context_service import build_market_sentiment_context
from portfolio_service import build_ai_portfolio_context
from strategy_scorer import rank_strong_stocks
from strategy_signal_service import (
    delete_all_signal_runs,
    delete_signal_run,
    get_local_capital_flow_map,
    list_signal_runs,
    save_capital_flow_snapshots,
    save_four_lights_run,
    save_overnight_run,
    validate_pending_signals,
)
from pipeline_feishu import (
    execute_strategy_to_multi_debate,
    check_pipeline_token,
    feishu_webhook_send_text,
    parse_feishu_message_text,
    feishu_should_trigger,
    handle_feishu_event_body,
    verify_feishu_event_token,
    run_pipeline_in_thread,
)

def register_routes(app):
    """注册所有API路由"""
    
    @app.route('/')
    def index():
        """首页 - API文档"""
        response = jsonify({
            'message': '股票数据API服务（新浪API）',
            'version': '3.0.0',
            'endpoints': {
                '/api/sina/comprehensive/<code>': '获取股票综合数据（实时、分钟K线、分时、日K线）',
                '/api/sina/comprehensive_with_indicators/<code>': '获取股票综合数据（包含技术指标：MA/EMA/MACD/RSI/KDJ/BOLL/OBV）',
                '/api/sina/realtime/<code>': '获取实时行情数据',
                '/api/sina/timeline/<code>': '获取分时数据（每分钟）',
                '/api/sina/minute/<code>': '获取分钟K线数据，参数: ?scale=5&datalen=240',
                '/api/sina/daily/<code>': '获取日K线数据，参数: ?count=240',
                '/api/sina/money_flow/<code>': '获取今日资金流向数据',
                '/api/sina/money_flow/history/<code>': '获取历史资金流向数据（日线），参数: ?days=60',
                '/api/sina/money_flow/realtime/<code>': '获取实时资金流向分钟线数据，参数: ?klt=1&lmt=0',
                '/api/sina/fundamental/<code>': '获取基本面数据',
                '/api/sina/industry_comparison/<code>': '获取行业对比数据',
                '/api/sina/for_ai/<code>': '获取格式化的股票数据，用于AI分析',
                '/api/sina/for_ai_with_indicators/<code>': '获取格式化的股票数据（含技术指标），用于AI分析',
                '/api/sentiment/news/<code>': '获取股票相关新闻，参数: ?days=7',
                '/api/sentiment/posts/<code>': '获取股吧帖子（最新+热门），参数: ?latest=10&hot=10',
                '/api/sentiment/all/<code>': '获取完整舆情数据（新闻+帖子），参数: ?days=7&latest=10&hot=10',
                '/api/strategy/strong_stocks': '获取强势股（前两个交易日10:30前涨停，当前未涨停）',
                '/api/strategy/four_lights/scan': 'POST 全市场四灯共振扫描并保存信号',
                '/api/strategy/four_lights/history': 'GET 四灯信号历史及跨时段验证；DELETE 清空',
                '/api/strategy/overnight/scan': 'POST 尾盘隔夜超短扫描并保存信号',
                '/api/strategy/overnight/history': 'GET 隔夜信号历史及验证；DELETE 清空',
                '/api/watchlist': '自选股管理，GET获取列表，POST添加',
                '/api/watchlist/<code>': '自选股管理，DELETE删除',
                '/api/config': '配置管理，GET获取所有配置，POST设置配置',
                '/api/config/<key>': '配置管理，GET获取单个配置，POST设置配置',
                '/api/agents': 'Agent管理，GET获取列表，POST创建',
                '/api/agents/<id>': 'Agent管理，PUT更新，DELETE删除',
                '/api/ai/analyze/<code>': 'AI分析股票，POST请求，body: {"agent_id": 1}',
                '/api/ai/debate/start/<code>': '启动多Agent辩论任务，POST请求',
                '/api/ai/debate/start_multi': '启动多选一辩论任务，POST: codes, agent_ids, decision_agent_id, analysis_rounds, debate_rounds',
                '/api/portfolio/analyze': 'POST 一键分析账户、市场情绪和全部持仓',
                '/api/ai/debate/status/<job_id>': '查询多Agent辩论任务状态',
                '/api/ai/debate/jobs': '获取辩论任务列表，参数: ?status=active|completed|failed|canceled',
                '/api/ai/debate/stop/<job_id>': '终止辩论任务，POST请求',
                '/api/ai/debate/delete/<job_id>': '删除辩论任务，DELETE请求',
                '/api/health': '健康检查',
                '/api/pipeline/strategy_to_multi_debate': 'POST 强势股筛选→多选一辩论（需 X-Pipeline-Token）',
                '/api/feishu/events': 'POST 飞书事件订阅回调（指令触发流水线，需配置 FEISHU_VERIFICATION_TOKEN）',
            }
        })
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    @app.route('/api/health')
    def health():
        """健康检查"""
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'service': '新浪股票API服务'
        })

    @app.route('/api/sina/comprehensive/<code>')
    def get_sina_comprehensive(code):
        """获取股票的综合数据"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取综合数据，股票代码: {code_str}")
            data = get_comprehensive_data(code_str)
            result = to_json(data)
            
            response = jsonify(result)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取综合数据失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/comprehensive_with_indicators/<code>')
    def get_sina_comprehensive_with_indicators(code):
        """获取股票的综合数据（包含技术指标）"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取综合数据（含技术指标），股票代码: {code_str}")
            data = get_comprehensive_data_with_indicators(code_str)
            result = to_json(data)
            
            response = jsonify(result)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取综合数据失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/realtime/<code>')
    def get_sina_realtime(code):
        """获取实时行情数据"""
        try:
            code_str = str(code).strip()
            # 支持sh/sz格式的代码（如sh000001用于上证指数）
            if code_str.startswith(('sh', 'sz')):
                # 直接使用，不需要验证6位数字
                print(f"[API] 获取实时行情，股票代码: {code_str}")
                data = get_realtime_data(code_str)
            elif not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            else:
                print(f"[API] 获取实时行情，股票代码: {code_str}")
                data = get_realtime_data(code_str)
            
            if data is None:
                return jsonify({'error': '获取数据失败', 'message': '无法获取实时行情数据'}), 500
            
            response = jsonify(data)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取实时行情失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/timeline/<code>')
    def get_sina_timeline(code):
        """获取分时数据（每分钟的数据点）"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取分时数据，股票代码: {code_str}")
            df = get_timeline_data(code_str)
            
            if df is None or len(df) == 0:
                return jsonify({'code': code_str, 'data': [], 'count': 0})
            
            records = df.to_dict('records')
            for record in records:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif isinstance(value, pd.Timestamp):
                        record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            
            response = jsonify({'code': code_str, 'data': records, 'count': len(records)})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取分时数据失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/minute/<code>')
    def get_sina_minute(code):
        """获取分钟K线数据"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            scale = int(request.args.get('scale', 5))
            datalen = int(request.args.get('datalen', 240))
            
            if scale not in [5, 15, 30, 60]:
                return jsonify({'error': '参数错误', 'message': 'scale参数应为 5, 15, 30, 60 之一'}), 400
            
            print(f"[API] 获取分钟K线，股票代码: {code_str}, scale: {scale}, datalen: {datalen}")
            df = get_minute_kline(code_str, scale=scale, datalen=datalen)
            
            if df is None or len(df) == 0:
                return jsonify({'code': code_str, 'scale': scale, 'data': [], 'count': 0})
            
            records = df.to_dict('records')
            for record in records:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif isinstance(value, pd.Timestamp):
                        record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            
            response = jsonify({'code': code_str, 'scale': scale, 'data': records, 'count': len(records)})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取分钟K线失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/daily/<code>')
    def get_sina_daily(code):
        """获取日K线数据"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            count = int(request.args.get('count', 240))
            
            print(f"[API] 获取日K线，股票代码: {code_str}, count: {count}")
            df = get_daily_kline(code_str, count=count)
            
            if df is None or len(df) == 0:
                return jsonify({'code': code_str, 'data': [], 'count': 0})
            
            records = df.to_dict('records')
            for record in records:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif isinstance(value, pd.Timestamp):
                        record[key] = value.strftime('%Y-%m-%d')
            
            response = jsonify({'code': code_str, 'data': records, 'count': len(records)})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取日K线失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/money_flow/<code>')
    def get_sina_money_flow(code):
        """获取今日资金流向数据"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取资金流向，股票代码: {code_str}")
            data = get_money_flow(code_str)
            
            response = jsonify(data)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取资金流向失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/money_flow/history/<code>')
    def get_sina_money_flow_history(code):
        """获取历史资金流向数据（日线）"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            days = int(request.args.get('days', 60))  # 默认60天
            
            print(f"[API] 获取历史资金流向，股票代码: {code_str}, days: {days}")
            data = get_money_flow_history(code_str, days=days)
            
            response = jsonify({
                'code': code_str,
                'days': days,
                'count': len(data),
                'data': data
            })
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取历史资金流向失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/money_flow/realtime/<code>')
    def get_sina_money_flow_realtime(code):
        """获取实时资金流向分钟线数据"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            klt = int(request.args.get('klt', 1))  # 1=1分钟，5=5分钟
            lmt = int(request.args.get('lmt', 0))  # 0=获取所有数据
            
            print(f"[API] 获取实时资金流向分钟线，股票代码: {code_str}, klt: {klt}, lmt: {lmt}")
            data = get_money_flow_realtime_kline(code_str, klt=klt, lmt=lmt)
            
            response = jsonify({
                'code': code_str,
                'klt': klt,
                'count': len(data),
                'data': data
            })
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取实时资金流向分钟线失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/fundamental/<code>')
    def get_sina_fundamental(code):
        """获取股票的基本面数据"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取基本面数据，股票代码: {code_str}")
            data = get_fundamental_data(code_str)
            
            response = jsonify(data)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取基本面数据失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/industry_comparison/<code>')
    def get_sina_industry_comparison(code):
        """获取股票的行业对比数据"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取行业对比数据，股票代码: {code_str}")
            data = get_industry_comparison(code_str)
            
            response = jsonify(data)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取行业对比数据失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/for_ai/<code>')
    def get_sina_for_ai(code):
        """获取格式化的股票数据，用于AI分析"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取AI分析数据，股票代码: {code_str}")
            data = get_comprehensive_data(code_str)
            formatted = format_for_ai(data)
            
            raw_data = {
                'realtime': data['realtime'],
                'timeline_count': len(data['timeline']) if data['timeline'] is not None else 0,
                'minute_5_count': len(data['minute_5']) if data['minute_5'] is not None else 0,
                'minute_15_count': len(data['minute_15']) if data['minute_15'] is not None else 0,
                'minute_30_count': len(data['minute_30']) if data['minute_30'] is not None else 0,
                'daily_count': len(data['daily']) if data['daily'] is not None else 0,
                'sector_info': data.get('sector_info', []),
                'money_flow': data.get('money_flow', {}),
                'fundamental': data.get('fundamental', {}),
                'industry_comparison': data.get('industry_comparison', {}),
            }
            
            response = jsonify({'code': code_str, 'formatted_text': formatted, 'raw_data': raw_data})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取AI分析数据失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500

    @app.route('/api/sina/for_ai_with_indicators/<code>')
    def get_sina_for_ai_with_indicators(code):
        """获取格式化的股票数据（包含技术指标），用于AI分析"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'error': '股票代码格式错误', 'message': '股票代码应为6位数字，如 000001'}), 400
            
            print(f"[API] 获取AI分析数据（含技术指标），股票代码: {code_str}")
            data = get_comprehensive_data_with_indicators(code_str)
            formatted = format_for_ai(data)
            
            raw_data = {
                'realtime': data['realtime'],
                'timeline_count': len(data['timeline']) if data['timeline'] is not None else 0,
                'minute_5_count': len(data['minute_5']) if data['minute_5'] is not None else 0,
                'minute_15_count': len(data['minute_15']) if data['minute_15'] is not None else 0,
                'minute_30_count': len(data['minute_30']) if data['minute_30'] is not None else 0,
                'daily_count': len(data['daily']) if data['daily'] is not None else 0,
                'sector_info': data.get('sector_info', []),
                'money_flow': data.get('money_flow', {}),
                'fundamental': data.get('fundamental', {}),
                'industry_comparison': data.get('industry_comparison', {}),
            }
            
            # 添加技术指标摘要
            if data['daily'] is not None and len(data['daily']) > 0:
                latest = data['daily'].iloc[-1]
                indicators_summary = {}
                
                ma_cols = [col for col in data['daily'].columns if col.startswith('MA') and not col.startswith('MACD')]
                if ma_cols:
                    indicators_summary['MA'] = {col: float(latest[col]) for col in ma_cols if pd.notna(latest[col])}
                
                if 'MACD_DIF' in data['daily'].columns and pd.notna(latest['MACD_DIF']):
                    indicators_summary['MACD'] = {
                        'DIF': float(latest['MACD_DIF']),
                        'DEA': float(latest.get('MACD_DEA', 0)) if pd.notna(latest.get('MACD_DEA')) else 0,
                        'MACD': float(latest.get('MACD', 0)) if pd.notna(latest.get('MACD')) else 0
                    }
                
                if 'RSI14' in data['daily'].columns and pd.notna(latest['RSI14']):
                    indicators_summary['RSI'] = float(latest['RSI14'])
                
                if 'KDJ_K' in data['daily'].columns and pd.notna(latest['KDJ_K']):
                    indicators_summary['KDJ'] = {
                        'K': float(latest['KDJ_K']),
                        'D': float(latest.get('KDJ_D', 0)) if pd.notna(latest.get('KDJ_D')) else 0,
                        'J': float(latest.get('KDJ_J', 0)) if pd.notna(latest.get('KDJ_J')) else 0
                    }
                
                if 'BOLL_UPPER' in data['daily'].columns and pd.notna(latest['BOLL_UPPER']):
                    indicators_summary['BOLL'] = {
                        'upper': float(latest['BOLL_UPPER']),
                        'mid': float(latest.get('BOLL_MID', 0)) if pd.notna(latest.get('BOLL_MID')) else 0,
                        'lower': float(latest.get('BOLL_LOWER', 0)) if pd.notna(latest.get('BOLL_LOWER')) else 0
                    }
                
                raw_data['indicators'] = indicators_summary
            
            response = jsonify({'code': code_str, 'formatted_text': formatted, 'raw_data': raw_data})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取AI分析数据失败: {error_msg}")
            return jsonify({'error': '获取数据失败', 'message': error_msg}), 500
    
    # ==================== 舆情数据API ====================
    
    @app.route('/api/sentiment/news/<code>')
    def get_sentiment_news(code):
        """获取股票相关新闻"""
        try:
            code_str = str(code).strip()
            days = int(request.args.get('days', 7))
            
            news_list = get_news_from_stock(code_str, days=days)
            
            response = jsonify({
                'code': code_str,
                'days': days,
                'count': len(news_list),
                'news': news_list
            })
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取新闻失败: {error_msg}")
            return jsonify({'error': '获取新闻失败', 'message': error_msg}), 500
    
    @app.route('/api/sentiment/posts/<code>')
    def get_sentiment_posts(code):
        """获取股吧帖子（最新+热门）"""
        try:
            code_str = str(code).strip()
            latest_count = int(request.args.get('latest', 10))
            hot_count = int(request.args.get('hot', 10))
            
            posts_list = get_guba_posts(code_str, latest_count=latest_count, hot_count=hot_count)
            
            # 按类型分组
            latest_posts = [p for p in posts_list if p.get('sort_type') == 'latest']
            hot_posts = [p for p in posts_list if p.get('sort_type') == 'hot']
            
            response = jsonify({
                'code': code_str,
                'latest_count': len(latest_posts),
                'hot_count': len(hot_posts),
                'total_count': len(posts_list),
                'latest_posts': latest_posts,
                'hot_posts': hot_posts,
                'all_posts': posts_list
            })
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取股吧帖子失败: {error_msg}")
            return jsonify({'error': '获取股吧帖子失败', 'message': error_msg}), 500
    
    @app.route('/api/sentiment/all/<code>')
    def get_sentiment_all(code):
        """获取完整舆情数据（新闻+帖子）"""
        try:
            code_str = str(code).strip()
            days = int(request.args.get('days', 7))
            latest_count = int(request.args.get('latest', 10))
            hot_count = int(request.args.get('hot', 10))
            
            # 获取新闻
            news_list = get_news_from_stock(code_str, days=days)
            
            # 获取帖子
            posts_list = get_guba_posts(code_str, latest_count=latest_count, hot_count=hot_count)
            
            # 按类型分组
            latest_posts = [p for p in posts_list if p.get('sort_type') == 'latest']
            hot_posts = [p for p in posts_list if p.get('sort_type') == 'hot']
            
            response = jsonify({
                'code': code_str,
                'news': {
                    'count': len(news_list),
                    'days': days,
                    'list': news_list
                },
                'posts': {
                    'latest_count': len(latest_posts),
                    'hot_count': len(hot_posts),
                    'total_count': len(posts_list),
                    'latest_posts': latest_posts,
                    'hot_posts': hot_posts,
                    'all_posts': posts_list
                }
            })
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取舆情数据失败: {error_msg}")
            return jsonify({'error': '获取舆情数据失败', 'message': error_msg}), 500
    
    # ==================== 自选股API ====================
    
    @app.route('/api/watchlist', methods=['GET'])
    def get_watchlist_api():
        """获取自选股列表"""
        db = next(get_db())
        try:
            items = get_watchlist(db)
            return jsonify({
                'success': True,
                'data': [{'id': item.id, 'code': item.code, 'name': item.name, 'sort_order': item.sort_order} for item in items]
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/watchlist', methods=['POST'])
    def add_watchlist_api():
        """添加自选股"""
        db = next(get_db())
        try:
            data = request.json
            code = data.get('code', '').strip()
            if not code or len(code) != 6:
                return jsonify({'success': False, 'error': '股票代码格式错误'}), 400
            
            name = data.get('name', '')
            item = add_to_watchlist(db, code, name)
            return jsonify({
                'success': True,
                'data': {'id': item.id, 'code': item.code, 'name': item.name}
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/watchlist/<code>', methods=['DELETE'])
    def remove_watchlist_api(code):
        """移除自选股"""
        db = next(get_db())
        try:
            success = remove_from_watchlist(db, code)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/watchlist/order', methods=['POST'])
    def update_watchlist_order_api():
        """更新自选股排序"""
        db = next(get_db())
        try:
            data = request.json
            orders = data.get('orders', [])  # [{'code': '000001', 'sort_order': 0}, ...]
            update_watchlist_order(db, [(item['code'], item['sort_order']) for item in orders])
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    # ==================== 配置API ====================
    
    @app.route('/api/config', methods=['GET'])
    def get_config_api():
        """获取所有配置"""
        db = next(get_db())
        try:
            configs = get_all_configs(db)
            return jsonify({'success': True, 'data': configs})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/config/<key>', methods=['GET'])
    def get_config_key_api(key):
        """获取单个配置"""
        db = next(get_db())
        try:
            value = get_config(db, key)
            return jsonify({'success': True, 'data': {key: value}})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/config/<key>', methods=['POST'])
    def set_config_api(key):
        """设置配置"""
        db = next(get_db())
        try:
            data = request.json
            value = data.get('value', '')
            set_config(db, key, value)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    # ==================== Agent API ====================
    
    @app.route('/api/agents', methods=['GET'])
    def get_agents_api():
        """获取所有Agent"""
        db = next(get_db())
        try:
            enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
            agents = get_agents(db, enabled_only)
            return jsonify({
                'success': True,
                'data': [{
                    'id': a.id,
                    'name': a.name,
                    'type': a.type,
                    'prompt': a.prompt,
                    'enabled': a.enabled,
                    'ai_provider': a.ai_provider,
                    'model': a.model,
                    'sort_order': a.sort_order
                } for a in agents]
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/agents', methods=['POST'])
    def create_agent_api():
        """创建Agent"""
        db = next(get_db())
        try:
            data = request.json
            agent = create_agent(
                db,
                name=data.get('name'),
                type=data.get('type'),
                prompt=data.get('prompt'),
                ai_provider=data.get('ai_provider'),
                model=data.get('model'),
                enabled=data.get('enabled', True),
                sort_order=data.get('sort_order', 0)
            )
            return jsonify({'success': True, 'data': {'id': agent.id}})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/agents/<int:agent_id>', methods=['PUT'])
    def update_agent_api(agent_id):
        """更新Agent"""
        db = next(get_db())
        try:
            data = request.json
            agent = update_agent(db, agent_id, **data)
            return jsonify({'success': agent is not None, 'data': {'id': agent.id} if agent else None})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/agents/<int:agent_id>', methods=['DELETE'])
    def delete_agent_api(agent_id):
        """删除Agent"""
        db = next(get_db())
        try:
            success = delete_agent(db, agent_id)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    # ==================== AI服务工具API ====================
    
    @app.route('/api/ai/models', methods=['GET'])
    def get_ai_models():
        """获取指定AI提供商的可用模型列表"""
        try:
            provider = request.args.get('provider')
            api_key = request.args.get('api_key')
            
            if not provider:
                return jsonify({'success': False, 'error': '缺少provider参数'}), 400
            
            if not api_key:
                # 尝试从数据库获取
                db = next(get_db())
                try:
                    api_key_key = f'{provider}_api_key'
                    api_key = get_config(db, api_key_key)
                finally:
                    db.close()
            
            if not api_key:
                return jsonify({'success': False, 'error': '未配置API Key'}), 400
            
            models = AIService.get_models(provider, api_key)
            return jsonify({
                'success': True,
                'data': models
            })
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取模型列表失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
    
    @app.route('/api/ai/test', methods=['POST'])
    def test_ai_connection():
        """测试AI服务连接"""
        try:
            data = request.json
            provider = data.get('provider')
            api_key = data.get('api_key')
            model = data.get('model')
            
            if not provider or not api_key:
                return jsonify({'success': False, 'error': '缺少provider或api_key参数'}), 400
            
            result = AIService.test_connection(provider, api_key, model)
            return jsonify(result)
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 测试连接失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500

    def _serialize_job(job):
        agent_info = {}
        try:
            agent_info = json.loads(job.agent_ids) if job.agent_ids else {}
        except Exception:
            agent_info = {}
        steps = []
        try:
            steps = json.loads(job.steps) if job.steps else []
        except Exception:
            steps = []
        return {
            'job_id': job.job_id,
            'code': job.code,
            'name': job.name,
            'agent_ids': agent_info.get('agent_ids', []),
            'analysis_rounds': agent_info.get('analysis_rounds', 3),
            'debate_rounds': agent_info.get('debate_rounds', 3),
            'meta': agent_info.get('meta', {}),
            'status': job.status,
            'progress': job.progress,
            'steps': steps,
            'report_md': job.report_md or '',
            'error': job.error,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'updated_at': job.updated_at.isoformat() if job.updated_at else None,
        }

    def _update_debate_job(db: SessionLocal, job_id, **kwargs):
        if 'steps' in kwargs and isinstance(kwargs['steps'], list):
            kwargs['steps'] = json.dumps(kwargs['steps'], ensure_ascii=False)
        update_debate_job(db, job_id, **kwargs)

    def _is_job_canceled(db, job_id):
        job = get_debate_job(db, job_id)
        return True if (job and job.canceled) else False

    def _run_debate_job(job_id, code_str, agent_ids, analysis_rounds, debate_rounds, override_api_key=None):
        db = SessionLocal()
        try:
            _update_debate_job(db, job_id, status='running', progress=5)

            agents = []
            for agent_id in agent_ids:
                agent = get_agent(db, agent_id)
                if not agent or not agent.enabled:
                    raise ValueError(f'Agent不存在或未启用: {agent_id}')
                agents.append(agent)

            # 获取股票数据
            print(f"[API] 获取股票数据（辩论）: {code_str}")
            stock_data = get_comprehensive_data_with_indicators(code_str)
            formatted_data = format_for_ai(stock_data)
            portfolio_context = build_ai_portfolio_context(db, code_str)

            # 获取舆情数据（新闻+帖子）
            try:
                news_list = get_news_from_stock(code_str, days=7)[:5]
                posts_list = get_guba_posts(code_str, latest_count=5, hot_count=5)
                sentiment_text = "News:\n" + "\n".join([f"- {n.get('title','')}" for n in news_list]) + "\n\nPosts:\n" + "\n".join([f"- {p.get('title','')}" for p in posts_list[:10]])
            except Exception as e:
                sentiment_text = f"Sentiment data unavailable: {str(e)}"

            default_model_map = {
                'openai': 'gpt-3.5-turbo',
                'deepseek': 'deepseek-chat',
                'qwen': 'qwen-turbo',
                'gemini': 'gemini-pro',
                'siliconflow': 'Qwen/Qwen2.5-7B-Instruct',
                'grok': 'grok-4-0709'
            }

            def resolve_agent_config(agent):
                provider = agent.ai_provider or get_config(db, 'default_ai_provider', 'openai')
                # 移动端可以通过override_api_key传入专属Key，优先使用；否则退回到服务器配置
                api_key = override_api_key or get_config(db, f'{provider}_api_key')
                if not api_key:
                    raise ValueError(f'未配置{provider} API Key')
                model = agent.model or get_config(db, f'{provider}_model', default_model_map.get(provider, 'gpt-3.5-turbo'))
                return provider, api_key, model

            steps = []
            analysis_memory = {agent.id: [] for agent in agents}

            # 多轮分析（同一轮并行）
            for round_idx in range(1, analysis_rounds + 1):
                if _is_job_canceled(db, job_id):
                    _update_debate_job(db, job_id, status='canceled')
                    return
                # 获取当前时间（每轮分析都更新）
                current_time = datetime.now()
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                current_time_info = f"Current Time: {current_time_str} (Weekday: {current_time.strftime('%A')})"
                
                prompts = []
                for agent in agents:
                    prev_analysis = "\n\n".join(analysis_memory[agent.id][-2:]) if analysis_memory[agent.id] else "None"
                    prompts.append((
                        agent,
                        f"{agent.prompt}\n\n"
                        f"{current_time_info}\n\n"
                        f"Stock Data:\n{formatted_data}\n\n"
                        f"{portfolio_context}\n\n"
                        f"Sentiment Data:\n{sentiment_text}\n\n"
                        f"Round {round_idx} Analysis:\n"
                        f"Build on your previous analysis and provide new insights without repetition.\n\n"
                        f"Previous Analysis (if any):\n{prev_analysis}\n\n"
                        f"Please provide your analysis in Chinese."
                    ))

                with ThreadPoolExecutor(max_workers=min(6, len(prompts))) as executor:
                    futures = {
                        executor.submit(
                            AIService.call_agent,
                            *resolve_agent_config(agent),
                            prompt
                        ): agent
                        for agent, prompt in prompts
                    }
                    for future in as_completed(futures):
                        agent = futures[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            result = f"[ERROR] {agent.name} analysis failed: {str(e)}"
                        analysis_memory[agent.id].append(result)
                        steps.append({
                            'phase': 'analysis',
                            'round': round_idx,
                            'agent_id': agent.id,
                            'agent_name': agent.name,
                            'content': result,
                            'timestamp': datetime.now().isoformat()
                        })
                        progress = 20 + round_idx * 10
                        _update_debate_job(db, job_id, steps=steps, progress=progress)

            # 多轮辩论（同一轮并行）
            debate_history = []
            for round_idx in range(1, debate_rounds + 1):
                if _is_job_canceled(db, job_id):
                    _update_debate_job(db, job_id, status='canceled')
                    return
                # 获取当前时间（每轮辩论都更新）
                current_time = datetime.now()
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                current_time_info = f"Current Time: {current_time_str} (Weekday: {current_time.strftime('%A')})"
                
                prompts = []
                other_latest = "\n\n".join([
                    f"{a.name}:\n{analysis_memory[a.id][-1]}"
                    for a in agents if analysis_memory[a.id]
                ])
                recent_debate = "\n\n".join([
                    f"Round {item['round']} - {item['agent_name']}:\n{item['content']}"
                    for item in debate_history[-min(len(debate_history), len(agents) * 2):]
                ]) if debate_history else "None"

                for agent in agents:
                    prompts.append((
                        agent,
                        f"{agent.prompt}\n\n"
                        f"{current_time_info}\n\n"
                        "You are participating in a multi-agent debate.\n\n"
                        f"Current Stock Data:\n{formatted_data}\n\n"
                        f"{portfolio_context}\n\n"
                        f"Sentiment Data:\n{sentiment_text}\n\n"
                        f"Debate Round {round_idx}:\n"
                        "Respond with counterarguments, supporting evidence, and actionable insights.\n"
                        "Focus on your unique perspective and address opposing viewpoints.\n\n"
                        f"Other agents' latest analyses:\n{other_latest}\n\n"
                        f"Recent Debate History:\n{recent_debate}\n\n"
                        "Please provide your debate response in Chinese."
                    ))

                with ThreadPoolExecutor(max_workers=min(6, len(prompts))) as executor:
                    futures = {
                        executor.submit(
                            AIService.call_agent,
                            *resolve_agent_config(agent),
                            prompt
                        ): agent
                        for agent, prompt in prompts
                    }
                    for future in as_completed(futures):
                        agent = futures[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            result = f"[ERROR] {agent.name} debate failed: {str(e)}"
                        item = {
                            'phase': 'debate',
                            'round': round_idx,
                            'agent_id': agent.id,
                            'agent_name': agent.name,
                            'content': result,
                            'timestamp': datetime.now().isoformat()
                        }
                        debate_history.append(item)
                        steps.append(item)
                        progress = 60 + round_idx * 10
                        _update_debate_job(db, job_id, steps=steps, progress=progress)

            # 资深操作员记录与最终报告
            operator_provider = get_config(db, 'default_ai_provider', 'openai')
            operator_api_key = override_api_key or get_config(db, f'{operator_provider}_api_key')
            if not operator_api_key:
                raise ValueError(f'未配置{operator_provider} API Key')
            operator_model = get_config(db, f'{operator_provider}_model', default_model_map.get(operator_provider, 'gpt-3.5-turbo'))

            transcript = "\n\n".join([
                f"[{item['phase']} R{item['round']}] {item['agent_name']}:\n{item['content']}"
                for item in steps
            ])

            operator_prompt = (
                "You are a senior trading operator and debate recorder.\n"
                "Based on the multi-agent analysis and debate transcript, produce a final research report in Markdown.\n"
                "The report must include sections: Basic Info, Overview, Key Points by Agent, Debate Summary, Risks, Final Recommendation.\n"
                "Use tables and bullet points where appropriate for readability.\n"
                "Provide a clear trading operation suggestion in the Final Recommendation section, including "
                "position percentage and amount, entry range, stop loss, take profit, validity period and invalidation conditions. "
                "NO TRADE is valid when evidence or portfolio capacity is inadequate.\n\n"
                f"Stock Data (key fields):\n{formatted_data}\n\n"
                f"{portfolio_context}\n\n"
                f"Sentiment Summary:\n{sentiment_text}\n\n"
                f"Transcript:\n{transcript}\n\n"
                "Please output the report in Chinese."
            )

            try:
                report_md = AIService.call_agent(operator_provider, operator_api_key, operator_model, operator_prompt)
                _update_debate_job(db, job_id, status='completed', progress=100, report_md=report_md, steps=steps, error=None)
            except Exception as e:
                fallback_report = (
                    "## 报告生成失败（已提供原始记录）\n\n"
                    f"- Error: {str(e)}\n\n"
                    "### 原始辩论记录（节选）\n\n"
                    f"{transcript[:8000]}\n\n"
                    "请稍后重试生成报告。"
                )
                _update_debate_job(db, job_id, status='completed', progress=100, report_md=fallback_report, steps=steps, error=None)
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 辩论分析失败: {error_msg}")
            _update_debate_job(db, job_id, status='failed', error=error_msg)
        finally:
            db.close()

    def _run_multi_select_job(
        job_id,
        codes,
        agent_ids,
        analysis_rounds,
        debate_rounds,
        override_api_key=None,
        candidate_context='',
    ):
        db = SessionLocal()
        try:
            _update_debate_job(db, job_id, status='running', progress=5)

            agents = []
            for agent_id in agent_ids:
                agent = get_agent(db, agent_id)
                if not agent or not agent.enabled:
                    raise ValueError(f'Agent不存在或未启用: {agent_id}')
                agents.append(agent)

            default_model_map = {
                'openai': 'gpt-3.5-turbo',
                'deepseek': 'deepseek-chat',
                'qwen': 'qwen-turbo',
                'gemini': 'gemini-pro',
                'siliconflow': 'Qwen/Qwen2.5-7B-Instruct',
                'grok': 'grok-4-0709'
            }

            # 固定裁判，不使用数据库Agent。若提供override_api_key则优先使用。
            operator_provider = get_config(db, 'default_ai_provider', 'openai')
            operator_api_key = override_api_key or get_config(db, f'{operator_provider}_api_key')
            if not operator_api_key:
                raise ValueError(f'未配置{operator_provider} API Key')
            operator_model = get_config(db, f'{operator_provider}_model', default_model_map.get(operator_provider, 'gpt-3.5-turbo'))

            # 获取多股票数据
            stock_blocks = []
            for code_str in codes:
                try:
                    stock_data = get_comprehensive_data_with_indicators(code_str)
                    formatted = format_for_ai(stock_data)
                    stock_name = ''
                    try:
                        stock_name = stock_data.get('realtime', {}).get('name', '')
                    except Exception:
                        stock_name = ''
                    stock_blocks.append(f"Stock {code_str} {stock_name}:\n{formatted}")
                except Exception as e:
                    stock_blocks.append(f"Stock {code_str}:\nData unavailable: {str(e)}")

            combined_data = "\n\n".join(stock_blocks)
            portfolio_context = build_ai_portfolio_context(db)
            multi_instruction = (
                "Choose one primary candidate and at most one backup candidate. "
                "If no candidate has a favorable risk/reward ratio, explicitly choose NO TRADE. "
                "Provide your preference and reasoning from your unique perspective."
            )
            score_context = (
                f"Pre-screening quantitative score summary:\n{candidate_context}\n\n"
                if candidate_context
                else ''
            )

            def resolve_agent_config(agent):
                provider = agent.ai_provider or get_config(db, 'default_ai_provider', 'openai')
                api_key = override_api_key or get_config(db, f'{provider}_api_key')
                if not api_key:
                    raise ValueError(f'未配置{provider} API Key')
                model = agent.model or get_config(db, f'{provider}_model', default_model_map.get(provider, 'gpt-3.5-turbo'))
                return provider, api_key, model

            steps = []
            analysis_memory = {agent.id: [] for agent in agents}

            # 多轮分析
            for round_idx in range(1, analysis_rounds + 1):
                if _is_job_canceled(db, job_id):
                    _update_debate_job(db, job_id, status='canceled')
                    return
                # 获取当前时间（每轮分析都更新）
                current_time = datetime.now()
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                current_time_info = f"Current Time: {current_time_str} (Weekday: {current_time.strftime('%A')})"
                
                prompts = []
                for agent in agents:
                    prev_analysis = "\n\n".join(analysis_memory[agent.id][-2:]) if analysis_memory[agent.id] else "None"
                    prompts.append((
                        agent,
                        f"{agent.prompt}\n\n"
                        f"{current_time_info}\n\n"
                        "Multi-Stock Selection Task:\n"
                        f"{score_context}"
                        f"{combined_data}\n\n"
                        f"{portfolio_context}\n\n"
                        f"{multi_instruction}\n\n"
                        f"Round {round_idx} Analysis:\n"
                        "Provide new insights and clearly state your preferred stock.\n\n"
                        f"Previous Analysis (if any):\n{prev_analysis}\n\n"
                        "Please provide your analysis in Chinese."
                    ))

                with ThreadPoolExecutor(max_workers=min(6, len(prompts))) as executor:
                    futures = {
                        executor.submit(
                            AIService.call_agent,
                            *resolve_agent_config(agent),
                            prompt
                        ): agent
                        for agent, prompt in prompts
                    }
                    for future in as_completed(futures):
                        agent = futures[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            result = f"[ERROR] {agent.name} analysis failed: {str(e)}"
                        analysis_memory[agent.id].append(result)
                        steps.append({
                            'phase': 'analysis',
                            'round': round_idx,
                            'agent_id': agent.id,
                            'agent_name': agent.name,
                            'content': result,
                            'timestamp': datetime.now().isoformat()
                        })
                        progress = 20 + round_idx * 10
                        _update_debate_job(db, job_id, steps=steps, progress=progress)

            # 多轮辩论
            debate_history = []
            for round_idx in range(1, debate_rounds + 1):
                if _is_job_canceled(db, job_id):
                    _update_debate_job(db, job_id, status='canceled')
                    return
                # 获取当前时间（每轮辩论都更新）
                current_time = datetime.now()
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                current_time_info = f"Current Time: {current_time_str} (Weekday: {current_time.strftime('%A')})"
                
                prompts = []
                other_latest = "\n\n".join([
                    f"{a.name}:\n{analysis_memory[a.id][-1]}"
                    for a in agents if analysis_memory[a.id]
                ])
                recent_debate = "\n\n".join([
                    f"Round {item['round']} - {item['agent_name']}:\n{item['content']}"
                    for item in debate_history[-min(len(debate_history), len(agents) * 2):]
                ]) if debate_history else "None"

                for agent in agents:
                    prompts.append((
                        agent,
                        f"{agent.prompt}\n\n"
                        f"{current_time_info}\n\n"
                        "You are participating in a multi-agent debate for a multi-stock selection task.\n"
                        f"{multi_instruction}\n\n"
                        f"{score_context}"
                        f"Current candidate data:\n{combined_data}\n\n"
                        f"{portfolio_context}\n\n"
                        f"Debate Round {round_idx}:\n"
                        "Respond with counterarguments and emphasize your preferred stock.\n\n"
                        f"Other agents' latest analyses:\n{other_latest}\n\n"
                        f"Recent Debate History:\n{recent_debate}\n\n"
                        "Please provide your debate response in Chinese."
                    ))

                with ThreadPoolExecutor(max_workers=min(6, len(prompts))) as executor:
                    futures = {
                        executor.submit(
                            AIService.call_agent,
                            *resolve_agent_config(agent),
                            prompt
                        ): agent
                        for agent, prompt in prompts
                    }
                    for future in as_completed(futures):
                        agent = futures[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            result = f"[ERROR] {agent.name} debate failed: {str(e)}"
                        item = {
                            'phase': 'debate',
                            'round': round_idx,
                            'agent_id': agent.id,
                            'agent_name': agent.name,
                            'content': result,
                            'timestamp': datetime.now().isoformat()
                        }
                        debate_history.append(item)
                        steps.append(item)
                        progress = 60 + round_idx * 10
                        _update_debate_job(db, job_id, steps=steps, progress=progress)

            # 决策员最终结论
            transcript = "\n\n".join([
                f"[{item['phase']} R{item['round']}] {item['agent_name']}:\n{item['content']}"
                for item in steps
            ])

            decision_prompt = (
                "You are a disciplined senior trader and final portfolio decision maker.\n"
                "Choose ONE primary candidate and at most ONE backup candidate. "
                "You MUST choose NO TRADE when the setup or portfolio capacity is inadequate.\n"
                "Be decisive and action-oriented, but never invent missing evidence.\n\n"
                f"{score_context}"
                f"Candidates:\n{combined_data}\n\n"
                f"{portfolio_context}\n\n"
                f"Debate Transcript:\n{transcript}\n\n"
                "Output a Markdown report with sections: Market Decision, Primary Candidate, "
                "Backup Candidate, Portfolio Allocation, Entry Plan, Risk Control. "
                "For each actionable candidate include entry range, position percentage and amount, "
                "stop loss, take profit, validity period and invalidation conditions.\n"
                "Please output in Chinese."
            )

            try:
                report_md = AIService.call_agent(operator_provider, operator_api_key, operator_model, decision_prompt)
                steps.append({
                    'phase': 'debate',
                    'round': debate_rounds + 1,
                    'agent_id': 0,
                    'agent_name': "裁判（决策）",
                    'content': report_md,
                    'timestamp': datetime.now().isoformat()
                })
                _update_debate_job(db, job_id, status='completed', progress=100, report_md=report_md, steps=steps, error=None)
            except Exception as e:
                fallback_report = (
                    "## 决策生成失败（已提供原始记录）\n\n"
                    f"- Error: {str(e)}\n\n"
                    "### 原始辩论记录（节选）\n\n"
                    f"{transcript[:8000]}\n\n"
                    "请稍后重试生成决策报告。"
                )
                _update_debate_job(db, job_id, status='completed', progress=100, report_md=fallback_report, steps=steps, error=None)

        except Exception as e:
            error_msg = str(e)
            print(f"[API] 多选一辩论失败: {error_msg}")
            _update_debate_job(db, job_id, status='failed', error=error_msg)
        finally:
            db.close()

    def _run_portfolio_analysis_job(job_id, agent_ids, override_api_key=None):
        db = SessionLocal()
        try:
            _update_debate_job(db, job_id, status='running', progress=5)
            agents = []
            for agent_id in agent_ids:
                agent = get_agent(db, agent_id)
                if not agent or not agent.enabled:
                    raise ValueError(f'Agent不存在或未启用: {agent_id}')
                agents.append(agent)

            positions = db.query(Position).order_by(Position.updated_at.desc()).all()
            if not positions:
                raise ValueError('当前没有持仓，无法执行组合分析')

            portfolio_context = build_ai_portfolio_context(db)
            market_context = build_market_sentiment_context()
            stock_blocks = []
            for position in positions:
                try:
                    # 组合分析只取可靠且快速的价量、日K指标和当日资金，
                    # 避免单只股票基本面/行业接口超时拖慢整个账户分析。
                    daily = get_daily_kline(position.code, count=120)
                    if daily is not None and len(daily) > 0:
                        daily = calculate_indicators(daily)
                    stock_data = {
                        'code': position.code,
                        'realtime': get_realtime_data(position.code),
                        'daily': daily,
                        'money_flow': get_money_flow(position.code),
                    }
                    stock_blocks.append(
                        f"持仓 {position.name or position.code}({position.code}):\n"
                        f"{format_for_ai(stock_data)}"
                    )
                except Exception as exc:
                    stock_blocks.append(
                        f"持仓 {position.name or position.code}({position.code}): "
                        f"走势数据获取失败 {str(exc)}"
                    )
            holding_market_data = '\n\n'.join(stock_blocks)

            default_model_map = {
                'openai': 'gpt-3.5-turbo',
                'deepseek': 'deepseek-chat',
                'qwen': 'qwen-turbo',
                'gemini': 'gemini-pro',
                'siliconflow': 'Qwen/Qwen2.5-7B-Instruct',
                'grok': 'grok-4-0709',
            }

            def resolve_agent_config(agent):
                provider = agent.ai_provider or get_config(db, 'default_ai_provider', 'openai')
                api_key = override_api_key or get_config(db, f'{provider}_api_key')
                if not api_key:
                    raise ValueError(f'未配置{provider} API Key')
                model = agent.model or get_config(
                    db,
                    f'{provider}_model',
                    default_model_map.get(provider, 'gpt-3.5-turbo'),
                )
                return provider, api_key, model

            common_instruction = (
                "This is a portfolio-level decision, not an isolated stock recommendation. "
                "Evaluate market regime, account cash and total exposure, concentration, every holding's trend, "
                "profit/loss and available quantity. Give prioritized account actions for today. "
                "Do not force a trade and do not suggest selling more than available quantity."
            )
            prompts = [
                (
                    agent,
                    f"{agent.prompt}\n\n{common_instruction}\n\n"
                    f"{market_context}\n\n{portfolio_context}\n\n"
                    f"All Holding Market Data:\n{holding_market_data}\n\n"
                    "Output your portfolio-level analysis in Chinese. For every holding state a clear action, "
                    "position change and trigger condition.",
                )
                for agent in agents
            ]

            steps = []
            with ThreadPoolExecutor(max_workers=min(6, len(prompts))) as executor:
                futures = {
                    executor.submit(AIService.call_agent, *resolve_agent_config(agent), prompt): agent
                    for agent, prompt in prompts
                }
                for future in as_completed(futures):
                    agent = futures[future]
                    try:
                        content = future.result()
                    except Exception as exc:
                        content = f'[ERROR] {agent.name} analysis failed: {str(exc)}'
                    steps.append({
                        'phase': 'analysis',
                        'round': 1,
                        'agent_id': agent.id,
                        'agent_name': agent.name,
                        'content': content,
                        'timestamp': datetime.now().isoformat(),
                    })
                    _update_debate_job(
                        db,
                        job_id,
                        steps=steps,
                        progress=20 + int(len(steps) / len(agents) * 55),
                    )

            transcript = '\n\n'.join(
                f"{step['agent_name']}:\n{step['content']}" for step in steps
            )
            operator_provider = get_config(db, 'default_ai_provider', 'openai')
            operator_api_key = override_api_key or get_config(db, f'{operator_provider}_api_key')
            if not operator_api_key:
                raise ValueError(f'未配置{operator_provider} API Key')
            operator_model = get_config(
                db,
                f'{operator_provider}_model',
                default_model_map.get(operator_provider, 'gpt-3.5-turbo'),
            )
            final_prompt = (
                "You are the chief portfolio manager. Produce one decisive Chinese Markdown account action plan.\n"
                "Reconcile the agent opinions with actual account constraints and current market sentiment.\n"
                "Required sections: 市场环境、账户体检、持仓逐只操作表、操作优先级、现金与仓位安排、"
                "做T计划、风险与失效条件。\n"
                "The holding table must include current position percentage, action, quantity or percentage change, "
                "price trigger, stop loss, take profit and validity period. NO TRADE is allowed.\n\n"
                f"{market_context}\n\n{portfolio_context}\n\n"
                f"All Holding Market Data:\n{holding_market_data}\n\n"
                f"Agent Opinions:\n{transcript}"
            )
            report_md = AIService.call_agent(
                operator_provider,
                operator_api_key,
                operator_model,
                final_prompt,
            )
            steps.append({
                'phase': 'debate',
                'round': 1,
                'agent_id': 0,
                'agent_name': '组合经理（最终决策）',
                'content': report_md,
                'timestamp': datetime.now().isoformat(),
            })
            _update_debate_job(
                db,
                job_id,
                status='completed',
                progress=100,
                report_md=report_md,
                steps=steps,
                error=None,
            )
        except Exception as exc:
            print(f'[API] 组合分析失败: {exc}')
            _update_debate_job(db, job_id, status='failed', error=str(exc))
        finally:
            db.close()

    @app.route('/api/portfolio/analyze', methods=['POST'])
    def start_portfolio_analysis_api():
        """启动账户、市场情绪和全部持仓的一键组合分析。"""
        try:
            body = request.get_json(silent=True) or {}
            agent_ids = body.get('agent_ids') or []
            override_api_key = body.get('override_api_key')
            if not isinstance(agent_ids, list) or len(agent_ids) < 2:
                return jsonify({'success': False, 'error': '至少选择2个Agent'}), 400

            db = SessionLocal()
            try:
                positions = db.query(Position).all()
                if not positions:
                    return jsonify({'success': False, 'error': '当前没有持仓'}), 400
                job_id = str(uuid.uuid4())
                job_name = f"账户持仓整体分析 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                codes = [position.code for position in positions]
                create_debate_job(
                    db,
                    job_id,
                    ','.join(codes),
                    job_name,
                    agent_ids,
                    1,
                    1,
                    meta={'mode': 'portfolio', 'codes': codes},
                )
            finally:
                db.close()

            threading.Thread(
                target=_run_portfolio_analysis_job,
                args=(job_id, agent_ids, override_api_key),
                daemon=True,
            ).start()
            return jsonify({'success': True, 'data': {'job_id': job_id, 'name': job_name}})
        except Exception as exc:
            return jsonify({'success': False, 'error': str(exc)}), 500

    @app.route('/api/ai/debate/start/<code>', methods=['POST'])
    def start_debate_job_api(code):
        """启动多Agent辩论任务（后台执行）"""
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'success': False, 'error': '股票代码格式错误'}), 400

            data = request.json or {}
            agent_ids = data.get('agent_ids', [])
            analysis_rounds = int(data.get('analysis_rounds', 3))
            debate_rounds = int(data.get('debate_rounds', 3))
            override_api_key = data.get('override_api_key')  # 可选：来自移动端的用户Key

            if not isinstance(agent_ids, list) or len(agent_ids) < 2:
                return jsonify({'success': False, 'error': '至少需要选择2个Agent参与辩论'}), 400

            job_id = str(uuid.uuid4())
            # 生成任务名称：股票名 + 日期
            try:
                realtime = get_realtime_data(code_str)
                stock_name = realtime.get('name') if isinstance(realtime, dict) else None
            except Exception:
                stock_name = None
            job_name = f"{stock_name or code_str} {datetime.now().strftime('%Y-%m-%d')}"

            db = next(get_db())
            try:
                create_debate_job(db, job_id, code_str, job_name, agent_ids, analysis_rounds, debate_rounds)
            finally:
                db.close()

            thread = threading.Thread(
                target=_run_debate_job,
                args=(job_id, code_str, agent_ids, analysis_rounds, debate_rounds, override_api_key),
                daemon=True
            )
            thread.start()

            return jsonify({'success': True, 'data': {'job_id': job_id, 'name': job_name}})
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 启动辩论任务失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500

    @app.route('/api/ai/debate/start_multi', methods=['POST'])
    def start_multi_debate_job_api():
        """启动多选一辩论任务（后台执行）"""
        try:
            data = request.json or {}
            codes = data.get('codes', [])
            agent_ids = data.get('agent_ids', [])
            analysis_rounds = int(data.get('analysis_rounds', 2))
            debate_rounds = int(data.get('debate_rounds', 1))
            override_api_key = data.get('override_api_key')
            candidate_context = str(data.get('candidate_context') or '')[:12000]

            if not isinstance(codes, list) or len(codes) < 2:
                return jsonify({'success': False, 'error': '至少需要选择2只股票'}), 400
            if not isinstance(agent_ids, list) or len(agent_ids) < 2:
                return jsonify({'success': False, 'error': '至少需要选择2个Agent参与辩论'}), 400
            codes = [str(c).strip() for c in codes if str(c).strip()]
            if not all(code.isdigit() and len(code) == 6 for code in codes):
                return jsonify({'success': False, 'error': '股票代码格式错误'}), 400

            job_id = str(uuid.uuid4())
            job_name = f"多选一: {'/'.join(codes)} {datetime.now().strftime('%Y-%m-%d')}"
            job_code = ",".join(codes)

            db = next(get_db())
            try:
                create_debate_job(
                    db, job_id, job_code, job_name, agent_ids, analysis_rounds, debate_rounds,
                    meta={'mode': 'multi_select', 'codes': codes}
                )
            finally:
                db.close()

            thread = threading.Thread(
                target=_run_multi_select_job,
                args=(
                    job_id,
                    codes,
                    agent_ids,
                    analysis_rounds,
                    debate_rounds,
                    override_api_key,
                    candidate_context,
                ),
                daemon=True
            )
            thread.start()

            return jsonify({'success': True, 'data': {'job_id': job_id, 'name': job_name}})
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 启动多选一辩论任务失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500

    @app.route('/api/ai/debate/status/<job_id>', methods=['GET'])
    def get_debate_job_status(job_id):
        """查询辩论任务状态"""
        db = next(get_db())
        try:
            job = get_debate_job(db, job_id)
        finally:
            db.close()
        if not job:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        return jsonify({'success': True, 'data': _serialize_job(job)})

    @app.route('/api/ai/debate/jobs', methods=['GET'])
    def list_debate_jobs_api():
        """获取辩论任务列表"""
        try:
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            db = next(get_db())
            try:
                jobs = list_debate_jobs(db, status=status, limit=limit)
                data = [_serialize_job(job) for job in jobs]
            finally:
                db.close()
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 获取辩论任务列表失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500

    @app.route('/api/ai/debate/stop/<job_id>', methods=['POST'])
    def stop_debate_job_api(job_id):
        """终止辩论任务"""
        db = next(get_db())
        try:
            job = get_debate_job(db, job_id)
            if not job:
                return jsonify({'success': False, 'error': '任务不存在'}), 404
            if job.status in ['completed', 'failed', 'canceled']:
                return jsonify({'success': False, 'error': '任务已结束，无法终止'}), 400
            cancel_debate_job(db, job_id)
            return jsonify({'success': True})
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 终止辩论任务失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        finally:
            db.close()

    @app.route('/api/ai/debate/delete/<job_id>', methods=['DELETE'])
    def delete_debate_job_api(job_id):
        """删除辩论任务"""
        db = next(get_db())
        try:
            job = get_debate_job(db, job_id)
            if not job:
                return jsonify({'success': False, 'error': '任务不存在'}), 404
            if job.status in ['queued', 'running']:
                return jsonify({'success': False, 'error': '任务进行中，无法删除，请先终止'}), 400
            success = delete_debate_job(db, job_id)
            return jsonify({'success': success})
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 删除辩论任务失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        finally:
            db.close()
    
    @app.route('/api/ai/debate/<code>', methods=['POST'])
    def debate_stock_api(code):
        """多Agent分析+辩论（含记录与最终报告）"""
        db = next(get_db())
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'success': False, 'error': '股票代码格式错误'}), 400

            data = request.json or {}
            agent_ids = data.get('agent_ids', [])
            analysis_rounds = int(data.get('analysis_rounds', 3))
            debate_rounds = int(data.get('debate_rounds', 3))

            if not isinstance(agent_ids, list) or len(agent_ids) < 2:
                return jsonify({'success': False, 'error': '至少需要选择2个Agent参与辩论'}), 400

            # 获取Agent配置
            agents = []
            for agent_id in agent_ids:
                agent = get_agent(db, agent_id)
                if not agent or not agent.enabled:
                    return jsonify({'success': False, 'error': f'Agent不存在或未启用: {agent_id}'}), 400
                agents.append(agent)

            # 获取股票数据
            print(f"[API] 获取股票数据（辩论）: {code_str}")
            stock_data = get_comprehensive_data_with_indicators(code_str)
            formatted_data = format_for_ai(stock_data)
            portfolio_context = build_ai_portfolio_context(db, code_str)

            default_model_map = {
                'openai': 'gpt-3.5-turbo',
                'deepseek': 'deepseek-chat',
                'qwen': 'qwen-turbo',
                'gemini': 'gemini-pro',
                'siliconflow': 'Qwen/Qwen2.5-7B-Instruct',
                'grok': 'grok-4-0709'
            }

            def resolve_agent_config(agent):
                provider = agent.ai_provider or get_config(db, 'default_ai_provider', 'openai')
                api_key = get_config(db, f'{provider}_api_key')
                if not api_key:
                    raise ValueError(f'未配置{provider} API Key')
                model = agent.model or get_config(db, f'{provider}_model', default_model_map.get(provider, 'gpt-3.5-turbo'))
                return provider, api_key, model

            steps = []
            analysis_memory = {agent.id: [] for agent in agents}

            # 获取当前时间
            current_time = datetime.now()
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            current_time_info = f"Current Time: {current_time_str} (Weekday: {current_time.strftime('%A')})"
            
            # 3轮分析
            for round_idx in range(1, analysis_rounds + 1):
                for agent in agents:
                    provider, api_key, model = resolve_agent_config(agent)
                    prev_analysis = "\n\n".join(analysis_memory[agent.id][-2:]) if analysis_memory[agent.id] else "None"
                    prompt = (
                        f"{agent.prompt}\n\n"
                        f"{current_time_info}\n\n"
                        f"Stock Data:\n{formatted_data}\n\n"
                        f"{portfolio_context}\n\n"
                        f"Round {round_idx} Analysis:\n"
                        f"Build on your previous analysis and provide new insights without repetition.\n\n"
                        f"Previous Analysis (if any):\n{prev_analysis}\n\n"
                        f"Please provide your analysis in Chinese."
                    )
                    result = AIService.call_agent(provider, api_key, model, prompt)
                    analysis_memory[agent.id].append(result)
                    steps.append({
                        'phase': 'analysis',
                        'round': round_idx,
                        'agent_id': agent.id,
                        'agent_name': agent.name,
                        'content': result,
                        'timestamp': datetime.now().isoformat()
                    })

            # 3轮辩论
            debate_history = []
            for round_idx in range(1, debate_rounds + 1):
                # 获取当前时间（每轮辩论都更新）
                current_time = datetime.now()
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                current_time_info = f"Current Time: {current_time_str} (Weekday: {current_time.strftime('%A')})"
                
                for agent in agents:
                    provider, api_key, model = resolve_agent_config(agent)
                    other_latest = "\n\n".join([
                        f"{a.name}:\n{analysis_memory[a.id][-1]}"
                        for a in agents if a.id != agent.id and analysis_memory[a.id]
                    ])
                    recent_debate = "\n\n".join([
                        f"Round {item['round']} - {item['agent_name']}:\n{item['content']}"
                        for item in debate_history[-min(len(debate_history), len(agents) * 2):]
                    ]) if debate_history else "None"

                    prompt = (
                        f"{agent.prompt}\n\n"
                        f"{current_time_info}\n\n"
                        "You are participating in a multi-agent debate.\n\n"
                        f"Debate Round {round_idx}:\n"
                        "Respond with counterarguments, supporting evidence, and actionable insights.\n"
                        "Focus on your unique perspective and address opposing viewpoints.\n\n"
                        f"Other agents' latest analyses:\n{other_latest}\n\n"
                        f"Recent Debate History:\n{recent_debate}\n\n"
                        "Please provide your debate response in Chinese."
                    )
                    result = AIService.call_agent(provider, api_key, model, prompt)
                    item = {
                        'phase': 'debate',
                        'round': round_idx,
                        'agent_id': agent.id,
                        'agent_name': agent.name,
                        'content': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    debate_history.append(item)
                    steps.append(item)

            # 资深操作员记录与最终报告
            operator_provider = get_config(db, 'default_ai_provider', 'openai')
            operator_api_key = get_config(db, f'{operator_provider}_api_key')
            if not operator_api_key:
                return jsonify({'success': False, 'error': f'未配置{operator_provider} API Key'}), 400
            operator_model = get_config(db, f'{operator_provider}_model', default_model_map.get(operator_provider, 'gpt-3.5-turbo'))

            transcript = "\n\n".join([
                f"[{item['phase']} R{item['round']}] {item['agent_name']}:\n{item['content']}"
                for item in steps
            ])

            operator_prompt = (
                "You are a senior trading operator and debate recorder.\n"
                "Based on the multi-agent analysis and debate transcript, produce a final research report in Markdown.\n"
                "The report must include sections: Overview, Key Points by Agent, Debate Summary, Risks, Final Recommendation.\n"
                "Provide a clear trading operation suggestion in the Final Recommendation section.\n\n"
                f"{portfolio_context}\n\n"
                f"Transcript:\n{transcript}\n\n"
                "Please output the report in Chinese."
            )

            report_md = AIService.call_agent(operator_provider, operator_api_key, operator_model, operator_prompt)

            return jsonify({
                'success': True,
                'data': {
                    'steps': steps,
                    'report_md': report_md,
                    'analysis_rounds': analysis_rounds,
                    'debate_rounds': debate_rounds
                }
            })
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 辩论分析失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        finally:
            db.close()

    # ==================== AI分析API ====================
    
    @app.route('/api/ai/analyze/<code>', methods=['POST'])
    def analyze_stock_api(code):
        """使用Agent分析股票"""
        db = next(get_db())
        try:
            code_str = str(code).strip()
            if not code_str.isdigit() or len(code_str) != 6:
                return jsonify({'success': False, 'error': '股票代码格式错误'}), 400
            
            data = request.json
            agent_id = data.get('agent_id')
            use_cache = data.get('use_cache', True)
            override_api_key = data.get('override_api_key')
            
            # 获取Agent配置
            agent = get_agent(db, agent_id)
            if not agent or not agent.enabled:
                return jsonify({'success': False, 'error': 'Agent不存在或未启用'}), 400

            portfolio_context = build_ai_portfolio_context(db, code_str)
            context_hash = hashlib.sha1(portfolio_context.encode('utf-8')).hexdigest()[:8]
            cache_type = f'{agent.type}:{context_hash}'
            
            # 检查缓存
            if use_cache:
                cached = get_cached_analysis(db, code_str, cache_type, max_age_minutes=30)
                if cached:
                    return jsonify({
                        'success': True,
                        'data': cached,
                        'cached': True
                    })
            
            # 获取AI配置：移动端可通过override_api_key传入专属Key
            ai_provider = agent.ai_provider or get_config(db, 'default_ai_provider', 'openai')
            api_key_key = f'{ai_provider}_api_key'
            api_key = override_api_key or get_config(db, api_key_key)
            if not api_key:
                return jsonify({'success': False, 'error': f'未配置{ai_provider} API Key'}), 400

            model = agent.model or get_config(db, f'{ai_provider}_model', 'gpt-3.5-turbo')
            
            # 获取股票数据
            print(f"[API] 获取股票数据: {code_str}")
            stock_data = get_comprehensive_data_with_indicators(code_str)
            formatted_data = format_for_ai(stock_data)
            
            # 获取当前时间
            current_time = datetime.now()
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            current_time_info = f"Current Time: {current_time_str} (Weekday: {current_time.strftime('%A')})"
            
            # 构建完整prompt
            full_prompt = (
                f"{agent.prompt}\n\n{current_time_info}\n\n"
                f"Stock Data:\n{formatted_data}\n\n"
                f"{portfolio_context}\n\n"
                "Please provide your analysis in Chinese."
            )
            
            # 调用AI
            try:
                print(f"[API] 调用AI分析: {agent.name} ({ai_provider})")
                result = AIService.call_agent(ai_provider, api_key, model, full_prompt)
                
                # 解析结果（如果是日内做T Agent，尝试提取价格建议）
                analysis_result = {
                    'analysis': result,
                    'agent_name': agent.name,
                    'agent_type': agent.type,
                    'timestamp': datetime.now().isoformat()
                }
                
                # 如果是日内做T Agent，尝试解析买入卖出价格
                if agent.type == 'intraday_t':
                    buy_price, sell_price = parse_intraday_t_prices(result)
                    if buy_price and sell_price:
                        analysis_result['recommendation'] = {
                            'buy_price': buy_price,
                            'sell_price': sell_price
                        }
                
                # 保存缓存
                if use_cache:
                    save_analysis_cache(db, code_str, cache_type, analysis_result)
                
                return jsonify({
                    'success': True,
                    'data': analysis_result,
                    'cached': False
                })
            except Exception as e:
                error_msg = str(e)
                print(f"[API] AI分析失败: {error_msg}")
                return jsonify({'success': False, 'error': f'AI分析失败: {error_msg}'}), 500
                
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 分析股票失败: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        finally:
            db.close()
    
    def parse_intraday_t_prices(text: str):
        """从文本中解析买入卖出价格（简单实现）"""
        try:
            # 尝试提取价格数字
            buy_match = re.search(r'买入[价格]?[：:]\s*(\d+\.?\d*)', text)
            sell_match = re.search(r'卖出[价格]?[：:]\s*(\d+\.?\d*)', text)
            
            buy_price = float(buy_match.group(1)) if buy_match else None
            sell_price = float(sell_match.group(1)) if sell_match else None
            
            return buy_price, sell_price
        except:
            return None, None
    
    # ==================== 策略API ====================

    @app.route('/api/strategy/four_lights/scan', methods=['POST'])
    def scan_four_lights_api():
        """扫描全市场高流动性股票，返回四灯共振 Top 候选并保存快照。"""
        db = SessionLocal()
        try:
            body = request.get_json(silent=True) or {}
            session = str(body.get('session') or 'auto')
            top_n = max(2, min(int(body.get('top_n', 5)), 10))
            result = scan_four_lights(
                session=session,
                top_n=top_n,
                local_capital_flows=get_local_capital_flow_map(db),
            )
            capital_snapshots = result.pop('_capital_snapshots', [])
            save_capital_flow_snapshots(db, capital_snapshots)
            result['run_id'] = save_four_lights_run(db, result)
            result['validation_target'] = (
                '当日14:30后验证'
                if result['session'] == 'morning'
                else '下一交易日验证'
            )
            return jsonify({'success': True, 'data': result})
        except ValueError as exc:
            db.rollback()
            return jsonify({'success': False, 'error': str(exc)}), 400
        except Exception as exc:
            db.rollback()
            print(f"[API] 四灯策略扫描失败: {exc}")
            return jsonify({'success': False, 'error': f'四灯策略扫描失败: {str(exc)}'}), 500
        finally:
            db.close()

    @app.route('/api/strategy/four_lights/history', methods=['GET', 'DELETE'])
    def four_lights_history_api():
        """读取或清空四灯历史信号；到达验证时点时自动记录当前收益。"""
        db = SessionLocal()
        try:
            if request.method == 'DELETE':
                deleted = delete_all_signal_runs(db, 'four_lights')
                return jsonify({'success': True, 'data': {'deleted': deleted}})
            if request.args.get('validate', 'true').lower() in ('1', 'true', 'yes'):
                validate_pending_signals(db)
            limit = max(1, min(int(request.args.get('limit', 10)), 30))
            return jsonify({
                'success': True,
                'data': list_signal_runs(db, limit_runs=limit, strategy='four_lights'),
            })
        finally:
            db.close()

    @app.route('/api/strategy/four_lights/history/<run_id>', methods=['DELETE'])
    def delete_four_lights_history_api(run_id):
        """按扫描批次删除四灯信号与验证记录。"""
        db = SessionLocal()
        try:
            deleted = delete_signal_run(db, run_id, strategy='four_lights')
            if not deleted:
                return jsonify({'success': False, 'error': '历史记录不存在'}), 404
            return jsonify({'success': True, 'data': {'deleted': deleted}})
        except Exception as exc:
            db.rollback()
            return jsonify({'success': False, 'error': str(exc)}), 500
        finally:
            db.close()

    @app.route('/api/strategy/overnight/scan', methods=['POST'])
    def scan_overnight_api():
        """扫描尾盘隔夜超短候选，默认次日卖出并保存验证快照。"""
        db = SessionLocal()
        try:
            body = request.get_json(silent=True) or {}
            top_n = max(2, min(int(body.get('top_n', 5)), 10))
            result = scan_overnight(top_n=top_n)
            result['run_id'] = save_overnight_run(db, result)
            result['validation_target'] = '下一交易日开盘后验证'
            return jsonify({'success': True, 'data': result})
        except Exception as exc:
            return jsonify({'success': False, 'error': f'隔夜策略扫描失败: {str(exc)}'}), 500
        finally:
            db.close()

    @app.route('/api/strategy/overnight/history', methods=['GET', 'DELETE'])
    def overnight_history_api():
        """读取或清空隔夜策略历史信号。"""
        db = SessionLocal()
        try:
            if request.method == 'DELETE':
                deleted = delete_all_signal_runs(db, 'overnight')
                return jsonify({'success': True, 'data': {'deleted': deleted}})
            if request.args.get('validate', 'true').lower() in ('1', 'true', 'yes'):
                validate_pending_signals(db)
            limit = max(1, min(int(request.args.get('limit', 10)), 30))
            return jsonify({
                'success': True,
                'data': list_signal_runs(db, limit_runs=limit, strategy='overnight'),
            })
        finally:
            db.close()

    @app.route('/api/strategy/overnight/history/<run_id>', methods=['DELETE'])
    def delete_overnight_history_api(run_id):
        """按扫描批次删除隔夜信号与验证记录。"""
        db = SessionLocal()
        try:
            deleted = delete_signal_run(db, run_id, strategy='overnight')
            if not deleted:
                return jsonify({'success': False, 'error': '历史记录不存在'}), 404
            return jsonify({'success': True, 'data': {'deleted': deleted}})
        except Exception as exc:
            db.rollback()
            return jsonify({'success': False, 'error': str(exc)}), 500
        finally:
            db.close()

    @app.route('/api/strategy/strong_stocks')
    def get_strong_stocks():
        """获取强势股（前两个交易日指定时间前涨停，当前未涨停）"""
        try:
            # 获取参数：涨停截止时间，默认11:30
            limit_time = request.args.get('limit_time', '11:30')  # 涨停截止时间（T-1和T-2共用）
            top_n = max(2, min(int(request.args.get('top_n', 5)), 10))
            
            print(f"[API] 开始筛选强势股... 截止时间={limit_time}")
            
            # 获取最近的交易日
            def get_recent_trade_dates():
                """获取最近的交易日（使用akshare）"""
                try:
                    import akshare as ak
                    # 使用akshare获取交易日历
                    trade_cal = ak.tool_trade_date_hist_sina()
                    today = datetime.now().date()
                    
                    # 找到最近的交易日
                    trade_dates = pd.to_datetime(trade_cal['trade_date']).dt.date.tolist()
                    trade_dates = [d for d in trade_dates if d <= today]
                    trade_dates.sort(reverse=True)
                    
                    if len(trade_dates) >= 3:
                        return [trade_dates[0], trade_dates[1], trade_dates[2]]
                    else:
                        print(f"[API] 交易日数据不足，只有 {len(trade_dates)} 个")
                        # 返回简单估计的日期
                        today = date.today()
                        return [today, today - timedelta(days=1), today - timedelta(days=2)]
                except Exception as e:
                    print(f"[API] 获取交易日失败: {e}")
                    import traceback
                    print(f"[API] 错误堆栈: {traceback.format_exc()}")
                    # 返回简单估计的日期
                    today = date.today()
                    return [today, today - timedelta(days=1), today - timedelta(days=2)]
            
            trade_dates = get_recent_trade_dates()
            if len(trade_dates) < 3:
                return jsonify({'error': '无法获取足够的交易日数据'}), 500
            
            t_date = trade_dates[0]
            t1_date = trade_dates[1]
            t2_date = trade_dates[2]
            
            print(f"[API] 交易日: T={t_date}, T-1={t1_date}, T-2={t2_date}")
            
            # 获取T-1和T-2的涨停数据
            def get_limit_up_stocks(date_obj):
                """获取指定日期的涨停股票（使用akshare）"""
                try:
                    import akshare as ak
                    date_str = date_obj.strftime('%Y%m%d')
                    
                    print(f"[API] 调用akshare获取涨停数据，日期: {date_str}")
                    limit_up_df = ak.stock_zt_pool_em(date=date_str)
                    
                    if limit_up_df is None or len(limit_up_df) == 0:
                        print(f"[API] 日期 {date_str} 无涨停数据")
                        return []
                    
                    print(f"[API] 日期 {date_str} 获取到 {len(limit_up_df)} 条涨停数据")
                    
                    stocks = []
                    for idx, row in limit_up_df.iterrows():
                        # 提取股票代码
                        code = None
                        for code_field in ['代码', '股票代码', 'code']:
                            if code_field in row and pd.notna(row[code_field]):
                                code_str = str(row[code_field]).strip()
                                if code_str.isdigit() and len(code_str) == 6:
                                    code = code_str
                                    break
                                elif code_str.isdigit():
                                    code = code_str.zfill(6)
                                    break
                        
                        if not code:
                            continue
                        
                        # 提取股票名称
                        name = None
                        for name_field in ['名称', '股票名称', 'name']:
                            if name_field in row and pd.notna(row[name_field]):
                                name = str(row[name_field]).strip()
                                break
                        
                        # 提取涨停时间
                        first_limit_time = None
                        for field in ['首次封板时间', '最后封板时间', '封板时间', '涨停时间', '首次涨停时间']:
                            if field in row and pd.notna(row[field]) and str(row[field]).strip():
                                first_limit_time = str(row[field]).strip()
                                if ' ' in first_limit_time:
                                    first_limit_time = first_limit_time.split(' ')[1]
                                break
                        
                        # 提取连板数和炸板次数
                        consecutive_days = 0
                        for field in ['连板数', '连板']:
                            if field in row and pd.notna(row[field]):
                                try:
                                    consecutive_days = int(row[field])
                                except:
                                    pass
                                break
                        
                        break_count = 0
                        for field in ['炸板次数', '炸板']:
                            if field in row and pd.notna(row[field]):
                                try:
                                    break_count = int(row[field])
                                except:
                                    pass
                                break
                        
                        # 提取行业
                        industry = ''
                        for field in ['所属行业', '行业']:
                            if field in row and pd.notna(row[field]):
                                industry = str(row[field]).strip()
                                break
                        
                        stocks.append({
                            'code': code,
                            'name': name or '未知',
                            'first_limit_time': first_limit_time,
                            'consecutive_days': consecutive_days,
                            'break_count': break_count,
                            'industry': industry,
                            'date': date_str
                        })
                    
                    return stocks
                except Exception as e:
                    print(f"[API] 获取 {date_obj} 涨停数据失败: {e}")
                    import traceback
                    print(f"[API] 错误堆栈: {traceback.format_exc()}")
                    return []
            
            print("[API] 获取T-1和T-2涨停数据...")
            t1_stocks = get_limit_up_stocks(t1_date)
            t2_stocks = get_limit_up_stocks(t2_date)
            
            print(f"[API] T-1涨停股票数: {len(t1_stocks)}, T-2涨停股票数: {len(t2_stocks)}")
            
            # 筛选指定时间之前涨停的股票
            def filter_early_limit(stocks, cutoff_time):
                """筛选指定时间之前涨停的股票"""
                result = []
                try:
                    # 将截止时间转换为数字格式（如11:30 -> 113000）
                    if ':' in cutoff_time:
                        parts = cutoff_time.split(':')
                        cutoff_value = int(parts[0]) * 10000 + int(parts[1]) * 100
                    else:
                        cutoff_value = int(cutoff_time)
                except:
                    cutoff_value = 113000  # 默认11:30
                
                print(f"[API] 筛选截止时间值: {cutoff_value}")
                
                for stock in stocks:
                    time_str = stock.get('first_limit_time', '')
                    try:
                        # 处理不同格式的时间
                        if ':' in str(time_str):
                            # 格式如 "09:25:00" 或 "09:25"
                            parts = str(time_str).split(':')
                            time_value = int(parts[0]) * 10000 + int(parts[1]) * 100
                            if len(parts) > 2:
                                time_value += int(parts[2])
                        else:
                            # 格式如 "092500" 或 92500
                            time_value = int(time_str)
                        
                        # 在截止时间之前或等于截止时间涨停
                        if time_value <= cutoff_value:
                            result.append(stock)
                    except Exception as e:
                        print(f"[API] 解析时间失败: {time_str}, 错误: {e}")
                        continue
                
                print(f"[API] 筛选前{len(stocks)}只，筛选后{len(result)}只")
                return result
            
            t1_early = filter_early_limit(t1_stocks, limit_time)
            t2_early = filter_early_limit(t2_stocks, limit_time)
            
            print(f"[API] T-1早盘涨停: {len(t1_early)}, T-2早盘涨停: {len(t2_early)}")
            
            # 找出同时在T-1和T-2都早盘涨停的股票
            t1_codes = {s['code'] for s in t1_early}
            t2_codes = {s['code'] for s in t2_early}
            common_codes = t1_codes & t2_codes
            
            print(f"[API] 同时在T-1和T-2早盘涨停的股票数: {len(common_codes)}")
            
            # 获取T日（今天）的涨停股票
            t_limit_stocks = get_limit_up_stocks(t_date)
            t_limit_codes = {s['code'] for s in t_limit_stocks}
            
            print(f"[API] T日涨停股票数: {len(t_limit_codes)}")

            # 获取T日（今天）的跌停股票
            t_down_codes = set()
            try:
                import akshare as ak
                t_down_df = ak.stock_dt_pool_em(date=t_date.strftime('%Y%m%d'))
                if t_down_df is not None and len(t_down_df) > 0 and '代码' in t_down_df.columns:
                    t_down_codes = set(t_down_df['代码'].astype(str).str.zfill(6).tolist())
                print(f"[API] T日跌停股票数: {len(t_down_codes)}")
            except Exception as e:
                print(f"[API] 获取T日跌停数据失败: {e}")
            
            # 筛选出今天还没有涨停且未跌停的股票
            result_codes = common_codes - t_limit_codes - t_down_codes
            
            print(f"[API] 符合条件的强势股数量: {len(result_codes)}")
            
            # 组装结果
            result_stocks = []
            for code in result_codes:
                # 从T-1数据中获取股票信息
                t1_info = next((s for s in t1_early if s['code'] == code), None)
                t2_info = next((s for s in t2_early if s['code'] == code), None)
                
                if t1_info:
                    stock_data = {
                        'code': code,
                        'name': t1_info['name'],
                        't1_limit_time': t1_info['first_limit_time'],
                        't2_limit_time': t2_info['first_limit_time'] if t2_info else None,
                        'consecutive_days': t1_info.get('consecutive_days', 0),
                        'break_count': t1_info.get('break_count', 0),
                        'industry': t1_info.get('industry', ''),
                        'current_price': None,
                        'change_percent': None,
                        'volume': None,
                        'amount': None,
                    }
                    
                    # 获取当前实时行情
                    try:
                        realtime = get_realtime_data(code)
                        if realtime:
                            stock_data['current_price'] = realtime.get('current_price')
                            stock_data['change_percent'] = realtime.get('change_percent')
                            stock_data['volume'] = realtime.get('volume')
                            stock_data['amount'] = realtime.get('amount')
                    except Exception as e:
                        print(f"[API] 获取 {code} 实时行情失败: {e}")
                    
                    result_stocks.append(stock_data)
            
            result_stocks = rank_strong_stocks(result_stocks, top_n=top_n)
            recommended_count = sum(1 for stock in result_stocks if stock['recommended'])
            print(
                f"[API] 返回强势股数据，共 {len(result_stocks)} 只，"
                f"推荐 {recommended_count} 只"
            )
            
            return jsonify({
                'strategy': 'strong_stocks',
                'description': f'T-1和T-2日{limit_time}前涨停，T日未涨停',
                'params': {
                    'limit_time': limit_time,
                    'top_n': top_n,
                },
                'trade_dates': {
                    'T': t_date.strftime('%Y-%m-%d'),
                    'T-1': t1_date.strftime('%Y-%m-%d'),
                    'T-2': t2_date.strftime('%Y-%m-%d'),
                },
                'count': len(result_stocks),
                'recommended_count': recommended_count,
                'stocks': result_stocks
            })
        
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 筛选强势股失败: {error_msg}")
            import traceback
            print(f"[API] 错误堆栈: {traceback.format_exc()}")
            return jsonify({'error': '筛选强势股失败', 'message': error_msg}), 500

    # ==================== 流水线 + 飞书 ====================
    @app.route('/api/pipeline/strategy_to_multi_debate', methods=['POST'])
    def pipeline_strategy_to_multi_debate():
        """策略筛选 → 全选强势股代码 → 启动多选一辩论（供脚本/飞书对接）。"""
        ok, err = check_pipeline_token(request)
        if not ok:
            return jsonify({'success': False, 'error': err}), 401
        data = request.json or {}
        limit_time = str(data.get('limit_time', '11:30'))
        agent_ids = data.get('agent_ids')
        if agent_ids is not None and not isinstance(agent_ids, list):
            return jsonify({'success': False, 'error': 'agent_ids 须为数组'}), 400
        analysis_rounds = int(data.get('analysis_rounds', 2))
        debate_rounds = int(data.get('debate_rounds', 1))
        override_api_key = data.get('override_api_key')

        good, result = execute_strategy_to_multi_debate(
            app,
            limit_time=limit_time,
            agent_ids=agent_ids,
            analysis_rounds=analysis_rounds,
            debate_rounds=debate_rounds,
            override_api_key=override_api_key,
        )
        if not good:
            return jsonify({'success': False, 'error': result}), 400
        wh = (os.environ.get('FEISHU_WEBHOOK_URL') or '').strip()
        if wh:
            feishu_webhook_send_text(
                wh,
                f"策略流水线已启动\njob_id: {result.get('job_id')}\n股票数: {result.get('count')}",
            )
        return jsonify({'success': True, 'data': result})

    @app.route('/api/feishu/events', methods=['POST'])
    def feishu_events():
        """飞书开放平台事件订阅：URL 校验 + 群消息关键词触发流水线。"""
        body = request.get_json(silent=True) or {}
        ch = handle_feishu_event_body(body)
        if ch is not None:
            return jsonify(ch)

        if body.get('schema') == '2.0':
            header = body.get('header') or {}
            if not verify_feishu_event_token(header):
                return jsonify({'code': 403, 'msg': 'verification token mismatch'}), 403
            et = header.get('event_type')
            if et == 'im.message.receive_v1':
                event = body.get('event') or {}
                text = parse_feishu_message_text(event)
                if feishu_should_trigger(text):
                    kw = {
                        'limit_time': os.environ.get('PIPELINE_LIMIT_TIME', '11:30'),
                        'analysis_rounds': int(os.environ.get('PIPELINE_ANALYSIS_ROUNDS', '2')),
                        'debate_rounds': int(os.environ.get('PIPELINE_DEBATE_ROUNDS', '1')),
                    }
                    wh = (os.environ.get('FEISHU_WEBHOOK_URL') or '').strip()
                    run_pipeline_in_thread(app, kw, wh)
                return jsonify({})
        return jsonify({})
