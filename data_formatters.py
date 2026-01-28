#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据格式化模块 - 用于AI分析和JSON序列化"""

import pandas as pd
import json
from datetime import datetime


def format_for_ai(data_dict):
    """格式化数据为AI分析友好的格式"""
    if not data_dict:
        return "无数据"
    
    info = []
    info.append(f"=== 股票代码: {data_dict['code']} ===\n")
    
    if data_dict.get('realtime'):
        rt = data_dict['realtime']
        info.append("【实时行情】")
        info.append(f"股票名称: {rt.get('name', 'N/A')}")
        info.append(f"当前价格: {rt.get('current_price', 'N/A')} 元")
        info.append(f"今日开盘: {rt.get('open', 'N/A')} 元")
        info.append(f"昨日收盘: {rt.get('yesterday_close', 'N/A')} 元")
        info.append(f"今日最高: {rt.get('high', 'N/A')} 元")
        info.append(f"今日最低: {rt.get('low', 'N/A')} 元")
        if rt.get('change_percent') is not None:
            info.append(f"涨跌幅: {rt.get('change_percent'):.2f}%")
        info.append(f"成交量: {rt.get('volume', 'N/A')} 手")
        info.append(f"成交额: {rt.get('amount', 'N/A')} 元")
        if rt.get('turnover_rate') is not None:
            info.append(f"换手率: {rt.get('turnover_rate'):.2f}%")
        if rt.get('bid1_price'):
            info.append(f"买一: {rt.get('bid1_price')} 元 ({rt.get('bid1_volume')} 手)")
        if rt.get('ask1_price'):
            info.append(f"卖一: {rt.get('ask1_price')} 元 ({rt.get('ask1_volume')} 手)")
        info.append("")
    
    if data_dict.get('timeline') is not None and len(data_dict['timeline']) > 0:
        timeline_df = data_dict['timeline']
        info.append("【分时数据统计（每分钟）】")
        info.append(f"数据点数: {len(timeline_df)} 个")
        if 'price' in timeline_df.columns:
            info.append(f"最高价: {timeline_df['price'].max():.2f} 元")
            info.append(f"最低价: {timeline_df['price'].min():.2f} 元")
            info.append(f"平均价: {timeline_df['price'].mean():.2f} 元")
            if 'volume' in timeline_df.columns and 'amount' in timeline_df.columns:
                total_amount = timeline_df['amount'].sum()
                total_volume = timeline_df['volume'].sum()
                if total_volume > 0:
                    vwap = total_amount / total_volume
                    info.append(f"VWAP(成交量加权均价): {vwap:.2f} 元")
            elif 'volume' in timeline_df.columns and 'price' in timeline_df.columns:
                total_amount = (timeline_df['price'] * timeline_df['volume']).sum()
                total_volume = timeline_df['volume'].sum()
                if total_volume > 0:
                    vwap = total_amount / total_volume
                    info.append(f"VWAP(成交量加权均价): {vwap:.2f} 元")
        info.append("")
    
    if data_dict.get('minute_5') is not None and len(data_dict['minute_5']) > 0:
        df_5m = data_dict['minute_5']
        info.append("【5分钟K线统计】")
        info.append(f"数据条数: {len(df_5m)} 根")
        if 'close' in df_5m.columns:
            info.append(f"最新收盘: {df_5m['close'].iloc[-1]:.2f} 元")
            info.append(f"最高价: {df_5m['high'].max():.2f} 元")
            info.append(f"最低价: {df_5m['low'].min():.2f} 元")
        if 'volume' in df_5m.columns:
            info.append(f"总成交量: {df_5m['volume'].sum():.0f} 手")
        info.append("")
    
    if data_dict.get('minute_15') is not None and len(data_dict['minute_15']) > 0:
        df_15m = data_dict['minute_15']
        info.append("【15分钟K线统计】")
        info.append(f"数据条数: {len(df_15m)} 根")
        if 'close' in df_15m.columns:
            info.append(f"最新收盘: {df_15m['close'].iloc[-1]:.2f} 元")
        info.append("")
    
    if data_dict.get('minute_30') is not None and len(data_dict['minute_30']) > 0:
        df_30m = data_dict['minute_30']
        info.append("【30分钟K线统计】")
        info.append(f"数据条数: {len(df_30m)} 根")
        if 'close' in df_30m.columns:
            info.append(f"最新收盘: {df_30m['close'].iloc[-1]:.2f} 元")
        info.append("")
    
    if data_dict.get('daily') is not None and len(data_dict['daily']) > 0:
        daily_df = data_dict['daily']
        info.append("【日K线统计（最近240个交易日）】")
        info.append(f"数据条数: {len(daily_df)} 根")
        if 'close' in daily_df.columns:
            info.append(f"最新收盘: {daily_df['close'].iloc[-1]:.2f} 元")
            info.append(f"最高价: {daily_df['high'].max():.2f} 元")
            info.append(f"最低价: {daily_df['low'].min():.2f} 元")
            if len(daily_df) >= 2:
                change = (daily_df['close'].iloc[-1] - daily_df['close'].iloc[-2]) / daily_df['close'].iloc[-2] * 100
                info.append(f"今日涨跌: {change:.2f}%")
        info.append("")
        
        # 技术指标
        if len(daily_df) > 0:
            latest = daily_df.iloc[-1]
            info.append("【技术指标分析】")
            
            ma_cols = [col for col in daily_df.columns if col.startswith('MA') and not col.startswith('MACD')]
            if ma_cols:
                ma_info = []
                for col in sorted(ma_cols):
                    if pd.notna(latest[col]):
                        ma_info.append(f"{col}: {latest[col]:.2f}")
                if ma_info:
                    info.append("移动平均线(MA): " + ", ".join(ma_info))
            
            ema_cols = [col for col in daily_df.columns if col.startswith('EMA')]
            if ema_cols:
                ema_info = []
                for col in sorted(ema_cols):
                    if pd.notna(latest[col]):
                        ema_info.append(f"{col}: {latest[col]:.2f}")
                if ema_info:
                    info.append("指数移动平均线(EMA): " + ", ".join(ema_info))
            
            if 'MACD_DIF' in daily_df.columns and pd.notna(latest['MACD_DIF']):
                macd_dif = latest['MACD_DIF']
                macd_dea = latest.get('MACD_DEA', 0) if pd.notna(latest.get('MACD_DEA')) else 0
                macd_hist = latest.get('MACD', 0) if pd.notna(latest.get('MACD')) else 0
                macd_signal = "金叉" if macd_dif > macd_dea else "死叉"
                info.append(f"MACD: DIF={macd_dif:.3f}, DEA={macd_dea:.3f}, MACD柱={macd_hist:.3f} ({macd_signal})")
            
            if 'RSI14' in daily_df.columns and pd.notna(latest['RSI14']):
                rsi = latest['RSI14']
                rsi_status = "超买" if rsi > 70 else ("超卖" if rsi < 30 else "正常")
                info.append(f"RSI(14): {rsi:.2f} ({rsi_status})")
            
            if 'KDJ_K' in daily_df.columns and pd.notna(latest['KDJ_K']):
                kdj_k = latest['KDJ_K']
                kdj_d = latest.get('KDJ_D', 0) if pd.notna(latest.get('KDJ_D')) else 0
                kdj_j = latest.get('KDJ_J', 0) if pd.notna(latest.get('KDJ_J')) else 0
                kdj_signal = "金叉" if kdj_k > kdj_d else "死叉"
                info.append(f"KDJ: K={kdj_k:.2f}, D={kdj_d:.2f}, J={kdj_j:.2f} ({kdj_signal})")
            
            if 'BOLL_UPPER' in daily_df.columns and pd.notna(latest['BOLL_UPPER']):
                current_price = latest.get('close', 0)
                boll_upper = latest['BOLL_UPPER']
                boll_mid = latest.get('BOLL_MID', 0) if pd.notna(latest.get('BOLL_MID')) else 0
                boll_lower = latest.get('BOLL_LOWER', 0) if pd.notna(latest.get('BOLL_LOWER')) else 0
                boll_position = ""
                if current_price > 0:
                    if current_price > boll_upper:
                        boll_position = "突破上轨"
                    elif current_price < boll_lower:
                        boll_position = "跌破下轨"
                    else:
                        boll_position = "轨道内"
                info.append(f"布林带: 上轨={boll_upper:.2f}, 中轨={boll_mid:.2f}, 下轨={boll_lower:.2f} ({boll_position})")
            
            if 'OBV' in daily_df.columns and pd.notna(latest['OBV']):
                obv = latest['OBV']
                if len(daily_df) >= 2:
                    obv_change = obv - daily_df.iloc[-2].get('OBV', 0)
                    obv_trend = "上升" if obv_change > 0 else "下降"
                    info.append(f"OBV: {obv:.0f} ({obv_trend})")
            
            info.append("")
    
    # 板块/行业信息
    if data_dict.get('sector_info') and len(data_dict['sector_info']) > 0:
        info.append("【板块/行业信息】")
        sectors = data_dict['sector_info']
        info.append(f"所属板块/行业: {', '.join(sectors)}")
        info.append("")
    
    # 资金流向
    if data_dict.get('money_flow'):
        mf = data_dict['money_flow']
        info.append("【资金流向分析】")
        
        # 主力资金
        if mf.get('main_net_inflow') is not None:
            main_net = mf['main_net_inflow']
            main_status = "流入" if main_net > 0 else "流出"
            main_ratio = f" (净比: {mf.get('main_net_ratio', 0):.2f}%)" if mf.get('main_net_ratio') is not None else ""
            info.append(f"主力资金净{main_status}: {abs(main_net):.2f} 万元{main_ratio}")
        
        # 超大单
        if mf.get('super_large_net_inflow') is not None:
            super_large_net = mf['super_large_net_inflow']
            super_large_status = "流入" if super_large_net > 0 else "流出"
            super_large_ratio = f" (净比: {mf.get('super_large_net_ratio', 0):.2f}%)" if mf.get('super_large_net_ratio') is not None else ""
            info.append(f"超大单净{super_large_status}: {abs(super_large_net):.2f} 万元{super_large_ratio}")
            if mf.get('super_large_inflow') is not None and mf.get('super_large_outflow') is not None:
                info.append(f"  超大单流入: {mf['super_large_inflow']:.2f} 万元, 流出: {mf['super_large_outflow']:.2f} 万元")
        
        # 大单
        if mf.get('large_net_inflow') is not None:
            large_net = mf['large_net_inflow']
            large_status = "流入" if large_net > 0 else "流出"
            large_ratio = f" (净比: {mf.get('large_net_ratio', 0):.2f}%)" if mf.get('large_net_ratio') is not None else ""
            info.append(f"大单净{large_status}: {abs(large_net):.2f} 万元{large_ratio}")
            if mf.get('large_inflow') is not None and mf.get('large_outflow') is not None:
                info.append(f"  大单流入: {mf['large_inflow']:.2f} 万元, 流出: {mf['large_outflow']:.2f} 万元")
        
        # 中单
        if mf.get('medium_net_inflow') is not None:
            medium_net = mf['medium_net_inflow']
            medium_status = "流入" if medium_net > 0 else "流出"
            medium_ratio = f" (净比: {mf.get('medium_net_ratio', 0):.2f}%)" if mf.get('medium_net_ratio') is not None else ""
            info.append(f"中单净{medium_status}: {abs(medium_net):.2f} 万元{medium_ratio}")
            if mf.get('medium_inflow') is not None and mf.get('medium_outflow') is not None:
                info.append(f"  中单流入: {mf['medium_inflow']:.2f} 万元, 流出: {mf['medium_outflow']:.2f} 万元")
        
        # 小单
        if mf.get('small_net_inflow') is not None:
            small_net = mf['small_net_inflow']
            small_status = "流入" if small_net > 0 else "流出"
            small_ratio = f" (净比: {mf.get('small_net_ratio', 0):.2f}%)" if mf.get('small_net_ratio') is not None else ""
            info.append(f"小单净{small_status}: {abs(small_net):.2f} 万元{small_ratio}")
            if mf.get('small_inflow') is not None and mf.get('small_outflow') is not None:
                info.append(f"  小单流入: {mf['small_inflow']:.2f} 万元, 流出: {mf['small_outflow']:.2f} 万元")
        
        # 如果所有数据都是None，说明未获取到
        if all(mf.get(k) is None for k in ['main_net_inflow', 'super_large_net_inflow', 'large_net_inflow', 'medium_net_inflow', 'small_net_inflow']):
            info.append("资金流向数据暂不可用")
        info.append("")
    
    # 基本面数据
    if data_dict.get('fundamental'):
        fund = data_dict['fundamental']
        info.append("【基本面分析】")
        
        # 估值指标
        if fund.get('pe_dynamic') is not None or fund.get('pe_ttm') is not None:
            pe_info = []
            if fund.get('pe_dynamic') is not None:
                pe_info.append(f"动态PE: {fund['pe_dynamic']:.2f}")
            if fund.get('pe_ttm') is not None:
                pe_info.append(f"TTM PE: {fund['pe_ttm']:.2f}")
            if pe_info:
                info.append("市盈率: " + ", ".join(pe_info))
        
        if fund.get('pb_ratio') is not None:
            info.append(f"市净率(PB): {fund['pb_ratio']:.2f}")
        if fund.get('ps_ratio') is not None:
            info.append(f"市销率(PS): {fund['ps_ratio']:.2f}")
        if fund.get('pcf_ratio') is not None:
            info.append(f"市现率(PCF): {fund['pcf_ratio']:.2f}")
        
        # 市值和股本
        if fund.get('total_market_cap') is not None:
            info.append(f"总市值: {fund['total_market_cap']:.2f} 亿元")
        if fund.get('circulating_market_cap') is not None:
            info.append(f"流通市值: {fund['circulating_market_cap']:.2f} 亿元")
        if fund.get('total_shares') is not None:
            info.append(f"总股本: {fund['total_shares']:.2f} 亿股")
        if fund.get('circulating_shares') is not None:
            info.append(f"流通股本: {fund['circulating_shares']:.2f} 亿股")
        
        # 财务指标
        if fund.get('roe') is not None:
            info.append(f"净资产收益率(ROE): {fund['roe']:.2f}%")
        if fund.get('eps') is not None:
            info.append(f"每股收益(EPS): {fund['eps']:.2f} 元")
        if fund.get('bps') is not None:
            info.append(f"每股净资产(BPS): {fund['bps']:.2f} 元")
        
        # 财务数据
        if fund.get('revenue') is not None:
            revenue_str = f"营业收入: {fund['revenue']:.2f} 亿元"
            if fund.get('revenue_growth') is not None:
                revenue_str += f" (同比增长: {fund['revenue_growth']:.2f}%)"
            info.append(revenue_str)
        
        if fund.get('net_profit') is not None:
            profit_str = f"净利润: {fund['net_profit']:.2f} 亿元"
            if fund.get('profit_growth') is not None:
                profit_str += f" (同比增长: {fund['profit_growth']:.2f}%)"
            info.append(profit_str)
        
        if fund.get('total_assets') is not None:
            info.append(f"总资产: {fund['total_assets']:.2f} 亿元")
        if fund.get('net_assets') is not None:
            info.append(f"净资产: {fund['net_assets']:.2f} 亿元")
        if fund.get('shareholders_num') is not None:
            info.append(f"股东人数: {fund['shareholders_num']:,} 人")
        
        # 如果所有数据都是None，说明未获取到
        if all(fund.get(k) is None for k in ['pe_dynamic', 'pe_ttm', 'pb_ratio', 'ps_ratio', 'total_market_cap', 'roe', 'revenue']):
            info.append("基本面数据暂不可用")
        info.append("")
    
    # 行业对比数据
    if data_dict.get('industry_comparison'):
        ic = data_dict['industry_comparison']
        if ic.get('rank') is not None:
            info.append("【行业对比分析】")
            info.append(f"所属行业: {ic.get('industry_name', 'N/A')} ({ic.get('industry_code', 'N/A')})")
            info.append(f"行业排名: {ic.get('rank')}/{ic.get('total_count')}")
            
            if ic.get('stock_change') is not None:
                info.append(f"股票涨跌幅: {ic.get('stock_change')}%")
            if ic.get('industry_avg_change') is not None:
                info.append(f"行业平均涨跌幅: {ic.get('industry_avg_change'):.2f}%")
                
                # 计算相对表现
                if ic.get('stock_change') is not None and ic.get('industry_avg_change') is not None:
                    relative_perf = ic.get('stock_change') - ic.get('industry_avg_change')
                    perf_status = "跑赢行业" if relative_perf > 0 else "跑输行业"
                    info.append(f"相对行业表现: {relative_perf:+.2f}% ({perf_status})")
            
            if ic.get('top_5_stocks') and len(ic['top_5_stocks']) > 0:
                info.append("行业前5名:")
                for idx, stock in enumerate(ic['top_5_stocks'], 1):
                    change_str = f"{stock.get('change', 'N/A')}%"
                    info.append(f"  {idx}. {stock.get('name', 'N/A')} ({stock.get('code', 'N/A')}) - {change_str}")
            
            info.append("")
    
    return "\n".join(info)


