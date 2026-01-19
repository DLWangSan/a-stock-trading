#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据获取模块 - 从新浪和东方财富API获取股票数据"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import traceback
import re
import json
from utils import get_stock_code_format, get_secid

# ==================== 数据获取函数 ====================

def get_realtime_data(code):
    """获取实时行情数据"""
    try:
        sina_code = get_stock_code_format(code)
        url = f"http://hq.sinajs.cn/list={sina_code}"
        
        response = requests.get(url, timeout=5, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        })
        response.encoding = 'gbk'
        
        if response.status_code == 200:
            data_str = response.text
            if '=' in data_str:
                data_part = data_str.split('=')[1].strip().strip('"').strip(';')
                fields = data_part.split(',')
                
                if len(fields) >= 32:
                    change_percent = None
                    if fields[2] and fields[3]:
                        try:
                            yesterday_close = float(fields[2])
                            current_price = float(fields[3])
                            change_percent = ((current_price - yesterday_close) / yesterday_close) * 100
                        except:
                            pass
                    
                    return {
                        'code': code,
                        'name': fields[0],
                        'open': float(fields[1]) if fields[1] else None,
                        'yesterday_close': float(fields[2]) if fields[2] else None,
                        'current_price': float(fields[3]) if fields[3] else None,
                        'high': float(fields[4]) if fields[4] else None,
                        'low': float(fields[5]) if fields[5] else None,
                        'volume': float(fields[8]) if fields[8] else None,
                        'amount': float(fields[9]) if fields[9] else None,
                        'date': fields[30] if len(fields) > 30 else None,
                        'time': fields[31] if len(fields) > 31 else None,
                        'change_percent': change_percent,
                        'bid1_volume': float(fields[10]) if len(fields) > 10 and fields[10] else None,
                        'bid1_price': float(fields[11]) if len(fields) > 11 and fields[11] else None,
                        'bid2_volume': float(fields[12]) if len(fields) > 12 and fields[12] else None,
                        'bid2_price': float(fields[13]) if len(fields) > 13 and fields[13] else None,
                        'bid3_volume': float(fields[14]) if len(fields) > 14 and fields[14] else None,
                        'bid3_price': float(fields[15]) if len(fields) > 15 and fields[15] else None,
                        'bid4_volume': float(fields[16]) if len(fields) > 16 and fields[16] else None,
                        'bid4_price': float(fields[17]) if len(fields) > 17 and fields[17] else None,
                        'bid5_volume': float(fields[18]) if len(fields) > 18 and fields[18] else None,
                        'bid5_price': float(fields[19]) if len(fields) > 19 and fields[19] else None,
                        'ask1_volume': float(fields[20]) if len(fields) > 20 and fields[20] else None,
                        'ask1_price': float(fields[21]) if len(fields) > 21 and fields[21] else None,
                        'ask2_volume': float(fields[22]) if len(fields) > 22 and fields[22] else None,
                        'ask2_price': float(fields[23]) if len(fields) > 23 and fields[23] else None,
                        'ask3_volume': float(fields[24]) if len(fields) > 24 and fields[24] else None,
                        'ask3_price': float(fields[25]) if len(fields) > 25 and fields[25] else None,
                        'ask4_volume': float(fields[26]) if len(fields) > 26 and fields[26] else None,
                        'ask4_price': float(fields[27]) if len(fields) > 27 and fields[27] else None,
                        'ask5_volume': float(fields[28]) if len(fields) > 28 and fields[28] else None,
                        'ask5_price': float(fields[29]) if len(fields) > 29 and fields[29] else None,
                    }
        return None
    except Exception as e:
        print(f"[API] 获取实时数据失败 {code}: {e}")
        traceback.print_exc()
        return None


