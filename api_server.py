#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask API服务 - 股票数据查询接口
使用新浪和东方财富API提供股票数据
"""

from flask import Flask, jsonify
from flask_cors import CORS
import warnings

warnings.filterwarnings('ignore')

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 确保JSON响应使用UTF-8编码
app.config['JSON_AS_ASCII'] = False

# 导入并注册路由（延迟导入避免循环依赖）
def register_routes():
    from api_routes import register_routes as register
    register(app)

register_routes()

if __name__ == '__main__':
    print("=" * 60)
    print("股票数据API服务启动")
    print("=" * 60)
    print("访问 http://localhost:5000 查看API文档")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
