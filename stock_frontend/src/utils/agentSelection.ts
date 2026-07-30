import type { Agent } from '../services/api';

export const CORE_AGENT_NAMES = [
  '技术分析Agent',
  '资金流Agent',
  '行业对比Agent',
  '舆情Agent',
  '看空Agent',
];

export const STRATEGY_AGENT_NAMES: Record<string, string[]> = {
  general: CORE_AGENT_NAMES,
  strong: [
    '技术分析Agent',
    '资金流Agent',
    '舆情Agent',
    '行业对比Agent',
    '看空Agent',
  ],
  four_lights: CORE_AGENT_NAMES,
  overnight: [
    '技术分析Agent',
    '资金流Agent',
    '日内做T Agent',
    '舆情Agent',
    '看空Agent',
  ],
};

export const STRATEGY_LABELS: Record<string, string> = {
  general: '通用多选一',
  strong: '强势股接力',
  four_lights: '四灯共振短线',
  overnight: '尾盘隔夜超短',
};

export function getDefaultAgentIds(
  agents: Agent[],
  limit = 5,
  strategy: string = 'general',
): number[] {
  const byName = new Map(agents.map((agent) => [agent.name, agent]));
  const preferred = STRATEGY_AGENT_NAMES[strategy] || CORE_AGENT_NAMES;
  const selected = preferred
    .map((name) => byName.get(name)?.id)
    .filter((id): id is number => id !== undefined);

  const sorted = [...agents].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
  for (const agent of sorted) {
    if (!selected.includes(agent.id)) selected.push(agent.id);
    if (selected.length >= limit) break;
  }
  return selected.slice(0, limit);
}