def get_minute_kline(code, scale=5, datalen=240):
    """获取分钟K线数据"""
    try:
        sina_code = get_stock_code_format(code)
        url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            'symbol': sina_code,
            'scale': scale,
            'ma': 'no',
            'datalen': min(datalen, 1023)
        }
        
        response = requests.get(url, params=params, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        })
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                if 'day' in df.columns:
                    df['datetime'] = pd.to_datetime(df['day'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                if 'datetime' in df.columns:
                    df = df.sort_values('datetime').reset_index(drop=True)
                return df
        return None
    except Exception as e:
        print(f"[API] 获取分钟K线失败 {code} scale={scale}: {e}")
        traceback.print_exc()
        return None


def get_timeline_data(code):
    """获取分时数据（每分钟的数据点）"""
    try:
        sina_code = get_stock_code_format(code)
        
        # 方法1：尝试使用新浪分时数据接口
        url1 = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getStockTimeLine"
        params1 = {'symbol': sina_code, 'scale': 1}
        
        try:
            response = requests.get(url1, params=params1, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://finance.sina.com.cn'
            })
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    if 'time' in df.columns:
                        try:
                            df['datetime'] = pd.to_datetime(df['time'], unit='s', errors='coerce')
                        except:
                            try:
                                df['datetime'] = pd.to_datetime(df['time'], errors='coerce')
                            except:
                                df['datetime'] = pd.date_range(end=datetime.now(), periods=len(df), freq='1min')
                    
                    for col in ['price', 'volume', 'amount', 'open', 'high', 'low', 'close']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    if 'datetime' in df.columns:
                        df = df.sort_values('datetime').reset_index(drop=True)
                    
                    if len(df) > 0:
                        return df
        except Exception as e:
            print(f"[API] 方法1获取分时数据失败: {e}")
        
        # 方法2：从5分钟K线数据中提取（作为备选）
        print(f"[API] 尝试从5分钟K线提取分时数据...")
        minute_5_df = get_minute_kline(code, scale=5, datalen=48)
        if minute_5_df is not None and len(minute_5_df) > 0:
            timeline_list = []
            for idx, row in minute_5_df.iterrows():
                if 'datetime' in row and 'close' in row:
                    base_time = row['datetime']
                    price = row['close']
                    volume = row.get('volume', 0) / 5 if 'volume' in row else 0
                    
                    for i in range(5):
                        timeline_list.append({
                            'datetime': base_time + pd.Timedelta(minutes=i),
                            'price': price,
                            'volume': volume,
                            'amount': price * volume if volume > 0 else 0
                        })
            
            if timeline_list:
                return pd.DataFrame(timeline_list)
        
        return None
    except Exception as e:
        print(f"[API] 获取分时数据失败 {code}: {e}")
        traceback.print_exc()
        return None


def get_daily_kline(code, count=240):
    """获取日K线数据"""
    try:
        sina_code = get_stock_code_format(code)
        url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            'symbol': sina_code,
            'scale': 240,
            'ma': 'no',
            'datalen': min(count, 1023)
        }
        
        response = requests.get(url, params=params, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        })
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                if 'day' in df.columns:
                    df['date'] = pd.to_datetime(df['day'], format='%Y-%m-%d', errors='coerce')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                if 'date' in df.columns:
                    df = df.sort_values('date').reset_index(drop=True)
                return df
        return None
    except Exception as e:
        print(f"[API] 获取日K线失败 {code}: {e}")
        traceback.print_exc()
        return None


def get_sector_info(code):
    """
    获取股票的板块/行业信息
    尝试从多个来源获取
    """
    try:
        sectors = []
        
        # 方法1：从新浪股票基本信息页面获取
        try:
            url = f"http://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpInfo/stockid/{code}.phtml"
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://finance.sina.com.cn'
            })
            response.encoding = 'gbk'
            
            if response.status_code == 200:
                content = response.text
                # 查找行业相关关键词
                industry_patterns = [
                    r'所属行业[：:]\s*([^<\n\r]+)',
                    r'行业分类[：:]\s*([^<\n\r]+)',
                    r'行业[：:]\s*([^<\n\r]+)',
                    r'<td[^>]*>所属行业</td>\s*<td[^>]*>([^<]+)</td>',
                    r'<td[^>]*>行业分类</td>\s*<td[^>]*>([^<]+)</td>',
                ]
                for pattern in industry_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            sector = match.strip()
                            # 清理HTML标签和特殊字符
                            sector = re.sub(r'<[^>]+>', '', sector)
                            sector = sector.strip()
                            if sector and sector not in sectors and len(sector) < 50 and sector != 'N/A':
                                sectors.append(sector)
                                print(f"[API] 找到板块信息: {sector}")
        except Exception as e:
            print(f"[API] 方法1获取板块信息失败: {e}")
        
        # 方法2：尝试从新浪概念板块接口获取
        try:
            sina_code = get_stock_code_format(code)
            # 尝试获取概念板块
            url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getStockNode"
            params = {'symbol': sina_code}
            response = requests.get(url, params=params, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://finance.sina.com.cn'
            })
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                name = item.get('name', item.get('板块名称', ''))
                                if name and name not in sectors:
                                    sectors.append(name)
                except:
                    pass
        except Exception as e:
            print(f"[API] 方法2获取板块信息失败: {e}")
        
        if not sectors:
            print(f"[API] 无法获取股票 {code} 的板块信息")
        
        return sectors
    except Exception as e:
        print(f"[API] 获取板块信息失败 {code}: {e}")
        traceback.print_exc()
        return []


