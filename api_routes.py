#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API路由模块"""

from flask import jsonify, request
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from datetime import datetime
import json
import re
from data_fetchers import get_realtime_data, get_timeline_data, get_minute_kline, get_daily_kline, get_money_flow, get_money_flow_history, get_money_flow_realtime_kline, get_fundamental_data, get_industry_comparison, get_news_from_stock, get_guba_posts
from technical_indicators import get_comprehensive_data, get_comprehensive_data_with_indicators
from data_formatters import format_for_ai, to_json
from models import get_db, SessionLocal
from db import (
    get_watchlist, add_to_watchlist, remove_from_watchlist, update_watchlist_order,
    get_config, set_config, get_all_configs,
    get_agents, get_agent, create_agent, update_agent, delete_agent,
    get_cached_analysis, save_analysis_cache,
    create_debate_job, update_debate_job, get_debate_job, list_debate_jobs, cancel_debate_job, delete_debate_job
)
from ai_service import AIService

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
                '/api/watchlist': '自选股管理，GET获取列表，POST添加',
                '/api/watchlist/<code>': '自选股管理，DELETE删除',
                '/api/config': '配置管理，GET获取所有配置，POST设置配置',
                '/api/config/<key>': '配置管理，GET获取单个配置，POST设置配置',
                '/api/agents': 'Agent管理，GET获取列表，POST创建',
                '/api/agents/<id>': 'Agent管理，PUT更新，DELETE删除',
                '/api/ai/analyze/<code>': 'AI分析股票，POST请求，body: {"agent_id": 1}',
                '/api/ai/debate/start/<code>': '启动多Agent辩论任务，POST请求',
                '/api/ai/debate/status/<job_id>': '查询多Agent辩论任务状态',
                '/api/ai/debate/jobs': '获取辩论任务列表，参数: ?status=active|completed|failed|canceled',
                '/api/ai/debate/stop/<job_id>': '终止辩论任务，POST请求',
                '/api/ai/debate/delete/<job_id>': '删除辩论任务，DELETE请求',
                '/api/health': '健康检查',
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

    def _run_debate_job(job_id, code_str, agent_ids, analysis_rounds, debate_rounds):
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
                'siliconflow': 'Qwen/Qwen2.5-7B-Instruct'
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

            # 多轮分析（同一轮并行）
            for round_idx in range(1, analysis_rounds + 1):
                if _is_job_canceled(db, job_id):
                    _update_debate_job(db, job_id, status='canceled')
                    return
                prompts = []
                for agent in agents:
                    prev_analysis = "\n\n".join(analysis_memory[agent.id][-2:]) if analysis_memory[agent.id] else "None"
                    prompts.append((
                        agent,
                        f"{agent.prompt}\n\n"
                        f"Stock Data:\n{formatted_data}\n\n"
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
                        result = future.result()
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
                        "You are participating in a multi-agent debate.\n\n"
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
                        result = future.result()
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
            operator_api_key = get_config(db, f'{operator_provider}_api_key')
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
                "Provide a clear trading operation suggestion in the Final Recommendation section.\n\n"
                f"Stock Data (key fields):\n{formatted_data}\n\n"
                f"Sentiment Summary:\n{sentiment_text}\n\n"
                f"Transcript:\n{transcript}\n\n"
                "Please output the report in Chinese."
            )

            report_md = AIService.call_agent(operator_provider, operator_api_key, operator_model, operator_prompt)

            _update_debate_job(db, job_id, status='completed', progress=100, report_md=report_md, steps=steps)
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 辩论分析失败: {error_msg}")
            _update_debate_job(db, job_id, status='failed', error=error_msg)
        finally:
            db.close()

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
                args=(job_id, code_str, agent_ids, analysis_rounds, debate_rounds),
                daemon=True
            )
            thread.start()

            return jsonify({'success': True, 'data': {'job_id': job_id, 'name': job_name}})
        except Exception as e:
            error_msg = str(e)
            print(f"[API] 启动辩论任务失败: {error_msg}")
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

            default_model_map = {
                'openai': 'gpt-3.5-turbo',
                'deepseek': 'deepseek-chat',
                'qwen': 'qwen-turbo',
                'gemini': 'gemini-pro',
                'siliconflow': 'Qwen/Qwen2.5-7B-Instruct'
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

            # 3轮分析
            for round_idx in range(1, analysis_rounds + 1):
                for agent in agents:
                    provider, api_key, model = resolve_agent_config(agent)
                    prev_analysis = "\n\n".join(analysis_memory[agent.id][-2:]) if analysis_memory[agent.id] else "None"
                    prompt = (
                        f"{agent.prompt}\n\n"
                        f"Stock Data:\n{formatted_data}\n\n"
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
            
            # 获取Agent配置
            agent = get_agent(db, agent_id)
            if not agent or not agent.enabled:
                return jsonify({'success': False, 'error': 'Agent不存在或未启用'}), 400
            
            # 检查缓存
            if use_cache:
                cached = get_cached_analysis(db, code_str, agent.type, max_age_minutes=30)
                if cached:
                    return jsonify({
                        'success': True,
                        'data': cached,
                        'cached': True
                    })
            
            # 获取AI配置
            ai_provider = agent.ai_provider or get_config(db, 'default_ai_provider', 'openai')
            api_key_key = f'{ai_provider}_api_key'
            api_key = get_config(db, api_key_key)
            if not api_key:
                return jsonify({'success': False, 'error': f'未配置{ai_provider} API Key'}), 400
            
            model = agent.model or get_config(db, f'{ai_provider}_model', 'gpt-3.5-turbo')
            
            # 获取股票数据
            print(f"[API] 获取股票数据: {code_str}")
            stock_data = get_comprehensive_data_with_indicators(code_str)
            formatted_data = format_for_ai(stock_data)
            
            # 构建完整prompt
            full_prompt = f"{agent.prompt}\n\nStock Data:\n{formatted_data}\n\nPlease provide your analysis in Chinese."
            
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
                    save_analysis_cache(db, code_str, agent.type, analysis_result)
                
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
