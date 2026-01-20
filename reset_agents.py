#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清空并重建默认Agent配置"""

from models import SessionLocal, Agent
from init_agents import init_default_agents


def reset_agents():
    db = SessionLocal()
    try:
        db.query(Agent).delete()
        db.commit()
        print("[重置] 已清空所有Agent")
    finally:
        db.close()

    init_default_agents()


if __name__ == '__main__':
    reset_agents()