def get_money_flow(code):
    """
    获取股票的资金流向数据（今日数据，使用东方财富ulist.np接口）
    包括：主力净流入、超大单、大单、中单、小单的净流入/流出及净比
    """
    try:
        secid = get_secid(code)
        
        url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            'fltt': '2',
            'secids': secid,
            'fields': 'f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f64,f65,f70,f71,f76,f77,f82,f83',
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
        }
        
        result = {
            'code': code,
            'main_net_inflow': None,  # 主力净流入（万元）
            'main_net_ratio': None,  # 主力净比（%）
            'super_large_net_inflow': None,  # 超大单净流入（万元）
            'super_large_net_ratio': None,  # 超大单净比（%）
            'super_large_inflow': None,  # 超大单流入（万元）
            'super_large_outflow': None,  # 超大单流出（万元）
            'large_net_inflow': None,  # 大单净流入（万元）
            'large_net_ratio': None,  # 大单净比（%）
            'large_inflow': None,  # 大单流入（万元）
            'large_outflow': None,  # 大单流出（万元）
            'medium_net_inflow': None,  # 中单净流入（万元）
            'medium_net_ratio': None,  # 中单净比（%）
            'medium_inflow': None,  # 中单流入（万元）
            'medium_outflow': None,  # 中单流出（万元）
            'small_net_inflow': None,  # 小单净流入（万元）
            'small_net_ratio': None,  # 小单净比（%）
            'small_inflow': None,  # 小单流入（万元）
            'small_outflow': None,  # 小单流出（万元）
        }
        
        try:
            response = requests.get(url, params=params, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://data.eastmoney.com'
            })
            
            if response.status_code == 200:
                text = response.text
                
                # 提取JSON（可能是JSONP格式）
                if '(' in text and '{' in text:
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        data = json.loads(json_str)
                    else:
                        data = json.loads(text)
                else:
                    data = json.loads(text)
                
                if isinstance(data, dict) and 'data' in data:
                    stock_data = data['data']
                    
                    if stock_data and 'diff' in stock_data and len(stock_data['diff']) > 0:
                        item = stock_data['diff'][0]  # 取第一个股票数据
                        
                        # 字段映射
                        field_mapping = {
                            'f62': 'main_net_inflow',
                            'f184': 'main_net_ratio',
                            'f66': 'super_large_net_inflow',
                            'f69': 'super_large_net_ratio',
                            'f64': 'super_large_inflow',
                            'f65': 'super_large_outflow',
                            'f72': 'large_net_inflow',
                            'f75': 'large_net_ratio',
                            'f70': 'large_inflow',
                            'f71': 'large_outflow',
                            'f78': 'medium_net_inflow',
                            'f81': 'medium_net_ratio',
                            'f76': 'medium_inflow',
                            'f77': 'medium_outflow',
                            'f84': 'small_net_inflow',
                            'f87': 'small_net_ratio',
                            'f82': 'small_inflow',
                            'f83': 'small_outflow',
                        }
                        
                        for field, key in field_mapping.items():
                            if field in item and item[field] is not None:
                                value = item[field]
                                if isinstance(value, (int, float)):
                                    if 'ratio' in key:
                                        # 百分比字段，直接使用
                                        result[key] = value
                                    else:
                                        # 金额字段，转换为万元
                                        result[key] = value / 10000
                        
                        if any(v is not None for v in result.values() if v != code):
                            print(f"[API] 成功获取资金流向数据（今日）")
                        else:
                            print(f"[API] 未找到资金流向字段")
                    else:
                        print(f"[API] 资金流向数据为空")
                else:
                    print(f"[API] 资金流向API返回数据格式异常")
        except Exception as e:
            print(f"[API] 获取资金流向失败: {e}")
            traceback.print_exc()
        
        return result
    except Exception as e:
        print(f"[API] 获取资金流向失败 {code}: {e}")
        traceback.print_exc()
        return {
            'code': code,
            'main_net_inflow': None,
            'main_net_ratio': None,
            'super_large_net_inflow': None,
            'super_large_net_ratio': None,
            'super_large_inflow': None,
            'super_large_outflow': None,
            'large_net_inflow': None,
            'large_net_ratio': None,
            'large_inflow': None,
            'large_outflow': None,
            'medium_net_inflow': None,
            'medium_net_ratio': None,
            'medium_inflow': None,
            'medium_outflow': None,
            'small_net_inflow': None,
            'small_net_ratio': None,
            'small_inflow': None,
            'small_outflow': None,
        }


