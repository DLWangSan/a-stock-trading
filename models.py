#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据库模型定义"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, Float, UniqueConstraint, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Watchlist(Base):
    """自选股表"""
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(50))
    added_at = Column(DateTime, default=datetime.now)
    sort_order = Column(Integer, default=0)

class Config(Base):
    """配置表"""
    __tablename__ = 'config'
    
    key = Column(String(50), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Agent(Base):
    """Agent配置表"""
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    type = Column(String(20), nullable=False)  # 'default', 'intraday_t', 'review'
    prompt = Column(Text)
    enabled = Column(Boolean, default=True)
    ai_provider = Column(String(20))  # 'openai', 'deepseek', 'qwen', 'gemini', 'grok'
    model = Column(String(50))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

class AnalysisCache(Base):
    """分析结果缓存表"""
    __tablename__ = 'analysis_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(6), nullable=False, index=True)
    analysis_type = Column(String(20), nullable=False)  # 'intraday_t', 'review', 'comprehensive'
    data = Column(Text)  # JSON格式
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

class DebateJob(Base):
    """多Agent辩论任务表"""
    __tablename__ = 'debate_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)
    code = Column(String(6), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default='queued')  # queued/running/completed/failed/canceled
    progress = Column(Integer, default=0)
    agent_ids = Column(Text)  # JSON
    steps = Column(Text)  # JSON
    report_md = Column(Text)
    error = Column(Text)
    canceled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class TradingProfile(Base):
    """单用户交易画像（当前系统默认仅使用 id=1）。"""
    __tablename__ = 'trading_profiles'

    id = Column(Integer, primary_key=True, default=1)
    style = Column(String(20), default='short')  # ultra_short/short/medium/long
    risk_level = Column(String(20), default='balanced')  # conservative/balanced/aggressive
    max_single_position_pct = Column(Float, default=30.0)
    max_total_position_pct = Column(Float, default=80.0)
    default_stop_loss_pct = Column(Float, default=5.0)
    default_take_profit_pct = Column(Float, default=10.0)
    available_cash = Column(Float, default=0.0)
    allow_intraday_t = Column(Boolean, default=True)
    notes = Column(Text, default='')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Position(Base):
    """用户当前持仓。A 股做 T 需要区分总数量与当日可卖数量。"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(50))
    quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0)
    opened_at = Column(DateTime)
    target_price = Column(Float)
    stop_loss_price = Column(Float)
    thesis = Column(Text, default='')
    notes = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class StrategySignal(Base):
    """策略扫描快照，用于跨时段验证信号表现。"""
    __tablename__ = 'strategy_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, index=True)
    strategy = Column(String(30), nullable=False, index=True)
    scan_session = Column(String(20), nullable=False)
    code = Column(String(6), nullable=False, index=True)
    name = Column(String(50))
    signal_price = Column(Float, nullable=False)
    score = Column(Float)
    light_count = Column(Integer)
    lights = Column(Text)
    details = Column(Text)
    validation_status = Column(String(20), default='pending')
    validation_price = Column(Float)
    validation_return_pct = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    validated_at = Column(DateTime)


class CapitalFlowSnapshot(Base):
    """本地累计的个股日级主力资金，用作外部5日接口的稳定备份。"""
    __tablename__ = 'capital_flow_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(6), nullable=False, index=True)
    trade_date = Column(String(10), nullable=False, index=True)
    main_net_inflow = Column(Float)
    main_net_ratio = Column(Float)
    source = Column(String(30))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('code', 'trade_date', name='uq_capital_flow_code_date'),
    )

# 数据库初始化
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base.metadata.create_all(engine)


def _ensure_sqlite_columns():
    """为已有本地数据库补充轻量字段；新数据库由 create_all 直接创建。"""
    columns = {column['name'] for column in inspect(engine).get_columns('trading_profiles')}
    if 'available_cash' not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                'ALTER TABLE trading_profiles ADD COLUMN available_cash FLOAT DEFAULT 0.0'
            ))


_ensure_sqlite_columns()
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

