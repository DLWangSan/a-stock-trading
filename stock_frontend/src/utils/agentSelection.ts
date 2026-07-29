import type { Agent } from '../services/api';

export const CORE_AGENT_NAMES = [
  '技术分析Agent',
  '资金流Agent',
  '行业对比Agent',
  '舆情Agent',
  '看空Agent',
];

export function getDefaultAgentIds(agents: Agent[], limit = 5): number[] {
  const byName = new Map(agents.map((agent) => [agent.name, agent]));
  const selected = CORE_AGENT_NAMES
    .map((name) => byName.get(name)?.id)
    .filter((id): id is number => id !== undefined);

  const sorted = [...agents].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
  for (const agent of sorted) {
    if (!selected.includes(agent.id)) selected.push(agent.id);
    if (selected.length >= limit) break;
  }
  return selected.slice(0, limit);
}