def get_money_flow_history(code, days=60):
    """
    获取股票的历史资金流向数据（日线）
    
    Args:
        code: 股票代码
        days: 获取天数，0表示获取所有数据
    
    Returns:
        list: 历史资金流向数据列表，每个元素包含日期、各类型净流入、净比等
    """
    try:
        secid = get_secid(code)
        
        url = "http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        params = {
            'lmt': str(days),  # 0表示获取所有数据
            'klt': '101',  # 101表示日线
            'fields1': 'f1,f2,f3,f7',  # 基础字段
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',  # 资金流向字段
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
            'secid': secid,
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://data.eastmoney.com'
            })
            
            if response.status_code == 200:
                text = response.text
                
                # 提取JSON（可能是JSONP格式）
                if '(' in text and '{' in text:
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        data = json.loads(json_str)
                    else:
                        data = json.loads(text)
                else:
                    data = json.loads(text)
                
                if isinstance(data, dict) and 'data' in data and data['data']:
                    klines = data['data'].get('klines', [])
                    
                    result = []
                    for kline in klines:
                        # kline格式：日期,主力净流入,超大单净流入,大单净流入,中单净流入,小单净流入,主力净比,超大单净比,大单净比,中单净比,小单净比,收盘价,涨跌幅,?,?
                        fields = kline.split(',')
                        if len(fields) >= 12:
                            try:
                                record = {
                                    'date': fields[0],
                                    'main_net_inflow': float(fields[1]) / 10000 if fields[1] else None,  # 万元
                                    'super_large_net_inflow': float(fields[2]) / 10000 if fields[2] else None,
                                    'large_net_inflow': float(fields[3]) / 10000 if fields[3] else None,
                                    'medium_net_inflow': float(fields[4]) / 10000 if fields[4] else None,
                                    'small_net_inflow': float(fields[5]) / 10000 if fields[5] else None,
                                    'main_net_ratio': float(fields[6]) if fields[6] else None,  # %
                                    'super_large_net_ratio': float(fields[7]) if fields[7] else None,
                                    'large_net_ratio': float(fields[8]) if fields[8] else None,
                                    'medium_net_ratio': float(fields[9]) if fields[9] else None,
                                    'small_net_ratio': float(fields[10]) if fields[10] else None,
                                    'close': float(fields[11]) if fields[11] else None,  # 收盘价
                                    'change_percent': float(fields[12]) if len(fields) > 12 and fields[12] else None,  # 涨跌幅
                                }
                                result.append(record)
                            except (ValueError, IndexError) as e:
                                continue
                    
                    print(f"[API] 成功获取历史资金流向数据，共 {len(result)} 条")
                    return result
                else:
                    print(f"[API] 历史资金流向API返回数据格式异常")
        except Exception as e:
            print(f"[API] 获取历史资金流向失败: {e}")
            traceback.print_exc()
        
        return []
    except Exception as e:
        print(f"[API] 获取历史资金流向失败 {code}: {e}")
        traceback.print_exc()
        return []


def get_money_flow_realtime_kline(code, klt=1, lmt=0):
    """
    获取股票的实时资金流向分钟线数据
    
    Args:
        code: 股票代码
        klt: K线类型，1=1分钟，5=5分钟
        lmt: 限制条数，0表示获取所有数据
    
    Returns:
        list: 分钟线资金流向数据列表
    """
    try:
        secid = get_secid(code)
        
        url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        params = {
            'lmt': str(lmt),
            'klt': str(klt),
            'fields1': 'f1,f2,f3,f7',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
            'secid': secid,
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://data.eastmoney.com'
            })
            
            if response.status_code == 200:
                text = response.text
                
                # 提取JSON（可能是JSONP格式）
                if '(' in text and '{' in text:
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        data = json.loads(json_str)
                    else:
                        data = json.loads(text)
                else:
                    data = json.loads(text)
                
                if isinstance(data, dict) and 'data' in data and data['data']:
                    klines = data['data'].get('klines', [])
                    
                    result = []
                    for kline in klines:
                        # kline格式：时间,主力净流入,超大单净流入,大单净流入,中单净流入,小单净流入
                        fields = kline.split(',')
                        if len(fields) >= 6:
                            try:
                                record = {
                                    'time': fields[0],
                                    'main_net_inflow': float(fields[1]) / 10000 if fields[1] else None,  # 万元
                                    'super_large_net_inflow': float(fields[2]) / 10000 if fields[2] else None,
                                    'large_net_inflow': float(fields[3]) / 10000 if fields[3] else None,
                                    'medium_net_inflow': float(fields[4]) / 10000 if fields[4] else None,
                                    'small_net_inflow': float(fields[5]) / 10000 if fields[5] else None,
                                }
                                result.append(record)
                            except (ValueError, IndexError) as e:
                                continue
                    
                    print(f"[API] 成功获取实时资金流向分钟线数据，共 {len(result)} 条")
                    return result
                else:
                    print(f"[API] 实时资金流向分钟线API返回数据格式异常")
        except Exception as e:
            print(f"[API] 获取实时资金流向分钟线失败: {e}")
            traceback.print_exc()
        
        return []
    except Exception as e:
        print(f"[API] 获取实时资金流向分钟线失败 {code}: {e}")
        traceback.print_exc()
        return []


# ==================== 基本面数据获取函数 ====================

