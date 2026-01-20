import { useEffect, useMemo, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { stockAPI } from '../services/api';
import type { DebateJobStatus, DebateStep, StockComprehensive, StockRealtime } from '../services/api';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export default function AIDebate() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const codeFromQuery = searchParams.get('code') || '';
  const jobIdFromQuery = searchParams.get('job_id') || searchParams.get('jobId') || '';
  const state = (location.state || {}) as {
    code?: string;
    agentIds?: number[];
    analysisRounds?: number;
    debateRounds?: number;
    modeLabel?: string;
  };
  const code = state.code || codeFromQuery;
  const agentIds = state.agentIds || [];
  const analysisRounds = state.analysisRounds || parseInt(searchParams.get('ar') || '3', 10);
  const debateRounds = state.debateRounds || parseInt(searchParams.get('dr') || '3', 10);
  const modeLabel = state.modeLabel || '自定义模式';

  const [jobId, setJobId] = useState(jobIdFromQuery);
  const [starting, setStarting] = useState(false);

  const { data, isLoading, isError, error } = useQuery<DebateJobStatus>({
    queryKey: ['ai-debate-status', jobId],
    queryFn: () => stockAPI.getDebateJobStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (data) => {
      if (!data) return 2000;
      return data.status === 'completed' || data.status === 'failed' ? false : 2000;
    },
  });

  useEffect(() => {
    if (!jobId && code && agentIds.length >= 2 && !starting) {
      setStarting(true);
      stockAPI
        .startDebateJob(code, agentIds, analysisRounds, debateRounds)
        .then((res) => {
          setJobId(res.job_id);
          setSearchParams({ code, job_id: res.job_id, ar: String(analysisRounds), dr: String(debateRounds) });
        })
        .catch((err) => {
          console.error('启动辩论失败:', err);
        })
        .finally(() => setStarting(false));
    }
  }, [jobId, code, agentIds, starting, setSearchParams]);

  const steps = useMemo(() => data?.steps || [], [data]);
  const reportMd = data?.report_md || '';
  const status = data?.status || (starting ? 'queued' : 'queued');

  const groupedSteps = useMemo(() => {
    const map = new Map<number, { agent_id: number; agent_name: string; items: DebateStep[] }>();
    steps.forEach((step) => {
      if (!map.has(step.agent_id)) {
        map.set(step.agent_id, { agent_id: step.agent_id, agent_name: step.agent_name, items: [] });
      }
      map.get(step.agent_id)?.items.push(step);
    });
    return Array.from(map.values());
  }, [steps]);

  const reportHtml = useMemo(() => {
    if (!reportMd) return '';
    const raw = marked.parse(reportMd, { gfm: true, breaks: true });
    return DOMPurify.sanitize(raw as string);
  }, [reportMd]);

  useEffect(() => {
    if (!code && data?.code) {
      setSearchParams({ code: data.code, job_id: jobId });
    }
  }, [code, data?.code, jobId, setSearchParams]);

  const handleExport = () => {
    if (!reportMd) return;
    const blob = new Blob([reportMd], { type: 'text/markdown;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai_report_${code}.md`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (!code && !jobId) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="text-center text-gray-500">
          缺少股票代码或任务ID，请从AI分析入口进入。
        </div>
      </div>
    );
  }

  const displayCode = code || data?.code || '';
  const displayName = data?.name || displayCode;
  const isMultiSelect = (data?.meta?.mode === 'multi_select') || displayCode.includes(',');
  const multiCodes = data?.meta?.codes || (displayCode.includes(',') ? displayCode.split(',') : []);

  const effectiveCode = !isMultiSelect ? displayCode : '';
  const { data: realtimeData } = useQuery<StockRealtime>({
    queryKey: ['realtime', effectiveCode],
    queryFn: () => stockAPI.getRealtime(effectiveCode),
    enabled: !!effectiveCode,
  });

  const { data: comprehensiveData } = useQuery<StockComprehensive>({
    queryKey: ['comprehensive', effectiveCode],
    queryFn: () => stockAPI.getComprehensive(effectiveCode),
    enabled: !!effectiveCode,
  });

  const { data: sentimentData } = useQuery({
    queryKey: ['sentiment', effectiveCode],
    queryFn: () => stockAPI.getSentiment(effectiveCode, 7),
    enabled: !!effectiveCode,
  });

  const formatNumber = (value?: number, digits: number = 2) => {
    if (value == null || Number.isNaN(value)) return '--';
    return Number(value).toFixed(digits);
  };

  const handleStop = async () => {
    if (!jobId) return;
    await stockAPI.stopDebateJob(jobId);
  };

  const handleDelete = async () => {
    if (!jobId) return;
    await stockAPI.deleteDebateJob(jobId);
    window.location.href = '/';
  };

  return (
    <div className="space-y-6">
      <style>
        {`
          @keyframes indeterminate {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(0%); }
            100% { transform: translateX(100%); }
          }
          .markdown-body h1, .markdown-body h2, .markdown-body h3 {
            font-weight: 700;
            margin: 0.75rem 0 0.5rem;
          }
          .markdown-body p { margin: 0.5rem 0; }
          .markdown-body ul { list-style: disc; padding-left: 1.25rem; margin: 0.5rem 0; }
          .markdown-body ol { list-style: decimal; padding-left: 1.25rem; margin: 0.5rem 0; }
          .markdown-body table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; }
          .markdown-body th, .markdown-body td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; }
          .markdown-body blockquote { border-left: 3px solid #cbd5e1; padding-left: 0.75rem; color: #6b7280; margin: 0.5rem 0; }
        `}
      </style>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            TradingAgents 辩论分析 - {displayName || '未知股票'}
          </h1>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {modeLabel} · 思考{analysisRounds} / 辩论{debateRounds}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleStop}
            disabled={!jobId || status === 'completed' || status === 'failed' || status === 'canceled'}
            className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            终止
          </button>
          <button
            onClick={handleDelete}
            disabled={!jobId || status === 'queued' || status === 'running'}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            删除
          </button>
        </div>
      </div>

      {/* 进度条 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="mb-2 text-sm text-gray-500 dark:text-gray-400">
          进度提示：多轮分析与辩论可能耗时较长（约10分钟），可离开页面后稍后回来查看
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
          {status === 'completed' ? (
            <div className="h-3 bg-gradient-to-r from-purple-500 to-purple-700" style={{ width: '100%' }} />
          ) : (
            <div
              className="h-3 w-1/2 bg-gradient-to-r from-purple-400 to-purple-700"
              style={{ animation: 'indeterminate 1.6s ease-in-out infinite' }}
            />
          )}
        </div>
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {status === 'completed'
            ? '分析完成'
            : status === 'failed'
            ? '分析失败'
            : status === 'canceled'
            ? '已终止'
            : '分析中...'}
        </div>
      </div>

      {/* 思考过程 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          专家思考过程（可滚动）
        </h2>
        <div className="max-h-[420px] overflow-y-auto space-y-3 border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-900">
          {isLoading && (
            <div className="text-gray-500">分析中，内容将自动加载...</div>
          )}
          {isError && (
            <div className="text-red-500">分析失败：{(error as Error).message}</div>
          )}
          {data?.error && (
            <div className="text-red-500">分析失败：{data.error}</div>
          )}
          {!isLoading && groupedSteps.length === 0 && !isError && (
            <div className="text-gray-500">暂无内容</div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {groupedSteps.map((group) => (
              <div key={group.agent_id} className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                <div className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  {group.agent_name}
                </div>
                <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                  {group.items.map((step, index) => (
                    <div key={`${step.phase}-${step.round}-${step.agent_id}-${index}`} className="border border-gray-100 dark:border-gray-700 rounded p-2">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                          {step.phase === 'analysis' ? '分析' : '辩论'} · 第{step.round}轮
                        </span>
                        <span className="text-xs text-gray-400">{step.timestamp}</span>
                      </div>
                      <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                        {step.content}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 基础信息 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">基础信息（接口数据）</h2>
        {isMultiSelect ? (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">多选一候选股票</div>
            <div className="flex flex-wrap gap-2">
              {multiCodes.length > 0 ? (
                multiCodes.map((item) => (
                  <span key={item} className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                    {item}
                  </span>
                ))
              ) : (
                <span className="text-sm text-gray-500">暂无候选股票列表</span>
              )}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-3">
              多选一模式不展示单只股票的实时与舆情面板，请查看最终报告中的综合结论。
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">实时行情</div>
              <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                <div>名称：{realtimeData?.name || displayName}</div>
                <div>现价：{formatNumber(realtimeData?.current_price)}</div>
                <div>涨跌幅：{formatNumber(realtimeData?.change_percent)}%</div>
                <div>昨收：{formatNumber(realtimeData?.yesterday_close)}</div>
                <div>开盘：{formatNumber(realtimeData?.open)}</div>
                <div>最高：{formatNumber(realtimeData?.high)}</div>
                <div>最低：{formatNumber(realtimeData?.low)}</div>
                <div>成交量：{realtimeData?.volume ? `${formatNumber(realtimeData.volume / 10000, 0)}万手` : '--'}</div>
                <div>成交额：{realtimeData?.amount ? `${formatNumber(realtimeData.amount / 100000000, 2)}亿` : '--'}</div>
              </div>
            </div>
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">资金与基本面</div>
              <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                <div>主力净流入：{comprehensiveData?.money_flow?.main_net_inflow != null ? `${formatNumber(comprehensiveData.money_flow.main_net_inflow, 2)}万` : '--'}</div>
                <div>超大单净流入：{comprehensiveData?.money_flow?.super_large_net_inflow != null ? `${formatNumber(comprehensiveData.money_flow.super_large_net_inflow, 2)}万` : '--'}</div>
                <div>PE：{formatNumber(comprehensiveData?.fundamental?.pe)}</div>
                <div>PB：{formatNumber(comprehensiveData?.fundamental?.pb)}</div>
                <div>PS：{formatNumber(comprehensiveData?.fundamental?.ps)}</div>
                <div>ROE：{formatNumber(comprehensiveData?.fundamental?.roe)}%</div>
                <div>EPS：{formatNumber(comprehensiveData?.fundamental?.eps)}</div>
                <div>BPS：{formatNumber(comprehensiveData?.fundamental?.bps)}</div>
              </div>
            </div>
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">行业对比</div>
              <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                <div>行业：{comprehensiveData?.industry_comparison?.industry_name || '--'}</div>
                <div>行业排名：{comprehensiveData?.industry_comparison?.rank != null ? `${comprehensiveData.industry_comparison.rank}` : '--'}</div>
                <div>行业平均涨跌：{formatNumber(comprehensiveData?.industry_comparison?.avg_change_percent)}%</div>
                <div>行业总数：{comprehensiveData?.industry_comparison?.total != null ? `${comprehensiveData.industry_comparison.total}` : '--'}</div>
              </div>
            </div>
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">舆情摘要（近7天）</div>
              <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                <div>新闻数量：{sentimentData?.news?.count ?? '--'}</div>
                <div>帖子数量：{sentimentData?.posts?.total_count ?? '--'}</div>
                <div>最新帖子：{sentimentData?.posts?.latest_count ?? '--'}</div>
                <div>热门帖子：{sentimentData?.posts?.hot_count ?? '--'}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 最终报告 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">研究报告（Markdown）</h2>
          <button
            onClick={handleExport}
            disabled={!reportMd}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            导出Markdown
          </button>
        </div>
        {status !== 'completed' ? (
          <div className="text-gray-500">报告生成中...</div>
        ) : reportHtml ? (
          <div
            className="markdown-body bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-700"
            dangerouslySetInnerHTML={{ __html: reportHtml }}
          />
        ) : (
          <div className="text-gray-500">暂无报告</div>
        )}
      </div>
    </div>
  );
}

