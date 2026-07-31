#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""策略感知的多选一辩论上下文。"""

from typing import Any, Dict, List, Optional

from portfolio_service import A_SHARE_LOT_RULES


STRATEGY_PROFILES: Dict[str, Dict[str, Any]] = {
    'general': {
        'label': '通用多选一',
        'holding_horizon': '由账户风格决定，通常短线至中线',
        'entry_window': '不限特定时段',
        'exit_plan': '按个股逻辑与账户风控退出',
        'selection_focus': [
            '综合风险收益比',
            '与现有持仓的相关性与集中度',
            '可执行的买卖触发条件',
        ],
        'hard_constraints': [
            '必须给出唯一主选标的，禁止用暂不交易代替选股',
            '若认为当下不宜开仓，仍须选出相对最优主选，并明确建议观望/轻仓/等待触发',
            '不得建议卖出超过可卖数量，仓位必须符合总仓位上限与可用现金',
            A_SHARE_LOT_RULES,
        ],
        'decision_lens': '比较候选的综合质量，不预设超短或隔夜偏好',
        'preferred_agents': [
            '技术分析Agent',
            '资金流Agent',
            '行业对比Agent',
            '舆情Agent',
            '看空Agent',
        ],
        'report_sections': [
            '市场与账户约束',
            '主选标的（必选）',
            '操作态度（可执行/观望等待）',
            '备选标的',
            '仓位与资金安排',
            '进出场计划',
            '风控与失效条件',
        ],
    },
    'strong': {
        'label': '强势股接力',
        'holding_horizon': '1至3个交易日，偏超短接力',
        'entry_window': '确认强势延续后再介入，避免尾盘追高一字',
        'exit_plan': '次日冲高优先兑现；转弱立刻降仓，不恋战',
        'selection_focus': [
            '连板或早盘涨停带来的股性与辨识度',
            '板块情绪能否支撑接力',
            '开板风险、封板质量与情绪退潮信号',
        ],
        'hard_constraints': [
            '必须给出唯一主选标的，禁止结论停在暂不交易',
            '高位加速但情绪退潮时，主选仍要给出，操作态度可改为观望等待确认',
            '单票仓位从严，优先考虑可卖与隔日风险',
            A_SHARE_LOT_RULES,
        ],
        'decision_lens': '优先选情绪延续最强、且次日仍有兑现空间的标的',
        'preferred_agents': [
            '技术分析Agent',
            '资金流Agent',
            '舆情Agent',
            '行业对比Agent',
            '看空Agent',
        ],
        'report_sections': [
            '情绪与接力环境',
            '主选标的（必选）',
            '操作态度（可执行/观望等待）',
            '备选标的',
            '仓位安排',
            '次日卖出/止损计划',
            '失效条件',
        ],
    },
    'four_lights': {
        'label': '四灯共振短线',
        'holding_horizon': '1至5个交易日',
        'entry_window': '三灯以上且量价资金共振时分批介入',
        'exit_plan': '达到目标或任一关键灯熄灭后减仓；最长持有不超过5个交易日',
        'selection_focus': [
            '趋势、动量、量价、资金四灯质量',
            '是否只是反弹而非趋势确认',
            '持有期内的波动与回撤承受力',
        ],
        'hard_constraints': [
            '必须给出唯一主选标的，禁止用暂不交易代替选股',
            '观察候选也可成为主选，但要写清为何相对最优',
            '缺少趋势确认时可建议轻仓或等待触发，但仍须保留主选',
            A_SHARE_LOT_RULES,
        ],
        'decision_lens': '优先选灯数高且结构更完整、适合1至5日持有的标的',
        'preferred_agents': [
            '技术分析Agent',
            '资金流Agent',
            '行业对比Agent',
            '舆情Agent',
            '看空Agent',
        ],
        'report_sections': [
            '四灯质量评估',
            '主选标的（必选）',
            '操作态度（可执行/观望等待）',
            '备选标的',
            '仓位与分批计划',
            '1至5日持有与退出计划',
            '风控与失效条件',
        ],
    },
    'overnight': {
        'label': '尾盘隔夜超短',
        'holding_horizon': '隔夜至次日早盘',
        'entry_window': '更适合14:20后复核执行，避免过早隔夜',
        'exit_plan': '次日集合竞价或开盘优先卖出；高开冲高乏力减仓，低开弱势直接止损',
        'selection_focus': [
            '次日竞价/开盘兑现概率',
            '涨停记忆与隔夜情绪延续',
            '尾盘承接与隔夜回撤风险',
        ],
        'hard_constraints': [
            '必须给出唯一主选标的，禁止结论停在暂不交易',
            '默认不做中线演绎，只评估隔夜到次日早盘',
            '若隔夜赔率一般，仍须选出相对最优主选，并明确建议观望或极小仓试错条件',
            A_SHARE_LOT_RULES,
        ],
        'decision_lens': '优先选隔夜赔率最好、次日最好卖的标的，而不是中线空间最大的票',
        'preferred_agents': [
            '技术分析Agent',
            '资金流Agent',
            '日内做T Agent',
            '舆情Agent',
            '看空Agent',
        ],
        'report_sections': [
            '隔夜环境判断',
            '主选标的（必选）',
            '操作态度（可执行/观望等待）',
            '备选标的',
            '尾盘仓位安排',
            '次日竞价/开盘卖出计划',
            '隔夜风控与失效条件',
        ],
    },
}