def get_fundamental_data(code):
    """
    获取股票的基本面数据（使用东方财富API）
    包括：估值指标（PE、PB、PS等）、财务指标（ROE、ROA等）、财务数据（营收、利润等）
    """
    try:
        secid = get_secid(code)
        
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        
        # 选择关键基本面字段
        fields = "f57,f58,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f60,f84,f85,f86,f87,f92,f116,f117,f162,f167,f168,f169,f170,f171,f173,f180,f181,f183,f184,f185,f186,f187,f188,f189"
        
        params = {
            'invt': '2',
            'fltt': '1',
            'fields': fields,
            'secid': secid,
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b'
        }
        
        result = {
            'code': code,
            'name': None,
            # 估值指标
            'pe_dynamic': None,  # 市盈率(动态)
            'pe_ttm': None,  # 市盈率(TTM)
            'pb_ratio': None,  # 市净率
            'ps_ratio': None,  # 市销率
            'pcf_ratio': None,  # 市现率
            # 市值和股本
            'total_market_cap': None,  # 总市值(亿元)
            'circulating_market_cap': None,  # 流通市值(亿元)
            'total_shares': None,  # 总股本(亿股)
            'circulating_shares': None,  # 流通股本(亿股)
            # 财务指标
            'roe': None,  # 净资产收益率(%)
            'eps': None,  # 每股收益(元)
            'bps': None,  # 每股净资产(元)
            # 财务数据
            'revenue': None,  # 营业收入(亿元)
            'revenue_growth': None,  # 营业收入同比增长(%)
            'net_profit': None,  # 净利润(亿元)
            'profit_growth': None,  # 净利润同比增长(%)
            'total_assets': None,  # 总资产(亿元)
            'net_assets': None,  # 净资产(亿元)
            'shareholders_num': None,  # 股东人数
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://quote.eastmoney.com'
            })
            
            if response.status_code == 200:
                text = response.text
                
                # 提取JSON（可能是JSONP格式）
                if '(' in text and '{' in text:
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        data = json.loads(json_str)
                    else:
                        data = json.loads(text)
                else:
                    data = json.loads(text)
                
                if isinstance(data, dict) and 'data' in data:
                    d = data['data']
                    
                    result['name'] = d.get('f58')
                    
                    # 估值指标
                    if d.get('f92') is not None:
                        result['pe_dynamic'] = d['f92']
                    if d.get('f171') is not None and isinstance(d['f171'], (int, float)):
                        result['pe_ttm'] = d['f171']
                    if d.get('f162') is not None and isinstance(d['f162'], (int, float)) and d['f162'] > 0:
                        result['pb_ratio'] = d['f162'] / 100  # 市净率需要除以100
                    if d.get('f167') is not None and isinstance(d['f167'], (int, float)) and d['f167'] > 0:
                        result['ps_ratio'] = d['f167'] / 100  # 市销率需要除以100
                    if d.get('f168') is not None and isinstance(d['f168'], (int, float)) and d['f168'] > 0:
                        result['pcf_ratio'] = d['f168'] / 100  # 市现率需要除以100
                    
                    # 市值和股本
                    if d.get('f116') is not None:
                        result['total_market_cap'] = d['f116'] / 100000000  # 元转亿元
                    if d.get('f117') is not None:
                        result['circulating_market_cap'] = d['f117'] / 100000000  # 元转亿元
                    if d.get('f84') is not None:
                        result['total_shares'] = d['f84'] / 10000  # 万股转亿股
                    if d.get('f85') is not None:
                        result['circulating_shares'] = d['f85'] / 10000  # 万股转亿股
                    
                    # 财务指标
                    if d.get('f173') is not None:
                        result['roe'] = d['f173']
                    if d.get('f180') is not None and isinstance(d['f180'], (int, float)):
                        # EPS可能需要除以100，但先保持原值，根据实际情况调整
                        result['eps'] = d['f180'] / 100 if abs(d['f180']) > 10 else d['f180']
                    if d.get('f181') is not None and isinstance(d['f181'], (int, float)):
                        # BPS可能需要除以100，但先保持原值，根据实际情况调整
                        result['bps'] = d['f181'] / 100 if abs(d['f181']) > 1000 else d['f181']
                    
                    # 财务数据
                    if d.get('f183') is not None:
                        result['revenue'] = d['f183'] / 10000  # 万元转亿元
                    if d.get('f184') is not None:
                        result['revenue_growth'] = d['f184']
                    if d.get('f185') is not None:
                        result['net_profit'] = d['f185'] / 10000  # 万元转亿元
                    if d.get('f186') is not None:
                        result['profit_growth'] = d['f186']
                    if d.get('f187') is not None:
                        result['total_assets'] = d['f187'] / 10000  # 万元转亿元
                    if d.get('f188') is not None:
                        result['net_assets'] = d['f188'] / 10000  # 万元转亿元
                    if d.get('f189') is not None:
                        result['shareholders_num'] = int(d['f189'])
                    
                    if any(v is not None for k, v in result.items() if k != 'code'):
                        print(f"[API] 成功获取基本面数据")
                else:
                    print(f"[API] 基本面数据API返回数据格式异常")
        except Exception as e:
            print(f"[API] 获取基本面数据失败: {e}")
            traceback.print_exc()
        
        return result
    except Exception as e:
        print(f"[API] 获取基本面数据失败 {code}: {e}")
        traceback.print_exc()
        return {
            'code': code,
            'name': None,
            'pe_dynamic': None,
            'pe_ttm': None,
            'pb_ratio': None,
            'ps_ratio': None,
            'pcf_ratio': None,
            'total_market_cap': None,
            'circulating_market_cap': None,
            'total_shares': None,
            'circulating_shares': None,
            'roe': None,
            'eps': None,
            'bps': None,
            'revenue': None,
            'revenue_growth': None,
            'net_profit': None,
            'profit_growth': None,
            'total_assets': None,
            'net_assets': None,
            'shareholders_num': None,
        }


