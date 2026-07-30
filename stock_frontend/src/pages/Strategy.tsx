import { useQuery, useQueryClient } from '@tanstack/react-query';
import { stockAPI } from '../services/api';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';
import { getDefaultAgentIds } from '../utils/agentSelection';
import type { FourLightsCandidate, FourLightsRun, FourLightsScan, OvernightCandidate, OvernightScan } from '../services/api';

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
  score: number;
  rank: number;
  eligible: boolean;
  recommended: boolean;
  score_reasons: string[];
  risk_flags: string[];
  hard_filter_reasons: string[];
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
  recommended_count: number;
  stocks: StrongStock[];
}

const TIME_OPTIONS = [
  '09:30', '09:45', '10:00', '10:15', '10:30', '10:45',
  '11:00', '11:15', '11:30', '13:00', '13:30', '14:00', '14:30', '15:00'
];

export default function Strategy() {
  const [activeStrategy, setActiveStrategy] = useState<'strong' | 'four_lights' | 'overnight'>('strong');
  const [limitTime, setLimitTime] = useState('11:30');
  const [fourLightsSession, setFourLightsSession] = useState<'auto' | 'morning' | 'afternoon'>('auto');
  const [fourLightsData, setFourLightsData] = useState<FourLightsScan | null>(null);
  const [fourLightsScanning, setFourLightsScanning] = useState(false);
  const [fourLightsError, setFourLightsError] = useState<string | null>(null);
  const [overnightData, setOvernightData] = useState<OvernightScan | null>(null);
  const [overnightScanning, setOvernightScanning] = useState(false);
  const [overnightError, setOvernightError] = useState<string | null>(null);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [showMultiModal, setShowMultiModal] = useState(false);
  const [selectedAgentIds, setSelectedAgentIds] = useState<number[]>([]);
  const [multiMode, setMultiMode] = useState<'fast' | 'balanced' | 'deep'>('fast');
  const [multiError, setMultiError] = useState<string | null>(null);
  const [addingMap, setAddingMap] = useState<Record<string, boolean>>({});
  const [addedMap, setAddedMap] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();
  const prevShowMultiModalRef = useRef(false);

  const { data, isLoading, error, refetch, isFetching } = useQuery<StrongStocksResponse>({
    queryKey: ['strong-stocks', limitTime],
    queryFn: () => stockAPI.getStrongStocks(limitTime),
    refetchInterval: 60000, // 每分钟刷新一次
    enabled: activeStrategy === 'strong',
  });

  const { data: fourLightsHistory = [], refetch: refetchFourLightsHistory } = useQuery<FourLightsRun[]>({
    queryKey: ['four-lights-history'],
    queryFn: () => stockAPI.getFourLightsHistory(10),
    enabled: activeStrategy === 'four_lights',
  });

  const { data: overnightHistory = [], refetch: refetchOvernightHistory } = useQuery<FourLightsRun[]>({
    queryKey: ['overnight-history'],
    queryFn: () => stockAPI.getOvernightHistory(10),
    enabled: activeStrategy === 'overnight',
  });

  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents', 'enabled'],
    queryFn: () => stockAPI.getAgents(true),
    enabled: showMultiModal,
  });

  useEffect(() => {
    if (showMultiModal && !prevShowMultiModalRef.current && agents && agents.length > 0) {
      setSelectedAgentIds(getDefaultAgentIds(agents));
    }
    prevShowMultiModalRef.current = showMultiModal;
  }, [showMultiModal, agents]);

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

  const handleScanFourLights = async () => {
    setFourLightsScanning(true);
    setFourLightsError(null);
    setSelectedCodes([]);
    try {
      const result = await stockAPI.scanFourLights(fourLightsSession);
      setFourLightsData(result);
      setSelectedCodes(result.stocks.map((stock) => stock.code));
      await refetchFourLightsHistory();
    } catch (e) {
      setFourLightsError(e instanceof Error ? e.message : '四灯策略扫描失败');
    } finally {
      setFourLightsScanning(false);
    }
  };

  const handleScanOvernight = async () => {
    setOvernightScanning(true);
    setOvernightError(null);
    setSelectedCodes([]);
    try {
      const result = await stockAPI.scanOvernight();
      setOvernightData(result);
      setSelectedCodes(result.stocks.map((stock) => stock.code));
      await refetchOvernightHistory();
    } catch (e) {
      setOvernightError(e instanceof Error ? e.message : '隔夜策略扫描失败');
    } finally {
      setOvernightScanning(false);
    }
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
      const candidateContext = activeStrategy === 'four_lights'
        ? fourLightsData?.stocks
          .filter((stock) => selectedCodes.includes(stock.code))
          .map((stock) => (
            `${stock.rank}. ${stock.name}(${stock.code})：四灯${stock.light_count}/4，`
            + `评分${stock.score}，建议持有1至5个交易日，`
            + `点亮${Object.entries(stock.lights).filter(([, on]) => on).map(([key]) => key).join('/')}`
          ))
          .join('\n')
        : activeStrategy === 'overnight'
          ? overnightData?.stocks
            .filter((stock) => selectedCodes.includes(stock.code))
            .map((stock) => (
              `${stock.rank}. ${stock.name}(${stock.code})：隔夜通过${stock.pass_count}/5，`
              + `评分${stock.score}，持有周期隔夜至次日早盘，卖出计划：${stock.sell_plan}`
            ))
            .join('\n')
          : undefined;
      const res = await stockAPI.startMultiSelectDebate(
        selectedCodes,
        selectedAgentIds,
        modeConfig.analysisRounds,
        modeConfig.debateRounds,
        candidateContext
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
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 强势股策略 */}
        <div
          onClick={() => { setActiveStrategy('strong'); setSelectedCodes([]); }}
          className={`cursor-pointer bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl p-6 text-white shadow-lg ring-offset-2 ${
            activeStrategy === 'strong' ? 'ring-4 ring-blue-300' : ''
          }`}
        >
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

        {/* 全市场四灯策略 */}
        <div
          onClick={() => { setActiveStrategy('four_lights'); setSelectedCodes([]); }}
          className={`cursor-pointer rounded-xl bg-gradient-to-br from-purple-500 to-indigo-700 p-6 text-white shadow-lg ring-offset-2 ${
            activeStrategy === 'four_lights' ? 'ring-4 ring-purple-300' : ''
          }`}
        >
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">四灯共振 AI策略</h2>
              <p className="mt-1 text-sm text-purple-100">短线偏超短 · 建议持有1至5个交易日</p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold">{fourLightsData?.count || 0}</div>
              <div className="text-sm text-purple-100">建议候选</div>
            </div>
          </div>
          <div className="rounded-lg bg-white/10 p-3">
            <div className="mb-3 flex flex-wrap gap-2 text-xs">
              {['趋势灯', '动量灯', '量价灯', '资金灯'].map((label) => (
                <span key={label} className="rounded-full bg-white/20 px-2 py-1">{label}</span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={fourLightsSession}
                onChange={(e) => setFourLightsSession(e.target.value as typeof fourLightsSession)}
                onClick={(e) => e.stopPropagation()}
                className="rounded-lg border border-white/30 bg-white/20 px-3 py-2 text-sm"
              >
                <option value="auto" className="text-gray-900">自动识别时段</option>
                <option value="morning" className="text-gray-900">早盘扫描</option>
                <option value="afternoon" className="text-gray-900">尾盘扫描</option>
              </select>
              <button
                onClick={(e) => { e.stopPropagation(); setActiveStrategy('four_lights'); void handleScanFourLights(); }}
                disabled={fourLightsScanning}
                className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-purple-700 disabled:opacity-60"
              >
                {fourLightsScanning ? '扫描中...' : '立即扫描并记录'}
              </button>
            </div>
            {fourLightsData && (
              <div className="mt-3 text-xs text-purple-100">
                {fourLightsData.session === 'morning' ? '早盘信号' : '尾盘信号'} · {fourLightsData.validation_target}
              </div>
            )}
          </div>
        </div>

        {/* 尾盘隔夜策略 */}
        <div
          onClick={() => { setActiveStrategy('overnight'); setSelectedCodes([]); }}
          className={`cursor-pointer rounded-xl bg-gradient-to-br from-rose-500 to-orange-600 p-6 text-white shadow-lg ring-offset-2 ${
            activeStrategy === 'overnight' ? 'ring-4 ring-rose-300' : ''
          }`}
        >
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">尾盘隔夜超短</h2>
              <p className="mt-1 text-sm text-rose-100">默认次日竞价/开盘卖出</p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold">{overnightData?.count || 0}</div>
              <div className="text-sm text-rose-100">隔夜候选</div>
            </div>
          </div>
          <div className="rounded-lg bg-white/10 p-3">
            <div className="mb-3 flex flex-wrap gap-2 text-xs">
              {['涨幅带', '涨停记忆', 'MA5', '量能', '流动性'].map((label) => (
                <span key={label} className="rounded-full bg-white/20 px-2 py-1">{label}</span>
              ))}
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setActiveStrategy('overnight'); void handleScanOvernight(); }}
              disabled={overnightScanning}
              className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-rose-700 disabled:opacity-60"
            >
              {overnightScanning ? '扫描中...' : '立即扫描并记录'}
            </button>
            {overnightData && (
              <div className="mt-3 text-xs text-rose-100">
                {overnightData.timing_note} · {overnightData.validation_target}
              </div>
            )}
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
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          {activeStrategy === 'strong'
            ? '强势股筛选结果'
            : activeStrategy === 'four_lights'
              ? '四灯共振建议'
              : '尾盘隔夜建议'}
        </h2>
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
            onClick={() => (
              activeStrategy === 'strong'
                ? refetch()
                : activeStrategy === 'four_lights'
                  ? handleScanFourLights()
                  : handleScanOvernight()
            )}
            disabled={
              activeStrategy === 'strong'
                ? isFetching
                : activeStrategy === 'four_lights'
                  ? fourLightsScanning
                  : overnightScanning
            }
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className={`h-5 w-5 ${(
              activeStrategy === 'strong' ? isFetching : activeStrategy === 'four_lights' ? fourLightsScanning : overnightScanning
            ) ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {(
              activeStrategy === 'strong' ? isFetching : activeStrategy === 'four_lights' ? fourLightsScanning : overnightScanning
            )
              ? '扫描中...'
              : activeStrategy === 'strong'
                ? '刷新数据'
                : '重新扫描'}
          </button>
        </div>
      </div>

      {/* 股票列表 - 根据状态渲染 */}
      {activeStrategy === 'strong' ? (isLoading ? (
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
                    评分
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
                      <div>{stock.name}</div>
                      {stock.recommended && (
                        <span className="mt-1 inline-block rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                          Top推荐
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm">
                      <div className={`font-semibold ${stock.eligible ? 'text-purple-600' : 'text-gray-400'}`}>
                        #{stock.rank} · {stock.score.toFixed(1)}
                      </div>
                      <div className="mt-1 max-w-48 text-xs text-gray-500" title={[...stock.score_reasons, ...stock.risk_flags, ...stock.hard_filter_reasons].join('；')}>
                        {stock.eligible
                          ? stock.score_reasons[0] || '数据有限'
                          : stock.hard_filter_reasons[0] || '未通过硬过滤'}
                      </div>
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
      )) : activeStrategy === 'four_lights' ? (
        <FourLightsResults
          data={fourLightsData}
          history={fourLightsHistory}
          scanning={fourLightsScanning}
          error={fourLightsError}
          selectedCodes={selectedCodes}
          onToggle={toggleSelectCode}
          onAddWatchlist={handleAddWatchlist}
          addingMap={addingMap}
          addedMap={addedMap}
        />
      ) : (
        <OvernightResults
          data={overnightData}
          history={overnightHistory}
          scanning={overnightScanning}
          error={overnightError}
          selectedCodes={selectedCodes}
          onToggle={toggleSelectCode}
          onAddWatchlist={handleAddWatchlist}
          addingMap={addingMap}
          addedMap={addedMap}
        />
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
                系统将给出1只主选、最多1只备选；机会不足时可以明确选择暂不交易。
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
                  选择参与辩论的Agent（默认核心5个，可继续增选）
                </label>
                {agents && agents.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-2">
                    <button
                      onClick={() => setSelectedAgentIds(getDefaultAgentIds(agents))}
                      className="rounded bg-purple-100 px-2 py-1 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                    >
                      核心5个
                    </button>
                    <button
                      onClick={() => setSelectedAgentIds(agents.map((agent) => agent.id))}
                      className="rounded bg-gray-100 px-2 py-1 text-xs dark:bg-gray-700"
                    >
                      全选
                    </button>
                    <button
                      onClick={() => setSelectedAgentIds([])}
                      className="rounded bg-gray-100 px-2 py-1 text-xs dark:bg-gray-700"
                    >
                      清空
                    </button>
                  </div>
                )}
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

const LIGHT_LABELS: Record<keyof FourLightsCandidate['lights'], string> = {
  trend: '趋势',
  momentum: '动量',
  volume: '量价',
  capital: '资金',
};

const LIGHT_TITLES: Record<keyof FourLightsCandidate['lights'], string> = {
  trend: '现价 > MA5 > MA10 > MA20，且 MACD DIF ≥ DEA',
  momentum: 'RSI 50–75，5日涨幅 0–18%，当日涨幅 -1.5%–6%',
  volume: '成交额≥3亿元，换手率2%–15%，预计量比1.1–3.5',
  capital: '5日累计净流入为正且至少3日流入；缺失时按当日净流入占比≥3%降级',
};

function FourLightsResults({
  data,
  history,
  scanning,
  error,
  selectedCodes,
  onToggle,
  onAddWatchlist,
  addingMap,
  addedMap,
}: {
  data: FourLightsScan | null;
  history: FourLightsRun[];
  scanning: boolean;
  error: string | null;
  selectedCodes: string[];
  onToggle: (code: string) => void;
  onAddWatchlist: (code: string, name: string) => Promise<void>;
  addingMap: Record<string, boolean>;
  addedMap: Record<string, boolean>;
}) {
  if (scanning && !data) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-12 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex flex-col items-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-500">正在扫描全市场并计算四灯，通常需要10至30秒...</p>
        </div>
      </div>
    );
  }
  if (error) {
    return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  }
  if (!data) {
    return (
      <div className="rounded-lg border border-dashed border-purple-300 bg-purple-50/50 py-14 text-center dark:border-purple-800 dark:bg-purple-900/10">
        <div className="text-lg font-medium text-purple-800 dark:text-purple-300">尚未执行四灯扫描</div>
        <p className="mt-2 text-sm text-gray-500">早盘信号在14:30后验证；尾盘信号在下一交易日验证。</p>
        {history.length > 0 && <SignalHistory history={history} strategy="four_lights" />}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-purple-200 bg-purple-50 p-4 text-sm text-purple-800 dark:border-purple-800 dark:bg-purple-900/20 dark:text-purple-200">
        本次从成交额靠前的 {data.universe_count} 只全市场高流动性股票中预筛
        {' '}{data.preselected_count} 只，得到 {data.count} 只评分靠前候选，其中
        {' '}{data.actionable_count} 只达到三灯以上可操作标准；其余仅供观察和Agent复核。
        策略周期：{data.holding_horizon}。信号时段：{data.session === 'morning' ? '早盘' : '尾盘'}；{data.validation_target}。
      </div>
      {data.stocks.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white py-12 text-center text-gray-500 dark:border-gray-700 dark:bg-gray-800">
          当前没有达到三灯共振的标的，建议暂不交易。
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.stocks.map((stock) => (
            <article key={stock.code} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-start justify-between gap-3">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selectedCodes.includes(stock.code)}
                    onChange={() => onToggle(stock.code)}
                    className="mt-1 rounded"
                  />
                  <span>
                    <span className="block text-lg font-semibold text-gray-900 dark:text-white">
                      #{stock.rank} {stock.name} <span className="text-sm text-gray-500">{stock.code}</span>
                      <span className={`ml-2 rounded-full px-2 py-0.5 text-xs ${
                        stock.actionable
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                          : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                      }`}>
                        {stock.actionable ? '可操作候选' : '观察候选'}
                      </span>
                    </span>
                    <span className="text-sm text-gray-500">
                      ¥{stock.current_price.toFixed(2)} · {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                      {' '}· 换手 {stock.turnover_rate.toFixed(2)}%
                    </span>
                  </span>
                </label>
                <div className="text-right">
                  <div className="text-2xl font-bold text-purple-600">{stock.score.toFixed(1)}</div>
                  <div className="text-xs text-gray-500">{stock.light_count}/4 灯</div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-4 gap-2">
                {(Object.keys(LIGHT_LABELS) as Array<keyof FourLightsCandidate['lights']>).map((key) => (
                  <div
                    key={key}
                    title={LIGHT_TITLES[key]}
                    className={`rounded-lg px-2 py-2 text-center text-xs font-medium ${
                      stock.lights[key]
                        ? 'border border-red-200 bg-gradient-to-b from-red-50 to-red-100 text-red-700 shadow-sm shadow-red-200 dark:border-red-800 dark:from-red-900/40 dark:to-red-900/20 dark:text-red-300'
                        : 'bg-gray-100 text-gray-400 dark:bg-gray-700'
                    }`}
                  >
                    <div className={`text-lg ${stock.lights[key] ? 'drop-shadow-[0_0_4px_rgba(220,38,38,0.65)]' : ''}`}>
                      {stock.lights[key] ? '●' : '○'}
                    </div>
                    {LIGHT_LABELS[key]}
                  </div>
                ))}
              </div>
              <div className="mt-3 text-xs text-gray-500">
                <div className="mb-1">
                  趋势参考：现价 {stock.current_price.toFixed(2)}
                  {' '}· MA5 {stock.details.ma5 ?? '--'}
                  {' '}· MA10 {stock.details.ma10 ?? '--'}
                  {' '}· MA20 {stock.details.ma20 ?? '--'}
                  {' '}· DIF {stock.details.macd_dif ?? '--'} / DEA {stock.details.macd_dea ?? '--'}
                </div>
                RSI {stock.details.rsi14 ?? '--'} · 5日涨幅 {stock.details.return_5d ?? '--'}%
                {' '}· 预计量比 {stock.details.projected_volume_ratio ?? '--'}
                {' '}· {stock.details.main_net_inflow_5d_wan != null
                  ? `5日主力净流入 ${stock.details.main_net_inflow_5d_wan} 万`
                  : stock.details.main_net_inflow_today_wan != null
                    ? `当日主力净流入 ${stock.details.main_net_inflow_today_wan} 万（降级）`
                    : '主力资金暂缺'}
              </div>
              {stock.risk_flags.length > 0 && (
                <p className="mt-2 text-xs text-amber-600">注意：{stock.risk_flags.join('；')}</p>
              )}
              <div className="mt-4 flex gap-2">
                <Link to={`/stock/${stock.code}`} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white">详情</Link>
                <button
                  onClick={() => void onAddWatchlist(stock.code, stock.name)}
                  disabled={addingMap[stock.code] || addedMap[stock.code]}
                  className="rounded bg-emerald-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {addedMap[stock.code] ? '已加入' : addingMap[stock.code] ? '加入中' : '加入自选'}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      <SignalHistory history={history} strategy="four_lights" />
    </div>
  );
}

const OVERNIGHT_CHECK_LABELS: Record<keyof OvernightCandidate['checks'], string> = {
  gain_band: '涨幅带',
  liquidity: '流动性',
  limit_memory: '涨停记忆',
  above_ma5: '站上MA5',
  volume_active: '量能',
};

function OvernightResults({
  data,
  history,
  scanning,
  error,
  selectedCodes,
  onToggle,
  onAddWatchlist,
  addingMap,
  addedMap,
}: {
  data: OvernightScan | null;
  history: FourLightsRun[];
  scanning: boolean;
  error: string | null;
  selectedCodes: string[];
  onToggle: (code: string) => void;
  onAddWatchlist: (code: string, name: string) => Promise<void>;
  addingMap: Record<string, boolean>;
  addedMap: Record<string, boolean>;
}) {
  if (scanning && !data) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-12 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex flex-col items-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-500">正在扫描尾盘隔夜候选，通常需要10至30秒...</p>
        </div>
      </div>
    );
  }
  if (error) {
    return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  }
  if (!data) {
    return (
      <div className="rounded-lg border border-dashed border-rose-300 bg-rose-50/50 py-14 text-center dark:border-rose-800 dark:bg-rose-900/10">
        <div className="text-lg font-medium text-rose-800 dark:text-rose-300">尚未执行隔夜扫描</div>
        <p className="mt-2 text-sm text-gray-500">建议14:20后扫描；默认次日竞价或开盘卖出，下一交易日验证。</p>
        {history.length > 0 && <SignalHistory history={history} strategy="overnight" />}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-200">
        本次从 {data.universe_count} 只高流动性股票中预筛 {data.preselected_count} 只，
        得到 {data.count} 只隔夜候选，其中 {data.actionable_count} 只达到可操作标准。
        持有周期：{data.holding_horizon}。{data.timing_note}；{data.validation_target}。
      </div>
      {data.stocks.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white py-12 text-center text-gray-500 dark:border-gray-700 dark:bg-gray-800">
          当前没有符合隔夜条件的标的，建议空仓观望。
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.stocks.map((stock) => (
            <article key={stock.code} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-start justify-between gap-3">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selectedCodes.includes(stock.code)}
                    onChange={() => onToggle(stock.code)}
                    className="mt-1 rounded"
                  />
                  <span>
                    <span className="block text-lg font-semibold text-gray-900 dark:text-white">
                      #{stock.rank} {stock.name} <span className="text-sm text-gray-500">{stock.code}</span>
                      <span className={`ml-2 rounded-full px-2 py-0.5 text-xs ${
                        stock.actionable
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                          : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                      }`}>
                        {stock.actionable ? '可操作隔夜' : '观察候选'}
                      </span>
                    </span>
                    <span className="text-sm text-gray-500">
                      ¥{stock.current_price.toFixed(2)} · {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                      {' '}· 换手 {stock.turnover_rate.toFixed(2)}%
                      {' '}· 流通市值 {stock.details.circulating_market_cap_yi ?? '--'} 亿
                    </span>
                  </span>
                </label>
                <div className="text-right">
                  <div className="text-2xl font-bold text-rose-600">{stock.score.toFixed(1)}</div>
                  <div className="text-xs text-gray-500">{stock.pass_count}/5 项</div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-5 gap-2">
                {(Object.keys(OVERNIGHT_CHECK_LABELS) as Array<keyof OvernightCandidate['checks']>).map((key) => (
                  <div
                    key={key}
                    className={`rounded-lg px-1 py-2 text-center text-[11px] font-medium ${
                      stock.checks[key]
                        ? 'border border-red-200 bg-gradient-to-b from-red-50 to-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-400'
                    }`}
                  >
                    <div>{stock.checks[key] ? '●' : '○'}</div>
                    {OVERNIGHT_CHECK_LABELS[key]}
                  </div>
                ))}
              </div>
              <div className="mt-3 text-xs text-gray-500">
                MA5 {stock.details.ma5 ?? '--'} · 预计量比 {stock.details.projected_volume_ratio ?? '--'}
                {' '}· 近5日涨停 {stock.details.recent_limit_days ?? 0} 次
              </div>
              <p className="mt-2 text-xs text-rose-700 dark:text-rose-300">{stock.sell_plan}</p>
              {stock.risk_flags.length > 0 && (
                <p className="mt-2 text-xs text-amber-600">注意：{stock.risk_flags.join('；')}</p>
              )}
              <div className="mt-4 flex gap-2">
                <Link to={`/stock/${stock.code}`} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white">详情</Link>
                <button
                  onClick={() => void onAddWatchlist(stock.code, stock.name)}
                  disabled={addingMap[stock.code] || addedMap[stock.code]}
                  className="rounded bg-emerald-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {addedMap[stock.code] ? '已加入' : addingMap[stock.code] ? '加入中' : '加入自选'}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      <SignalHistory history={history} strategy="overnight" />
    </div>
  );
}

function SignalHistory({
  history,
  strategy,
}: {
  history: FourLightsRun[];
  strategy: 'four_lights' | 'overnight';
}) {
  const queryClient = useQueryClient();
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const queryKey = strategy === 'four_lights' ? ['four-lights-history'] : ['overnight-history'];

  const handleDelete = async (run: FourLightsRun) => {
    const label = new Date(run.created_at).toLocaleString('zh-CN');
    if (!window.confirm(`确认删除 ${label} 的整次扫描及验证记录吗？`)) return;
    setDeletingRunId(run.run_id);
    try {
      if (strategy === 'four_lights') {
        await stockAPI.deleteFourLightsHistory(run.run_id);
      } else {
        await stockAPI.deleteOvernightHistory(run.run_id);
      }
      await queryClient.invalidateQueries({ queryKey });
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '删除历史记录失败');
    } finally {
      setDeletingRunId(null);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('确认清空当前策略的全部历史信号与验证记录吗？此操作不可恢复。')) return;
    setClearing(true);
    try {
      if (strategy === 'four_lights') {
        await stockAPI.clearFourLightsHistory();
      } else {
        await stockAPI.clearOvernightHistory();
      }
      await queryClient.invalidateQueries({ queryKey });
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '清空历史记录失败');
    } finally {
      setClearing(false);
    }
  };

  if (history.length === 0) return null;
  return (
    <section className="mt-6 text-left">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">历史信号验证</h3>
        <button
          type="button"
          onClick={() => void handleClearAll()}
          disabled={clearing}
          className="rounded border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:hover:bg-red-900/20"
        >
          {clearing ? '清空中...' : '清空全部'}
        </button>
      </div>
      <div className="space-y-2">
        {history.slice(0, 8).map((run) => (
          <div key={run.run_id} className="rounded-lg border border-gray-200 bg-white p-3 text-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-2 flex items-center justify-between gap-3 text-gray-500">
              <span>{new Date(run.created_at).toLocaleString('zh-CN')} · {run.session === 'morning' ? '早盘' : '尾盘'}</span>
              <span className="flex items-center gap-3">
                <span>{run.validation_status === 'validated' ? '已验证' : '待验证'}</span>
                <button
                  type="button"
                  onClick={() => void handleDelete(run)}
                  disabled={deletingRunId === run.run_id}
                  className="rounded border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:hover:bg-red-900/20"
                >
                  {deletingRunId === run.run_id ? '删除中...' : '删除'}
                </button>
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {run.stocks.map((stock) => (
                <span key={stock.code} className="rounded bg-gray-100 px-2 py-1 dark:bg-gray-700">
                  {stock.name} {stock.validation_return_pct == null
                    ? '待验证'
                    : `${stock.validation_return_pct >= 0 ? '+' : ''}${stock.validation_return_pct.toFixed(2)}%`}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
