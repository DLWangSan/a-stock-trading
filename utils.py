#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具函数模块
"""


def get_stock_code_format(code):
    """转换股票代码格式（用于新浪API）"""
    code_str = str(code).strip()
    if code_str.startswith('6'):
        return f"sh{code_str}"
    elif code_str.startswith(('0', '3')):
        return f"sz{code_str}"
    else:
        return code_str


def get_secid(code):
    """获取东方财富API的secid格式"""
    return f"{'1' if code.startswith('6') else '0'}.{code}"