# ==================== 行业对比数据获取函数 ====================

def get_industry_comparison(code, sector_info=None):
    """
    获取股票的行业对比数据（使用东方财富API）
    包括：行业排名、板块平均涨跌幅、板块内前5名等
    
    Args:
        code: 股票代码
        sector_info: 可选的板块信息列表
    """
    try:
        secid = get_secid(code)
        
        result = {
            'code': code,
            'industry_code': None,
            'industry_name': None,
            'rank': None,  # 在行业中的排名
            'total_count': None,  # 行业总股票数
            'stock_change': None,  # 股票涨跌幅
            'industry_avg_change': None,  # 行业平均涨跌幅
            'top_5_stocks': [],  # 行业前5名
        }
        
        # 方法1：使用slist接口获取股票所属的行业板块代码（推荐方法，快速高效）
        # 这个接口会同时返回股票信息和所属板块信息，f13=90表示板块类型
        try:
            url1 = "https://push2.eastmoney.com/api/qt/slist/get"
            params1 = {
                'fltt': '1',
                'invt': '2',
                'fields': 'f12,f13,f14,f3,f152,f4,f1,f2,f20,f58',
                'secid': secid,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'pn': '1',
                'np': '1',
                'spt': '1'
            }
            
            response1 = requests.get(url1, params=params1, timeout=8, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://quote.eastmoney.com'
            })
            
            if response1.status_code == 200:
                text1 = response1.text
                if '(' in text1 and '{' in text1:
                    match1 = re.search(r'\{.*\}', text1, re.DOTALL)
                    if match1:
                        data1 = json.loads(match1.group(0))
                    else:
                        data1 = json.loads(text1)
                else:
                    data1 = json.loads(text1)
                
                if isinstance(data1, dict) and 'data' in data1 and 'diff' in data1['data']:
                    items = data1['data']['diff']
                    
                    # 查找板块信息（f13=90表示板块类型）
                    block_code = None
                    block_name = None
                    for item in items:
                        if item.get('f13') == 90:  # 90表示板块
                            block_code = item.get('f12')  # 板块代码，如BK0546
                            block_name = item.get('f14')  # 板块名称，如"玻璃玻纤"
                            break
                    
                    if block_code and block_code.startswith('BK'):
                        # 找到了板块代码，现在获取该板块的所有股票和排名
                        url2 = "https://push2.eastmoney.com/api/qt/clist/get"
                        params2 = {
                            'np': '1',
                            'fltt': '1',
                            'invt': '2',
                            'fs': f'b:{block_code}+f:!18',
                            'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f58',
                            'fid': 'f3',  # 按涨跌幅排序
                            'pn': '1',
                            'pz': '200',
                            'po': '1',
                            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                            'dect': '1'
                        }
                        
                        response2 = requests.get(url2, params=params2, timeout=8, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Referer': 'http://quote.eastmoney.com'
                        })
                        
                        if response2.status_code == 200:
                            text2 = response2.text
                            if '(' in text2 and '{' in text2:
                                match2 = re.search(r'\{.*\}', text2, re.DOTALL)
                                if match2:
                                    data2 = json.loads(match2.group(0))
                                else:
                                    data2 = json.loads(text2)
                            else:
                                data2 = json.loads(text2)
                            
                            if isinstance(data2, dict) and 'data' in data2 and 'diff' in data2['data']:
                                stocks = data2['data']['diff']
                                
                                if stocks:
                                    # 查找目标股票
                                    target_code = code
                                    for idx, stock in enumerate(stocks, 1):
                                        if stock.get('f12') == target_code:
                                            result['industry_code'] = block_code
                                            result['industry_name'] = block_name
                                            result['rank'] = idx
                                            result['total_count'] = len(stocks)
                                            result['stock_change'] = stock.get('f3')
                                            
                                            # 计算板块平均涨跌幅
                                            total_change = sum(float(s.get('f3', 0)) for s in stocks if s.get('f3') and isinstance(s.get('f3'), (int, float)))
                                            result['industry_avg_change'] = total_change / len(stocks) if stocks else 0
                                            
                                            # 获取前5名
                                            result['top_5_stocks'] = [
                                                {
                                                    'code': s.get('f12'),
                                                    'name': s.get('f14'),
                                                    'change': s.get('f3'),
                                                    'price': s.get('f2')
                                                }
                                                for s in stocks[:5]
                                            ]
                                            
                                            print(f"[API] 成功获取行业对比数据: {block_name}板块({block_code})，排名 {idx}/{len(stocks)}")
                                            return result
        except Exception as e:
            print(f"[API] 方法1获取行业对比数据失败: {e}")
            traceback.print_exc()
        
        # 方法2：如果方法1失败，尝试常见行业板块（作为备用）
        print(f"[API] 方法1未找到股票 {code} 的行业板块，尝试备用方法...")
        industry_blocks = {
            # 金融类
            'BK0475': '银行',
            'BK0473': '保险',
            'BK0474': '证券',
            'BK0476': '多元金融',
            # 科技类
            'BK0727': '电子',
            'BK0728': '计算机',
            'BK0729': '通信',
            'BK0730': '传媒',
            'BK0731': '软件服务',
            # 制造业
            'BK0451': '机械设备',
            'BK0452': '汽车',
            'BK0453': '电气设备',
            'BK0454': '化工',
            'BK0455': '钢铁',
            'BK0456': '有色金属',
            'BK0457': '建筑材料',
            'BK0458': '建筑装饰',
            'BK0459': '轻工制造',
            'BK0460': '纺织服装',
            # 消费类
            'BK0438': '食品饮料',
            'BK0439': '农林牧渔',
            'BK0440': '商业贸易',
            'BK0441': '休闲服务',
            'BK0442': '家用电器',
            # 医药类
            'BK0737': '医药生物',
            'BK0738': '医疗器械',
            # 能源类
            'BK0468': '采掘',
            'BK0469': '公用事业',
            'BK0470': '交通运输',
            # 房地产
            'BK0451': '房地产',
            # 其他
            'BK0471': '国防军工',
            'BK0472': '综合',
        }
        
        # 尝试常见行业板块，找到股票所属的板块
        for block_code, block_name in industry_blocks.items():
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'np': '1',
                'fltt': '1',
                'invt': '2',
                'fs': f'b:{block_code}+f:!18',
                'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f58',
                'fid': 'f3',  # 按涨跌幅排序
                'pn': '1',
                'pz': '200',  # 增加获取数量，确保能找到股票
                'po': '1',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'dect': '1'
            }
            
            try:
                response = requests.get(url, params=params, timeout=8, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'http://quote.eastmoney.com'
                })
                
                if response.status_code == 200:
                    text = response.text
                    if '(' in text and '{' in text:
                        match = re.search(r'\{.*\}', text, re.DOTALL)
                        if match:
                            data = json.loads(match.group(0))
                        else:
                            data = json.loads(text)
                    else:
                        data = json.loads(text)
                    
                    if isinstance(data, dict) and 'data' in data and 'diff' in data['data']:
                        stocks = data['data']['diff']
                        
                        if not stocks or len(stocks) == 0:
                            continue
                        
                        # 查找目标股票
                        target_code = code
                        for idx, stock in enumerate(stocks, 1):
                            if stock.get('f12') == target_code:
                                result['industry_code'] = block_code
                                result['industry_name'] = block_name
                                result['rank'] = idx
                                result['total_count'] = len(stocks)
                                result['stock_change'] = stock.get('f3')
                                
                                # 计算板块平均涨跌幅
                                total_change = sum(float(s.get('f3', 0)) for s in stocks if s.get('f3') and isinstance(s.get('f3'), (int, float)))
                                result['industry_avg_change'] = total_change / len(stocks) if stocks else 0
                                
                                # 获取前5名
                                result['top_5_stocks'] = [
                                    {
                                        'code': s.get('f12'),
                                        'name': s.get('f14'),
                                        'change': s.get('f3'),
                                        'price': s.get('f2')
                                    }
                                    for s in stocks[:5]
                                ]
                                
                                print(f"[API] 成功获取行业对比数据: {block_name}板块，排名 {idx}/{len(stocks)}")
                                return result
            except Exception as e:
                # 如果某个板块查询失败，继续尝试下一个
                continue
        
        print(f"[API] 未找到股票 {code} 的行业排名数据")
        return result
    except Exception as e:
        print(f"[API] 获取行业对比数据失败 {code}: {e}")
        traceback.print_exc()
        return {
            'code': code,
            'industry_code': None,
            'industry_name': None,
            'rank': None,
            'total_count': None,
            'stock_change': None,
            'industry_avg_change': None,
            'top_5_stocks': [],
        }


