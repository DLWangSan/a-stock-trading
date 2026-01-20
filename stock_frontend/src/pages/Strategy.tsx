import { useQuery } from '@tanstack/react-query';
import { stockAPI } from '../services/api';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';

interface StrongStock {
  code: string;
  name: string;
  t1_limit_time: string;
  t2_limit_time: string;
  consecutive_days: number;
  break_count: number;
  industry: string;
  current_price: number | null;
  change_percent: number | null;
  volume: number | null;
  amount: number | null;
}

interface StrongStocksResponse {
  strategy: string;
  description: string;
  params: {
    limit_time: string;
  };
  trade_dates: {
    T: string;
    'T-1': string;
    'T-2': string;
  };
  count: number;
  stocks: StrongStock[];
}

const TIME_OPTIONS = [
  '09:30', '09:45', '10:00', '10:15', '10:30', '10:45',
  '11:00', '11:15', '11:30', '13:00', '13:30', '14:00', '14:30', '15:00'
];

export default function Strategy() {
  const [limitTime, setLimitTime] = useState('11:30');
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [showMultiModal, setShowMultiModal] = useState(false);
  const [selectedAgentIds, setSelectedAgentIds] = useState<number[]>([]);
  const [multiMode, setMultiMode] = useState<'fast' | 'balanced' | 'deep'>('fast');
  const [multiError, setMultiError] = useState<string | null>(null);
  const [addingMap, setAddingMap] = useState<Record<string, boolean>>({});
  const [addedMap, setAddedMap] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();

  const { data, isLoading, error, refetch, isFetching } = useQuery<StrongStocksResponse>({
    queryKey: ['strong-stocks', limitTime],
    queryFn: () => stockAPI.getStrongStocks(limitTime),
    refetchInterval: 60000, // 每分钟刷新一次
  });

  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents', 'enabled'],
    queryFn: () => stockAPI.getAgents(true),
    enabled: showMultiModal,
  });

  useEffect(() => {
    if (showMultiModal && agents && agents.length > 0 && selectedAgentIds.length === 0) {
      setSelectedAgentIds(agents.map((agent) => agent.id));
    }
  }, [showMultiModal, agents, selectedAgentIds.length]);

  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '-';
    if (num >= 100000000) {
      return (num / 100000000).toFixed(2) + '亿';
    } else if (num >= 10000) {
      return (num / 10000).toFixed(2) + '万';
    }
    return num.toFixed(2);
  };

  // 格式化涨停时间显示（将092500转为09:25:00）
  const formatLimitTime = (time: string | null | undefined): string => {
    if (!time) return '-';
    const str = String(time);
    if (str.includes(':')) return str;
    if (str.length === 6) {
      return `${str.slice(0, 2)}:${str.slice(2, 4)}:${str.slice(4, 6)}`;
    } else if (str.length === 5) {
      return `0${str.slice(0, 1)}:${str.slice(1, 3)}:${str.slice(3, 5)}`;
    }
    return str;
  };

  const toggleSelectCode = (code: string) => {
    setSelectedCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleAddWatchlist = async (code: string, name: string) => {
    if (addingMap[code]) return;
    setAddingMap((prev) => ({ ...prev, [code]: true }));
    try {
      await stockAPI.addWatchlist(code, name);
      setAddedMap((prev) => ({ ...prev, [code]: true }));
    } catch (e) {
      console.error('加入自选失败:', e);
      alert('加入自选失败');
    } finally {
      setAddingMap((prev) => ({ ...prev, [code]: false }));
    }
  };

  const handleOpenMulti = () => {
    if (selectedCodes.length < 2) {
      setMultiError('请至少勾选2只股票');
      return;
    }
    setMultiError(null);
    setShowMultiModal(true);
  };

  const handleStartMulti = async () => {
    if (selectedCodes.length < 2) {
      setMultiError('请至少勾选2只股票');
      return;
    }
    if (selectedAgentIds.length < 2) {
      setMultiError('至少选择2个Agent参与辩论');
      return;
    }
    setMultiError(null);
    try {
      const modeConfig = {
        fast: { analysisRounds: 1, debateRounds: 1 },
        balanced: { analysisRounds: 2, debateRounds: 1 },
        deep: { analysisRounds: 3, debateRounds: 2 },
      }[multiMode];
      const res = await stockAPI.startMultiSelectDebate(
        selectedCodes,
        selectedAgentIds,
        modeConfig.analysisRounds,
        modeConfig.debateRounds
      );
      setShowMultiModal(false);
      const params = new URLSearchParams();
      params.set('job_id', res.job_id);
      params.set('code', selectedCodes.join(','));
      navigate(`/ai-debate?${params.toString()}`);
    } catch (e) {
      console.error('多选一任务启动失败:', e);
      setMultiError('启动多选一任务失败，请稍后重试');
    }
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      {/* 策略卡片 - 始终显示 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* 强势股策略 */}
        <div className="bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold">强势股策略</h2>
            {isLoading ? (
              <div className="text-right">
                <div className="h-10 w-16 bg-blue-400/50 rounded animate-pulse"></div>
                <div className="text-sm text-blue-100 mt-1">加载中...</div>
              </div>
            ) : (
              <div className="text-right">
                <div className="text-4xl font-bold">{data?.count || 0}</div>
                <div className="text-sm text-blue-100">符合条件</div>
              </div>
            )}
          </div>
          
          {/* 参数设置 */}
          <div className="mb-4 p-3 bg-blue-600/50 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-blue-100 mb-1">涨停截止时间</div>
                <div className="text-xs text-blue-200">T-1和T-2共用</div>
              </div>
              <select
                value={limitTime}
                onChange={(e) => setLimitTime(e.target.value)}
                className="px-3 py-2 text-sm bg-white/20 border border-blue-400/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                {TIME_OPTIONS.map((time) => (
                  <option key={time} value={time} className="text-gray-900">
                    {time}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-4 w-32 bg-blue-400/50 rounded animate-pulse"></div>
              <div className="h-4 w-36 bg-blue-400/50 rounded animate-pulse"></div>
              <div className="h-4 w-36 bg-blue-400/50 rounded animate-pulse"></div>
            </div>
          ) : data?.trade_dates ? (
            <div className="space-y-1 text-sm text-blue-100">
              <div>T 日: {data.trade_dates.T}</div>
              <div>T-1日: {data.trade_dates['T-1']}</div>
              <div>T-2日: {data.trade_dates['T-2']}</div>
            </div>
          ) : null}
        </div>

        {/* 其他策略待开发 */}
        <div className="bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-xl p-6 shadow-lg flex items-center justify-center">
          <div className="text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">其他策略</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">正在开发中...</p>
          </div>
        </div>
      </div>

      {/* 风险提示 - 始终显示 */}
      <div className="mb-6 text-center">
        <p className="text-sm text-yellow-600 dark:text-yellow-400 flex items-center justify-center gap-2">
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>固定策略筛选，仅供参考学习。股市有风险，投资需谨慎，不构成投资建议。</span>
        </p>
      </div>

      {/* 筛选结果标题和刷新按钮 - 始终显示 */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">筛选结果</h2>
        <div className="flex items-center gap-3">
          {selectedCodes.length >= 2 && (
            <button
              onClick={handleOpenMulti}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              多选一 AI分析
            </button>
          )}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className={`h-5 w-5 ${isFetching ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {isFetching ? '刷新中...' : '刷新数据'}
          </button>
        </div>
      </div>

      {/* 股票列表 - 根据状态渲染 */}
      {isLoading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12">
          <div className="flex flex-col items-center justify-center">
            <LoadingSpinner size="large" />
            <p className="mt-4 text-gray-500 dark:text-gray-400">正在加载数据...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 className="text-red-800 dark:text-red-300 font-medium">加载数据失败</h3>
          <p className="text-red-600 dark:text-red-400 text-sm mt-1">{String(error)}</p>
          <button
            onClick={() => refetch()}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            重试
          </button>
        </div>
      ) : !data || data.stocks.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <p className="mt-2 text-gray-500 dark:text-gray-400">暂无符合条件的股票</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden shadow">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    勾选
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    代码
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    名称
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    行业
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    T-1涨停
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    T-2涨停
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    连板
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    炸板
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    当前价
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    涨跌幅
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    成交量
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {data.stocks.map((stock) => (
                  <tr key={stock.code} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                      <input
                        type="checkbox"
                        checked={selectedCodes.includes(stock.code)}
                        onChange={() => toggleSelectCode(stock.code)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {stock.code}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {stock.name}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {stock.industry || '-'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatLimitTime(stock.t1_limit_time)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatLimitTime(stock.t2_limit_time)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                      {stock.consecutive_days > 0 ? (
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                          {stock.consecutive_days}连板
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {stock.break_count > 0 ? (
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                          {stock.break_count}次
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {stock.current_price ? `¥${stock.current_price.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-semibold">
                      {stock.change_percent !== null ? (
                        <span
                          className={
                            stock.change_percent >= 0
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-green-600 dark:text-green-400'
                          }
                        >
                          {stock.change_percent >= 0 ? '+' : ''}
                          {stock.change_percent.toFixed(2)}%
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatNumber(stock.volume)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/stock/${stock.code}`}
                          className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
                        >
                          详情
                        </Link>
                        <button
                          onClick={() => handleAddWatchlist(stock.code, stock.name)}
                          disabled={addingMap[stock.code] || addedMap[stock.code]}
                          className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {addedMap[stock.code] ? '已加入' : addingMap[stock.code] ? '加入中' : '加入自选'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 多选一 模态 */}
      {showMultiModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">多选一 AI分析</h2>
              <button
                onClick={() => {
                  setShowMultiModal(false);
                  setMultiError(null);
                }}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                本模式要求从所选股票中<strong>必须选择一只</strong>进行买入决策。
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  选择模式
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    onClick={() => setMultiMode('fast')}
                    className={`px-3 py-2 rounded-lg text-sm border ${
                      multiMode === 'fast'
                        ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                        : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
                    }`}
                  >
                    快速模式
                    <div className="text-xs opacity-70">思考1 / 辩论1</div>
                  </button>
                  <button
                    onClick={() => setMultiMode('balanced')}
                    className={`px-3 py-2 rounded-lg text-sm border ${
                      multiMode === 'balanced'
                        ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                        : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
                    }`}
                  >
                    均衡模式
                    <div className="text-xs opacity-70">思考2 / 辩论1</div>
                  </button>
                  <button
                    onClick={() => setMultiMode('deep')}
                    className={`px-3 py-2 rounded-lg text-sm border ${
                      multiMode === 'deep'
                        ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                        : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
                    }`}
                  >
                    深入模式
                    <div className="text-xs opacity-70">思考3 / 辩论2</div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  选择参与辩论的Agent（至少2个）
                </label>
                {agentsLoading ? (
                  <div className="text-gray-500">加载中...</div>
                ) : agents && agents.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {agents.map((agent) => (
                      <label
                        key={agent.id}
                        className="flex items-center gap-2 p-2 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <input
                          type="checkbox"
                          checked={selectedAgentIds.includes(agent.id)}
                          onChange={() =>
                            setSelectedAgentIds((prev) =>
                              prev.includes(agent.id) ? prev.filter((id) => id !== agent.id) : [...prev, agent.id]
                            )
                          }
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
              {multiError && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-red-700 dark:text-red-400 text-sm">
                  {multiError}
                </div>
              )}

              <button
                onClick={handleStartMulti}
                className="w-full px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-all font-semibold"
              >
                启动多选一分析
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