def to_json(data_dict):
    """将数据转换为JSON格式"""
    def convert_df_to_dict(df):
        if df is None or len(df) == 0:
            return None
        records = df.to_dict('records')
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, pd.Timestamp):
                    record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, (pd.Timedelta, pd.Period)):
                    record[key] = str(value)
        return records
    
    result = {
        'code': data_dict['code'],
        'timestamp': data_dict['timestamp'],
        'realtime': data_dict['realtime'],
        'minute_5': convert_df_to_dict(data_dict['minute_5']),
        'minute_15': convert_df_to_dict(data_dict['minute_15']),
        'minute_30': convert_df_to_dict(data_dict['minute_30']),
        'timeline': convert_df_to_dict(data_dict['timeline']),
        'daily': convert_df_to_dict(data_dict['daily']),
        'sector_info': data_dict.get('sector_info', []),
        'money_flow': data_dict.get('money_flow', {}),
    }
    
    # 添加技术指标、基本面、行业对比数据
    if 'indicators' in data_dict:
        result['indicators'] = data_dict['indicators']
    
    if 'fundamental' in data_dict:
        result['fundamental'] = data_dict['fundamental']
    
    if 'industry_comparison' in data_dict:
        result['industry_comparison'] = data_dict['industry_comparison']
    
    # 添加计数字段
    result['daily_count'] = len(data_dict['daily']) if data_dict.get('daily') is not None else 0
    result['minute_5_count'] = len(data_dict['minute_5']) if data_dict.get('minute_5') is not None else 0
    result['minute_15_count'] = len(data_dict['minute_15']) if data_dict.get('minute_15') is not None else 0
    result['minute_30_count'] = len(data_dict['minute_30']) if data_dict.get('minute_30') is not None else 0
    result['timeline_count'] = len(data_dict['timeline']) if data_dict.get('timeline') is not None else 0
    
    return result


# ==================== Flask API 接口 ====================