# ==================== 舆情数据获取函数 ====================

def get_news_from_stock(code, days=7):
    """
    获取股票相关新闻
    
    Args:
        code: 股票代码
        days: 获取最近几天的新闻，默认7天
    
    Returns:
        list: 新闻列表
    """
    try:
        # 根据股票代码获取secid格式
        code_str = str(code).strip()
        if code_str.startswith('6'):
            secid = f"1.{code_str}"  # 上海A股
        elif code_str.startswith(('0', '3')):
            secid = f"0.{code_str}"  # 深圳A股
        else:
            secid = f"1.{code_str}"  # 默认上海
        
        url = "https://np-listapi.eastmoney.com/comm/web/getListInfo"
        params = {
            'cfh': '1',
            'client': 'web',
            'mTypeAndCode': secid,
            'type': '1',  # 1=新闻
            'pageSize': '50'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'https://quote.eastmoney.com/sh{code}.html' if code.startswith('6') else f'https://quote.eastmoney.com/sz{code}.html',
            'Accept': '*/*'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = json.loads(response.text)
            if isinstance(data, dict) and 'data' in data and 'list' in data['data']:
                items = data['data']['list']
                news_list = []
                for item in items:
                    if isinstance(item, dict):
                        news_item = {
                            'title': item.get('Art_Title', ''),
                            'url': item.get('Art_Url', ''),
                            'summary': '',  # 这个API不提供摘要
                            'source': '东方财富',
                            'time': item.get('Art_ShowTime', ''),
                            'type': 'news'
                        }
                        if news_item['title']:
                            news_list.append(news_item)
                
                # 过滤指定天数内的新闻
                if days > 0:
                    filtered_news = []
                    today = datetime.now().date()
                    for news in news_list:
                        try:
                            if news.get('time'):
                                news_time = datetime.strptime(news['time'], '%Y-%m-%d %H:%M:%S')
                                news_date = news_time.date()
                                days_ago_date = today - timedelta(days=days)
                                if news_date >= days_ago_date:
                                    filtered_news.append(news)
                            else:
                                filtered_news.append(news)
                        except:
                            filtered_news.append(news)  # 解析失败也保留
                    news_list = filtered_news
                
                return news_list
        
        return []
    except Exception as e:
        return []


def get_guba_posts(code, latest_count=10, hot_count=10):
    """
    获取股吧帖子（最新+热门）
    
    Args:
        code: 股票代码
        latest_count: 最新帖子数量
        hot_count: 热门帖子数量
    
    Returns:
        list: 帖子列表
    """
    try:
        url = "https://gbapi.eastmoney.com/webarticlelist/api/Article/Articlelist"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'https://guba.eastmoney.com/list,{code},99.html',
            'Accept': 'application/json'
        }
        
        all_posts = []
        post_ids = set()  # 用于去重
        
        # 1. 获取最新帖子
        params_latest = {
            'code': code,
            'sorttype': '1',  # 1=最新
            'ps': str(latest_count),
            'from': 'CommonBaPost',
            'deviceid': 'quoteweb',
            'version': '200',
            'product': 'Guba',
            'plat': 'Web',
            'needzd': 'true'
        }
        
        response_latest = requests.get(url, params=params_latest, headers=headers, timeout=10)
        if response_latest.status_code == 200:
            data = json.loads(response_latest.text)
            if isinstance(data, dict) and 're' in data and isinstance(data['re'], list):
                for article in data['re']:
                    if isinstance(article, dict):
                        post_id = article.get('post_id')
                        if post_id and post_id not in post_ids:
                            post_ids.add(post_id)
                            post_item = {
                                'post_id': post_id,
                                'title': article.get('post_title', ''),
                                'url': article.get('post_url', ''),
                                'author': article.get('user_nickname', ''),
                                'read_count': article.get('post_click_count', 0),
                                'comment_count': article.get('post_comment_count', 0),
                                'time': article.get('post_publish_time', ''),
                                'type': 'forum',
                                'sort_type': 'latest'
                            }
                            if post_item['title']:
                                all_posts.append(post_item)
        
        # 2. 获取热门帖子
        params_hot = {
            'code': code,
            'sorttype': '2',  # 2=热门
            'ps': str(hot_count),
            'from': 'CommonBaPost',
            'deviceid': 'quoteweb',
            'version': '200',
            'product': 'Guba',
            'plat': 'Web',
            'needzd': 'true'
        }
        
        response_hot = requests.get(url, params=params_hot, headers=headers, timeout=10)
        if response_hot.status_code == 200:
            try:
                data = json.loads(response_hot.text)
                if isinstance(data, dict) and 're' in data and isinstance(data['re'], list):
                    for article in data['re']:
                        if isinstance(article, dict):
                            post_id = article.get('post_id')
                            if post_id and post_id not in post_ids:
                                post_ids.add(post_id)
                                post_item = {
                                    'post_id': post_id,
                                    'title': article.get('post_title', ''),
                                    'url': article.get('post_url', ''),
                                    'author': article.get('user_nickname', ''),
                                    'read_count': article.get('post_click_count', 0),
                                    'comment_count': article.get('post_comment_count', 0),
                                    'time': article.get('post_publish_time', ''),
                                    'type': 'forum',
                                    'sort_type': 'hot'
                                }
                                if post_item['title']:
                                    all_posts.append(post_item)
            except json.JSONDecodeError:
                pass
        
        return all_posts
    except Exception as e:
        return []


# ==================== 技术指标计算函数 ====================

