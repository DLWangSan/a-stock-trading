#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证换手率是否传递给agent"""

from technical_indicators import get_comprehensive_data_with_indicators
from data_formatters import format_for_ai

# 测试两个股票
test_codes = ['603256', '601615']

for code in test_codes:
    print(f"\n{'='*60}")
    print(f"测试股票: {code}")
    print('='*60)
    
    data = get_comprehensive_data_with_indicators(code)
    formatted = format_for_ai(data)
    
    # 检查实时数据中的换手率
    realtime_turnover = data['realtime'].get('turnover_rate') if data.get('realtime') else None
    print(f"\n实时数据中的换手率: {realtime_turnover}")
    
    # 检查格式化数据中是否包含换手率
    has_turnover = '换手率' in formatted
    print(f"格式化数据中包含换手率: {has_turnover}")
    
    if has_turnover:
        # 提取换手率行
        for line in formatted.split('\n'):
            if '换手率' in line:
                print(f"格式化后的换手率信息: {line.strip()}")
                # 提取数值
                import re
                match = re.search(r'换手率:\s*([\d.]+)%', line)
                if match:
                    formatted_value = float(match.group(1))
                    print(f"格式化后的换手率数值: {formatted_value}%")
                    if realtime_turnover:
                        diff = abs(formatted_value - realtime_turnover)
                        if diff < 0.01:  # 允许0.01%的误差（四舍五入）
                            print("✓ 换手率数值匹配正确")
                        else:
                            print(f"✗ 换手率数值不匹配，差异: {diff}%")
                break