def normalize_strategy_key(strategy: Optional[str]) -> str:
    key = str(strategy or 'general').strip().lower()
    return key if key in STRATEGY_PROFILES else 'general'


def build_strategy_profile(
    strategy: Optional[str] = None,
    candidate_lines: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    key = normalize_strategy_key(strategy)
    base = dict(STRATEGY_PROFILES[key])
    profile = {
        'strategy': key,
        'label': base['label'],
        'holding_horizon': base['holding_horizon'],
        'entry_window': base['entry_window'],
        'exit_plan': base['exit_plan'],
        'selection_focus': list(base['selection_focus']),
        'hard_constraints': list(base['hard_constraints']),
        'decision_lens': base['decision_lens'],
        'preferred_agents': list(base['preferred_agents']),
        'report_sections': list(base['report_sections']),
        'candidate_summary': '\n'.join(candidate_lines or [])[:8000],
    }
    if extra:
        for field in (
            'holding_horizon',
            'entry_window',
            'exit_plan',
            'decision_lens',
            'candidate_summary',
            'label',
        ):
            value = extra.get(field)
            if value:
                profile[field] = value
        for field in ('selection_focus', 'hard_constraints', 'report_sections', 'preferred_agents'):
            value = extra.get(field)
            if isinstance(value, list) and value:
                profile[field] = value
    return profile


def format_strategy_brief(profile: Dict[str, Any]) -> str:
    focus = '\n'.join(f'- {item}' for item in profile.get('selection_focus') or [])
    constraints = '\n'.join(f'- {item}' for item in profile.get('hard_constraints') or [])
    sections = ' / '.join(profile.get('report_sections') or [])
    candidate_summary = profile.get('candidate_summary') or '无额外量化摘要'
    return '\n'.join([
        '【策略多选一约束】',
        f"策略：{profile.get('label')} ({profile.get('strategy')})",
        f"建议持有：{profile.get('holding_horizon')}",
        f"介入窗口：{profile.get('entry_window')}",
        f"退出计划：{profile.get('exit_plan')}",
        f"决策视角：{profile.get('decision_lens')}",
        '选择重点：',
        focus,
        '硬约束：',
        constraints,
        '选股强制要求：必须明确唯一主选股票代码与名称；允许建议“观望/等待触发/轻仓”，',
        '但禁止把最终结论写成暂不交易或 NO TRADE 来回避选股。',
        f'交易单位：{A_SHARE_LOT_RULES}',
        f'最终报告必须覆盖：{sections}',
        '候选量化摘要：',
        candidate_summary,
        '所有Agent必须在上述策略周期内评估，不要用更长周期的逻辑覆盖策略假设。',
    ])


def build_strategy_multi_instruction(profile: Dict[str, Any]) -> str:
    return (
        f"This is a strategy-aware multi-stock selection for {profile.get('label')}. "
        f"Holding horizon: {profile.get('holding_horizon')}. "
        f"Exit plan: {profile.get('exit_plan')}. "
        "You MUST choose exactly ONE primary candidate from the provided list. "
        "You may also choose at most ONE backup candidate. "
        "If the setup is weak, still pick the relatively best primary candidate, "
        "and set action stance to wait/watch/light-position instead of refusing to choose. "
        "Never end with NO TRADE or 暂不交易 as the stock selection result. "
        "Do not optimize for a different holding period."
    )


def build_strategy_decision_prompt(
    profile: Dict[str, Any],
    strategy_brief: str,
    combined_data: str,
    portfolio_context: str,
    transcript: str,
) -> str:
    sections = '\n'.join(
        f'{index}. {title}'
        for index, title in enumerate(profile.get('report_sections') or [], start=1)
    )
    return (
        "You are the final decision maker for a strategy-aware A-share multi-select task.\n"
        "Respect the strategy holding horizon and exit plan above all.\n"
        "HARD RULE: You MUST name exactly ONE primary candidate with stock code and name. "
        "A backup candidate is optional. "
        "You may recommend waiting, watching, or using a very light position, "
        "but you are NOT allowed to conclude with NO TRADE / 暂不交易 instead of selecting a stock.\n"
        "Be decisive and action-oriented, but never invent missing evidence.\n\n"
        f"{strategy_brief}\n\n"
        f"Candidates:\n{combined_data}\n\n"
        f"{portfolio_context}\n\n"
        f"Debate Transcript:\n{transcript}\n\n"
        "Output a Chinese Markdown report with these sections:\n"
        f"{sections}\n\n"
        "In 主选标的（必选）, always include: code, name, why it is the relative best under this strategy, "
        "and whether current action stance is 可执行买入 / 等待触发 / 仅观察. "
        "Also include entry range, suggested position percentage and amount, stop loss, take profit, "
        "exact sell timing, validity period and invalidation conditions. "
        "Quantity suggestions must follow A-share lot rules: 1 lot = 100 shares; "
        "never suggest odd lots like 50 shares except when clearing remaining odd shares."
    )
