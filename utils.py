#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具函数模块
"""


def get_stock_code_format(code):
    """转换股票代码格式（用于新浪API）"""
    code_str = str(code).strip()
    
    # 如果已经是sh/sz格式，直接返回
    if code_str.startswith(('sh', 'sz')):
        return code_str
    
    # 处理指数代码
    if code_str == '1A0001' or code_str == '000001':
        # 上证指数使用 sh000001
        return 'sh000001'
    elif code_str.startswith('1A'):
        # 其他指数代码，去掉1A前缀
        return f"sh{code_str[2:]}"
    elif code_str.startswith('6'):
        return f"sh{code_str}"
    elif code_str.startswith(('0', '3')):
        return f"sz{code_str}"
    else:
        return code_str


def get_secid(code):
    """获取东方财富API的secid格式"""
    code_str = str(code).strip()
    
    # 处理指数代码
    if code_str == '1A0001' or code_str == '000001':
        # 上证指数
        return '1.000001'
    elif code_str.startswith('1A'):
        # 其他指数代码，去掉1A前缀
        return f"1.{code_str[2:]}"
    elif code_str.startswith('6'):
        return f"1.{code_str}"
    else:
        return f"0.{code_str}"

