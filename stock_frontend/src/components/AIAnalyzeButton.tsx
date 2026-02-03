import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import type { Agent } from '../services/api';

interface AIAnalyzeButtonProps {
  code: string;
  className?: string;
}

export default function AIAnalyzeButton({ code, className = '' }: AIAnalyzeButtonProps) {
  const [showModal, setShowModal] = useState(false);
  const [selectedAgentIds, setSelectedAgentIds] = useState<number[]>([]);
  const [mode, setMode] = useState<'fast' | 'balanced' | 'deep'>('fast');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const prevShowModalRef = useRef(false);

  // 获取启用的Agents
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents', 'enabled'],
    queryFn: () => stockAPI.getAgents(true),
  });

  // 仅在弹窗「刚打开」时默认全选，避免「清空」后被 useEffect 再次全选
  useEffect(() => {
    if (showModal && !prevShowModalRef.current && agents && agents.length > 0) {
      setSelectedAgentIds(agents.map((agent) => agent.id));
    }
    prevShowModalRef.current = showModal;
  }, [showModal, agents]);

  const toggleAgent = (agentId: number) => {
    setSelectedAgentIds((prev) =>
      prev.includes(agentId) ? prev.filter((id) => id !== agentId) : [...prev, agentId]
    );
  };

  const handleStartDebate = () => {
    if (selectedAgentIds.length < 2) {
      setError('至少选择2个Agent参与辩论');
      return;
    }

    setError(null);
    setShowModal(false);
    const modeConfig = {
      fast: { analysisRounds: 1, debateRounds: 1, label: '快速模式' },
      balanced: { analysisRounds: 2, debateRounds: 1, label: '均衡模式' },
      deep: { analysisRounds: 3, debateRounds: 2, label: '深入模式' },
    }[mode];
    navigate(`/ai-debate?code=${code}&ar=${modeConfig.analysisRounds}&dr=${modeConfig.debateRounds}`, {
      state: {
        code,
        agentIds: selectedAgentIds,
        analysisRounds: modeConfig.analysisRounds,
        debateRounds: modeConfig.debateRounds,
        modeLabel: modeConfig.label,
      },
    });
  };

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className={`px-4 py-2 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all shadow-md hover:shadow-lg flex items-center gap-2 ${className}`}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        TradingAgents AI分析
      </button>

      {/* 辩论选择弹窗 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* 头部 */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                TradingAgents 多Agent辩论
              </h2>
              <button
                onClick={() => {
                  setShowModal(false);
                  setError(null);
                }}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 内容 */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                  {/* 模式选择 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      选择模式
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <button
                        onClick={() => setMode('fast')}
                        className={`px-3 py-2 rounded-lg text-sm border ${
                          mode === 'fast'
                            ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
                        }`}
                      >
                        快速模式
                        <div className="text-xs opacity-70">思考1 / 辩论1</div>
                      </button>
                      <button
                        onClick={() => setMode('balanced')}
                        className={`px-3 py-2 rounded-lg text-sm border ${
                          mode === 'balanced'
                            ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
                        }`}
                      >
                        均衡模式
                        <div className="text-xs opacity-70">思考2 / 辩论1</div>
                      </button>
                      <button
                        onClick={() => setMode('deep')}
                        className={`px-3 py-2 rounded-lg text-sm border ${
                          mode === 'deep'
                            ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
                        }`}
                      >
                        深入模式
                        <div className="text-xs opacity-70">思考3 / 辩论2</div>
                      </button>
                    </div>
                  </div>

                {/* Agent选择 */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      选择参与辩论的Agent（至少2个）
                    </label>
                    {agents && agents.length > 0 && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSelectedAgentIds(agents.map((agent) => agent.id))}
                          className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded"
                        >
                          全选
                        </button>
                        <button
                          onClick={() => setSelectedAgentIds([])}
                          className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded"
                        >
                          清空
                        </button>
                      </div>
                    )}
                  </div>
                  {agentsLoading ? (
                    <div className="text-gray-500">加载中...</div>
                  ) : agents && agents.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {agents.map((agent: Agent) => (
                        <label
                          key={agent.id}
                          className="flex items-center gap-2 p-2 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                        >
                          <input
                            type="checkbox"
                            checked={selectedAgentIds.includes(agent.id)}
                            onChange={() => toggleAgent(agent.id)}
                            className="rounded"
                          />
                          <span className="text-sm text-gray-900 dark:text-white">
                            {agent.name} ({agent.type})
                          </span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <div className="text-gray-500">暂无启用的Agent，请先在配置页面添加</div>
                  )}
                </div>

                {/* 错误提示 */}
                {error && (
                  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">
                    {error}
                  </div>
                )}

                {/* 进入辩论 */}
                <button
                  onClick={handleStartDebate}
                  disabled={selectedAgentIds.length < 2}
                  className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold"
                >
                  进入辩论
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

