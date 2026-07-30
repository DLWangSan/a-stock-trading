#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""默认核心 Agent 组合选择。"""

from typing import Iterable, List


CORE_AGENT_NAMES = [
    '技术分析Agent',
    '资金流Agent',
    '行业对比Agent',
    '舆情Agent',
    '看空Agent',
]

STRATEGY_AGENT_NAMES = {
    'general': CORE_AGENT_NAMES,
    'strong': [
        '技术分析Agent',
        '资金流Agent',
        '舆情Agent',
        '行业对比Agent',
        '看空Agent',
    ],
    'four_lights': CORE_AGENT_NAMES,
    'overnight': [
        '技术分析Agent',
        '资金流Agent',
        '日内做T Agent',
        '舆情Agent',
        '看空Agent',
    ],
}


def select_core_agent_ids(agents: Iterable, limit: int = 5, strategy: str = 'general') -> List[int]:
    """优先返回与策略匹配的核心角色；缺失时按排序补足。"""
    rows = list(agents)
    by_name = {agent.name: agent for agent in rows}
    preferred = STRATEGY_AGENT_NAMES.get(strategy, CORE_AGENT_NAMES)
    selected = [
        by_name[name].id
        for name in preferred
        if name in by_name
    ]
    for agent in sorted(rows, key=lambda item: (item.sort_order or 0, item.id)):
        if agent.id not in selected:
            selected.append(agent.id)
        if len(selected) >= limit:
            break
    return selected[:limit]
