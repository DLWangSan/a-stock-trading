#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""技术指标计算模块"""

import pandas as pd
import numpy as np
import warnings
import time
from datetime import datetime
from data_fetchers import get_daily_kline, get_timeline_data, get_minute_kline, get_realtime_data, get_sector_info, get_money_flow, get_fundamental_data, get_industry_comparison
warnings.filterwarnings("ignore")

def calculate_ma(df, periods=[5, 10, 20, 30, 60]):
    """计算移动平均线（MA）"""
    if df is None or len(df) == 0 or 'close' not in df.columns:
        return df
    df = df.copy()
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period, min_periods=1).mean()
    return df


def calculate_ema(df, periods=[12, 26, 50]):
    """计算指数移动平均线（EMA）"""
    if df is None or len(df) == 0 or 'close' not in df.columns:
        return df
    df = df.copy()
    for period in periods:
        df[f'EMA{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df


def calculate_macd(df, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    if df is None or len(df) == 0 or 'close' not in df.columns:
        return df
    df = df.copy()
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    df['MACD_DIF'] = ema_fast - ema_slow
    df['MACD_DEA'] = df['MACD_DIF'].ewm(span=signal, adjust=False).mean()
    df['MACD'] = (df['MACD_DIF'] - df['MACD_DEA']) * 2
    return df


def calculate_rsi(df, period=14):
    """计算RSI相对强弱指标"""
    if df is None or len(df) == 0 or 'close' not in df.columns:
        return df
    df = df.copy()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    rs = gain / loss
    df[f'RSI{period}'] = 100 - (100 / (1 + rs))
    return df


def calculate_kdj(df, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    if df is None or len(df) == 0:
        return df
    if 'high' not in df.columns or 'low' not in df.columns or 'close' not in df.columns:
        return df
    df = df.copy()
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['KDJ_K'] = rsv.ewm(com=m1-1, adjust=False).mean()
    df['KDJ_D'] = df['KDJ_K'].ewm(com=m2-1, adjust=False).mean()
    df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']
    return df


def calculate_boll(df, period=20, std_dev=2):
    """计算布林带（BOLL）"""
    if df is None or len(df) == 0 or 'close' not in df.columns:
        return df
    df = df.copy()
    df['BOLL_MID'] = df['close'].rolling(window=period, min_periods=1).mean()
    std = df['close'].rolling(window=period, min_periods=1).std()
    df['BOLL_UPPER'] = df['BOLL_MID'] + (std * std_dev)
    df['BOLL_LOWER'] = df['BOLL_MID'] - (std * std_dev)
    return df


def calculate_obv(df):
    """计算OBV能量潮指标"""
    if df is None or len(df) == 0:
        return df
    if 'close' not in df.columns or 'volume' not in df.columns:
        return df
    df = df.copy()
    price_change = df['close'].diff()
    obv = (np.sign(price_change) * df['volume']).fillna(0)
    df['OBV'] = obv.cumsum()
    return df


def calculate_indicators(df, indicators=['MA', 'EMA', 'MACD', 'RSI', 'KDJ', 'BOLL', 'OBV']):
    """批量计算技术指标"""
    if df is None or len(df) == 0:
        return df
    result_df = df.copy()
    if 'MA' in indicators:
        result_df = calculate_ma(result_df, periods=[5, 10, 20, 30, 60])
    if 'EMA' in indicators:
        result_df = calculate_ema(result_df, periods=[12, 26, 50])
    if 'MACD' in indicators:
        result_df = calculate_macd(result_df)
    if 'RSI' in indicators:
        result_df = calculate_rsi(result_df, period=14)
    if 'KDJ' in indicators:
        result_df = calculate_kdj(result_df)
    if 'BOLL' in indicators:
        result_df = calculate_boll(result_df)
    if 'OBV' in indicators:
        result_df = calculate_obv(result_df)
    return result_df


# ==================== 数据整合函数 ====================

def get_comprehensive_data(code):
    """获取股票的综合数据"""
    result = {
        'code': code,
        'timestamp': datetime.now().isoformat(),
        'realtime': None,
        'minute_5': None,
        'minute_15': None,
        'minute_30': None,
        'timeline': None,
        'daily': None,
        'sector_info': None,  # 板块/行业信息
        'money_flow': None,   # 资金流向
        'fundamental': None,  # 基本面数据
        'industry_comparison': None,  # 行业对比数据
    }
    
    print(f"[API] 获取 {code} 实时行情...")
    result['realtime'] = get_realtime_data(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 5分钟K线...")
    result['minute_5'] = get_minute_kline(code, scale=5, datalen=240)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 15分钟K线...")
    result['minute_15'] = get_minute_kline(code, scale=15, datalen=160)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 30分钟K线...")
    result['minute_30'] = get_minute_kline(code, scale=30, datalen=80)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 分时数据...")
    result['timeline'] = get_timeline_data(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 日K线...")
    result['daily'] = get_daily_kline(code, count=240)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 板块/行业信息...")
    result['sector_info'] = get_sector_info(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 资金流向...")
    result['money_flow'] = get_money_flow(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 基本面数据...")
    result['fundamental'] = get_fundamental_data(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 行业对比数据...")
    result['industry_comparison'] = get_industry_comparison(code, sector_info=result.get('sector_info'))
    
    return result


def get_comprehensive_data_with_indicators(code):
    """获取股票的综合数据（包含技术指标）"""
    result = {
        'code': code,
        'timestamp': datetime.now().isoformat(),
        'realtime': None,
        'minute_5': None,
        'minute_15': None,
        'minute_30': None,
        'timeline': None,
        'daily': None,
        'indicators': None,  # 技术指标摘要
        'sector_info': None,  # 板块/行业信息
        'money_flow': None,   # 资金流向
        'fundamental': None,  # 基本面数据
        'industry_comparison': None,  # 行业对比数据
    }
    
    print(f"[API] 获取 {code} 实时行情...")
    result['realtime'] = get_realtime_data(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 5分钟K线...")
    result['minute_5'] = get_minute_kline(code, scale=5, datalen=240)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 15分钟K线...")
    result['minute_15'] = get_minute_kline(code, scale=15, datalen=160)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 30分钟K线...")
    result['minute_30'] = get_minute_kline(code, scale=30, datalen=80)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 分时数据...")
    result['timeline'] = get_timeline_data(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 日K线...")
    daily_df = get_daily_kline(code, count=240)
    if daily_df is not None and len(daily_df) > 0:
        print(f"[API] 计算 {code} 技术指标...")
        daily_df = calculate_indicators(daily_df)
        result['daily'] = daily_df
        
        # 提取最新技术指标摘要
        if len(daily_df) > 0:
            latest = daily_df.iloc[-1]
            indicators_summary = {}
            
            ma_cols = [col for col in daily_df.columns if col.startswith('MA') and not col.startswith('MACD')]
            if ma_cols:
                indicators_summary['MA'] = {col: float(latest[col]) for col in ma_cols if pd.notna(latest[col])}
            
            ema_cols = [col for col in daily_df.columns if col.startswith('EMA')]
            if ema_cols:
                indicators_summary['EMA'] = {col: float(latest[col]) for col in ema_cols if pd.notna(latest[col])}
            
            if 'MACD_DIF' in daily_df.columns and pd.notna(latest['MACD_DIF']):
                indicators_summary['MACD'] = {
                    'DIF': float(latest['MACD_DIF']),
                    'DEA': float(latest.get('MACD_DEA', 0)) if pd.notna(latest.get('MACD_DEA')) else 0,
                    'MACD': float(latest.get('MACD', 0)) if pd.notna(latest.get('MACD')) else 0
                }
            
            if 'RSI14' in daily_df.columns and pd.notna(latest['RSI14']):
                indicators_summary['RSI'] = float(latest['RSI14'])
            
            if 'KDJ_K' in daily_df.columns and pd.notna(latest['KDJ_K']):
                indicators_summary['KDJ'] = {
                    'K': float(latest['KDJ_K']),
                    'D': float(latest.get('KDJ_D', 0)) if pd.notna(latest.get('KDJ_D')) else 0,
                    'J': float(latest.get('KDJ_J', 0)) if pd.notna(latest.get('KDJ_J')) else 0
                }
            
            if 'BOLL_UPPER' in daily_df.columns and pd.notna(latest['BOLL_UPPER']):
                indicators_summary['BOLL'] = {
                    'upper': float(latest['BOLL_UPPER']),
                    'mid': float(latest.get('BOLL_MID', 0)) if pd.notna(latest.get('BOLL_MID')) else 0,
                    'lower': float(latest.get('BOLL_LOWER', 0)) if pd.notna(latest.get('BOLL_LOWER')) else 0
                }
            
            if 'OBV' in daily_df.columns and pd.notna(latest['OBV']):
                indicators_summary['OBV'] = float(latest['OBV'])
            
            result['indicators'] = indicators_summary
    else:
        result['daily'] = None
    
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 板块/行业信息...")
    result['sector_info'] = get_sector_info(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 资金流向...")
    result['money_flow'] = get_money_flow(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 基本面数据...")
    result['fundamental'] = get_fundamental_data(code)
    time.sleep(0.1)
    
    print(f"[API] 获取 {code} 行业对比数据...")
    result['industry_comparison'] = get_industry_comparison(code, sector_info=result.get('sector_info'))
    
    return result
