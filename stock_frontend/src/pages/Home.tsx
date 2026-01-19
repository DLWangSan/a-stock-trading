import { useQuery } from '@tanstack/react-query';
import { Link, useLocation } from 'react-router-dom';
import { stockAPI } from '../services/api';
import { useWatchlistStore } from '../store/watchlistStore';
import { useEffect, useState } from 'react';
import AIAnalyzeButton from '../components/AIAnalyzeButton';

// 判断是否在交易时间
function isTradingTime(): boolean {
  const now = new Date();
  const hour = now.getHours();
  const minute = now.getMinutes();
  const day = now.getDay(); // 0=周日, 6=周六
  
  // 周末不交易
  if (day === 0 || day === 6) return false;
  
  // 交易时间：9:30-11:30, 13:00-15:00
  const morningStart = hour === 9 && minute >= 30 || hour > 9 && hour < 11 || hour === 11 && minute <= 30;
  const afternoonStart = hour >= 13 && hour < 15;
  
  return morningStart || afternoonStart;
}

// 根据交易时间返回更新间隔（毫秒）
function getRefetchInterval(): number {
  return isTradingTime() ? 5000 : 60000; // 交易时间5秒，非交易时间60秒
}

export default function Home() {
  const { items, fetchWatchlist } = useWatchlistStore();
  const [debateFilter, setDebateFilter] = useState<'active' | 'completed'>('active');
  const location = useLocation();

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  const { data: debateJobs = [], isLoading: debateLoading, refetch: refetchDebates } = useQuery({
    queryKey: ['debate-jobs', debateFilter],
    queryFn: () => stockAPI.listDebateJobs(debateFilter, 20),
    refetchInterval: 5000,
  });

  useEffect(() => {
    refetchDebates();
  }, [location.pathname, debateFilter, refetchDebates]);

  const handleStopDebate = async (jobId: string) => {
    await stockAPI.stopDebateJob(jobId);
    refetchDebates();
  };

  const handleDeleteDebate = async (jobId: string) => {
    await stockAPI.deleteDebateJob(jobId);
    refetchDebates();
  };

  // 获取三大指数数据
  const fetchIndexData = async (code: string) => {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
    const res = await fetch(`${apiUrl}/api/sina/realtime/${code}`);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    const data = await res.json();
    if (data.error) {
      throw new Error(data.message || data.error);
    }
    return data;
  };

  // 上证指数
  const { data: shIndex, isLoading: shLoading } = useQuery({
    queryKey: ['realtime', 'sh000001'],
    queryFn: () => fetchIndexData('sh000001'),
    refetchInterval: getRefetchInterval(),
    retry: 2,
  });

  // 深证成指
  const { data: szIndex, isLoading: szLoading } = useQuery({
    queryKey: ['realtime', 'sz399001'],
    queryFn: () => fetchIndexData('sz399001'),
    refetchInterval: getRefetchInterval(),
    retry: 2,
  });

  // 创业板指
  const { data: cybIndex, isLoading: cybLoading } = useQuery({
    queryKey: ['realtime', 'sz399006'],
    queryFn: () => fetchIndexData('sz399006'),
    refetchInterval: getRefetchInterval(),
    retry: 2,
  });

  return (
    <div className="space-y-6">
      {/* 三大指数卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 上证指数 */}
        <IndexCard
          title="上证指数"
          data={shIndex}
          isLoading={shLoading}
          gradientFrom="from-blue-600"
          gradientTo="to-blue-800"
        />
        
        {/* 深证成指 */}
        <IndexCard
          title="深证成指"
          data={szIndex}
          isLoading={szLoading}
          gradientFrom="from-indigo-600"
          gradientTo="to-indigo-800"
        />
        
        {/* 创业板指 */}
        <IndexCard
          title="创业板指"
          data={cybIndex}
          isLoading={cybLoading}
          gradientFrom="from-purple-600"
          gradientTo="to-purple-800"
        />
      </div>

      {/* 自选股列表 */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">自选股</h2>
          <Link
            to="/watchlist"
            className="text-blue-600 hover:text-blue-800 dark:text-blue-400"
          >
            管理自选
          </Link>
        </div>

        {items.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
            <p className="text-gray-500 dark:text-gray-400">暂无自选股</p>
            <Link
              to="/watchlist"
              className="mt-4 inline-block text-blue-600 hover:text-blue-800 dark:text-blue-400"
            >
              添加自选股
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => (
              <StockCard key={item.code} code={item.code} name={item.name} />
            ))}
          </div>
        )}
      </div>

      {/* 辩论记录 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">辩论记录</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setDebateFilter('active')}
                className={`px-3 py-1 rounded ${
                  debateFilter === 'active'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                }`}
              >
                进行中
              </button>
              <button
                onClick={() => setDebateFilter('completed')}
                className={`px-3 py-1 rounded ${
                  debateFilter === 'completed'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                }`}
              >
                已完成
              </button>
            </div>
          </div>
          {debateLoading ? (
            <div className="text-gray-500">加载中...</div>
          ) : debateJobs.length === 0 ? (
            <div className="text-gray-500">暂无任务</div>
          ) : (
            <div className="space-y-2">
              {debateJobs.map((job) => (
                <Link
                  key={job.job_id}
                  to={`/ai-debate?code=${job.code}&job_id=${job.job_id}`}
                  className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <div>
                    <div className="font-semibold text-gray-900 dark:text-white">{job.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{job.updated_at}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        job.status === 'completed'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                          : job.status === 'failed'
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                          : job.status === 'canceled'
                          ? 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                          : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
                      }`}
                    >
                      {job.status === 'completed'
                        ? '已完成'
                        : job.status === 'failed'
                        ? '失败'
                        : job.status === 'canceled'
                        ? '已终止'
                        : '进行中'}
                    </span>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        handleStopDebate(job.job_id);
                      }}
                      disabled={job.status !== 'queued' && job.status !== 'running'}
                      className="text-xs px-2 py-1 bg-yellow-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      终止
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        handleDeleteDebate(job.job_id);
                      }}
                      disabled={job.status === 'queued' || job.status === 'running'}
                      className="text-xs px-2 py-1 bg-red-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      删除
                    </button>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
    </div>
  );
}

// 指数卡片组件
function IndexCard({ 
  title, 
  data, 
  isLoading, 
  gradientFrom, 
  gradientTo 
}: { 
  title: string; 
  data: any; 
  isLoading: boolean;
  gradientFrom: string;
  gradientTo: string;
}) {
  const changePercent = data?.change_percent ?? 0;
  const changeValue = data?.current_price && data?.yesterday_close 
    ? data.current_price - data.yesterday_close 
    : 0;
  const isUp = changePercent >= 0;

  return (
    <div className={`bg-gradient-to-r ${gradientFrom} ${gradientTo} rounded-xl shadow-lg p-6 text-white transition-transform hover:scale-105`}>
      <h3 className="text-lg font-semibold mb-4 opacity-90">{title}</h3>
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
        </div>
      ) : data && data.current_price != null ? (
        <div>
          {/* 指数值 - 根据涨跌显示红绿 */}
          <div className={`text-4xl font-bold mb-2 ${isUp ? 'text-red-300' : 'text-green-300'}`}>
            {Number(data.current_price).toFixed(2)}
          </div>
          <div className="flex items-baseline gap-3 mb-3">
            {/* 涨跌幅 - 根据涨跌显示红绿 */}
            <div className={`text-2xl font-bold ${isUp ? 'text-red-200' : 'text-green-200'}`}>
              {isUp ? '+' : ''}{changePercent.toFixed(2)}%
            </div>
            {/* 涨跌值 - 根据涨跌显示红绿 */}
            <div className={`text-lg font-semibold ${isUp ? 'text-red-200' : 'text-green-200'}`}>
              {isUp ? '+' : ''}{changeValue.toFixed(2)}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs opacity-80 mt-4 pt-4 border-t border-white/20">
            <div>
              <div className="opacity-70">最高</div>
              <div className="font-semibold">{data.high?.toFixed(2) || '--'}</div>
            </div>
            <div>
              <div className="opacity-70">最低</div>
              <div className="font-semibold">{data.low?.toFixed(2) || '--'}</div>
            </div>
            <div className="col-span-2">
              <div className="opacity-70">成交量</div>
              <div className="font-semibold">
                {data.volume ? (data.volume / 10000).toFixed(0) + '万手' : '--'}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-red-200 text-sm">数据加载失败</div>
      )}
    </div>
  );
}

function StockCard({ code, name }: { code: string; name?: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['realtime', code],
    queryFn: () => stockAPI.getRealtime(code),
    refetchInterval: getRefetchInterval(),
  });

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <Link to={`/stock/${code}`} className="flex-1">
          <div>
            <h3 className="font-bold text-lg text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400">
              {name || code}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{code}</p>
          </div>
        </Link>
      </div>
      {isLoading ? (
        <div className="text-gray-400">加载中...</div>
      ) : data ? (
        <div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {data.current_price?.toFixed(2)}
          </div>
          <div
            className={`text-lg font-semibold mb-3 ${
              data.change_percent >= 0
                ? 'text-red-600 dark:text-red-400'
                : 'text-green-600 dark:text-green-400'
            }`}
          >
            {data.change_percent >= 0 ? '+' : ''}
            {data.change_percent?.toFixed(2)}%
          </div>
          <AIAnalyzeButton code={code} className="w-full text-sm" />
        </div>
      ) : (
        <div className="text-gray-400">数据获取失败</div>
      )}
    </div>
  );
}

