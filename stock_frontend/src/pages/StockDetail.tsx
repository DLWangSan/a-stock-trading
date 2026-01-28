import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { stockAPI } from '../services/api';
import CandlestickChart from '../components/charts/CandlestickChart';
import AIAnalyzeButton from '../components/AIAnalyzeButton';

// 现代化的加载动画组件
function LoadingSpinner({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative w-16 h-16">
        <div className="absolute top-0 left-0 w-full h-full border-4 border-blue-200 rounded-full"></div>
        <div className="absolute top-0 left-0 w-full h-full border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
      </div>
      <p className="mt-4 text-gray-500 dark:text-gray-400">{text}</p>
    </div>
  );
}

export default function StockDetail() {
  const { code } = useParams<{ code: string }>();
  const codeStr = code || '';

  // 分别加载不同数据，先显示已加载的
  const { data: realtimeData, isLoading: realtimeLoading } = useQuery({
    queryKey: ['realtime', codeStr],
    queryFn: () => stockAPI.getRealtime(codeStr),
    enabled: !!codeStr,
  });

  const { data: comprehensiveData, isLoading: comprehensiveLoading } = useQuery({
    queryKey: ['comprehensive', codeStr],
    queryFn: () => stockAPI.getComprehensive(codeStr),
    enabled: !!codeStr,
  });

  const { data: sentimentData, isLoading: sentimentLoading } = useQuery({
    queryKey: ['sentiment', codeStr],
    queryFn: () => stockAPI.getSentiment(codeStr, 7),
    enabled: !!codeStr,
  });

  // 获取日K线数据（包含技术指标）
  const { data: dailyData, isLoading: dailyLoading } = useQuery({
    queryKey: ['daily', codeStr],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
      const response = await fetch(`${apiUrl}/api/sina/comprehensive_with_indicators/${codeStr}`);
      if (!response.ok) {
        throw new Error('Failed to fetch daily data');
      }
      const result = await response.json();
      return result;
    },
    enabled: !!codeStr,
  });

  // 获取历史资金流向
  const { data: moneyFlowHistory, isLoading: moneyFlowHistoryLoading } = useQuery({
    queryKey: ['moneyFlowHistory', codeStr],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
      const response = await fetch(`${apiUrl}/api/sina/money_flow/history/${codeStr}?days=60`);
      if (!response.ok) {
        throw new Error('Failed to fetch money flow history');
      }
      const result = await response.json();
      const data = result.data || [];
      // 按日期倒序排列（最新的在前）
      return data.sort((a: any, b: any) => {
        const dateA = new Date(a.date).getTime();
        const dateB = new Date(b.date).getTime();
        return dateB - dateA; // 倒序
      });
    },
    enabled: !!codeStr,
  });

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${
            (realtimeData?.change_percent ?? 0) >= 0
              ? 'text-red-600 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
          }`}>
            {realtimeData?.name || comprehensiveData?.realtime?.name || codeStr}
          </h1>
          <p className="text-gray-500 dark:text-gray-400">{codeStr}</p>
        </div>
        <AIAnalyzeButton code={codeStr} />
      </div>

      {/* 实时行情卡片 */}
      {realtimeLoading && comprehensiveLoading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <LoadingSpinner text="加载实时行情..." />
        </div>
      ) : (realtimeData || comprehensiveData?.realtime) ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">实时行情</h2>
          {/* 优先使用comprehensiveData中的实时数据（包含换手率），如果没有则使用realtimeData */}
          {(() => {
            // 优先使用comprehensiveData.realtime（包含换手率），否则使用realtimeData
            const displayData = comprehensiveData?.realtime || realtimeData;
            return (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">当前价</div>
                  <div className={`text-2xl font-bold ${
                    (displayData?.change_percent ?? 0) >= 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-green-600 dark:text-green-400'
                  }`}>
                    {displayData?.current_price?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">涨跌幅</div>
                  <div
                    className={`text-2xl font-bold ${
                      (displayData?.change_percent ?? 0) >= 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-green-400'
                    }`}
                  >
                    {(displayData?.change_percent ?? 0) >= 0 ? '+' : ''}
                    {displayData?.change_percent?.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">最高</div>
                  <div className="text-xl font-semibold text-gray-900 dark:text-white">
                    {displayData?.high?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">最低</div>
                  <div className="text-xl font-semibold text-gray-900 dark:text-white">
                    {displayData?.low?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">成交量</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {displayData?.volume ? (displayData.volume / 10000).toFixed(0) + '万手' : '--'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">成交额</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {displayData?.amount ? (displayData.amount / 100000000).toFixed(2) + '亿' : '--'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">换手率</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {displayData?.turnover_rate != null && displayData.turnover_rate !== undefined 
                      ? displayData.turnover_rate.toFixed(2) + '%' 
                      : '--'}
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      ) : null}

      {/* K线图 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">K线图</h2>
        {dailyLoading ? (
          <LoadingSpinner text="加载K线数据..." />
        ) : (
          <CandlestickChart 
            code={codeStr} 
            indicatorsData={
              dailyData?.raw_data?.daily || 
              dailyData?.daily || 
              comprehensiveData?.daily || 
              null
            }
          />
        )}
      </div>

      {/* 技术指标 */}
      {comprehensiveData?.indicators && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">技术指标</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {comprehensiveData.indicators.MA && Object.entries(comprehensiveData.indicators.MA).map(([key, value]: [string, any]) => (
              <div key={key}>
                <div className="text-sm text-gray-500 dark:text-gray-400">{key}</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {typeof value === 'number' ? value.toFixed(2) : value}
                </div>
              </div>
            ))}
            {comprehensiveData.indicators.RSI && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">RSI</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {comprehensiveData.indicators.RSI.toFixed(2)}
                </div>
              </div>
            )}
            {comprehensiveData.indicators.MACD && (
              <>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">MACD DIF</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {comprehensiveData.indicators.MACD.DIF?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">MACD DEA</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {comprehensiveData.indicators.MACD.DEA?.toFixed(2)}
                  </div>
                </div>
              </>
            )}
            {comprehensiveData.indicators.KDJ && (
              <>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">KDJ K</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {comprehensiveData.indicators.KDJ.K?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">KDJ D</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {comprehensiveData.indicators.KDJ.D?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">KDJ J</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">
                    {comprehensiveData.indicators.KDJ.J?.toFixed(2)}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* 基本面数据 */}
      {comprehensiveData?.fundamental && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">基本面数据</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {comprehensiveData.fundamental.pe && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">市盈率(PE)</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {comprehensiveData.fundamental.pe.toFixed(2)}
                </div>
              </div>
            )}
            {comprehensiveData.fundamental.pb && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">市净率(PB)</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {comprehensiveData.fundamental.pb.toFixed(2)}
                </div>
              </div>
            )}
            {comprehensiveData.fundamental.roe && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">净资产收益率(ROE)</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {comprehensiveData.fundamental.roe.toFixed(2)}%
                </div>
              </div>
            )}
            {comprehensiveData.fundamental.eps && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">每股收益(EPS)</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {comprehensiveData.fundamental.eps.toFixed(2)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 行业对比 */}
      {comprehensiveData?.industry_comparison && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">行业对比</h2>
          <div className="space-y-2">
            {comprehensiveData.industry_comparison.industry_name && (
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">行业：</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                  {comprehensiveData.industry_comparison.industry_name}
                </span>
              </div>
            )}
            {comprehensiveData.industry_comparison.rank && (
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">行业排名：</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                  第 {comprehensiveData.industry_comparison.rank} 名
                </span>
              </div>
            )}
            {comprehensiveData.industry_comparison.industry_avg_change && (
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">行业平均涨跌幅：</span>
                <span className={`text-sm font-semibold ${
                  comprehensiveData.industry_comparison.industry_avg_change >= 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {comprehensiveData.industry_comparison.industry_avg_change >= 0 ? '+' : ''}
                  {comprehensiveData.industry_comparison.industry_avg_change.toFixed(2)}%
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 今日资金流向 */}
      {comprehensiveData?.money_flow && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">今日资金流向</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {comprehensiveData.money_flow.main_net_inflow != null && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">主力净流入</div>
                <div className={`text-lg font-semibold ${
                  comprehensiveData.money_flow.main_net_inflow >= 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {comprehensiveData.money_flow.main_net_inflow >= 0 ? '+' : ''}
                  {comprehensiveData.money_flow.main_net_inflow.toFixed(2)}万
                </div>
                {comprehensiveData.money_flow.main_net_ratio && (
                  <div className="text-xs text-gray-400 mt-1">
                    占比: {comprehensiveData.money_flow.main_net_ratio.toFixed(2)}%
                  </div>
                )}
              </div>
            )}
            {comprehensiveData.money_flow.super_large_net_inflow != null && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">超大单净流入</div>
                <div className={`text-lg font-semibold ${
                  comprehensiveData.money_flow.super_large_net_inflow >= 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {comprehensiveData.money_flow.super_large_net_inflow >= 0 ? '+' : ''}
                  {comprehensiveData.money_flow.super_large_net_inflow.toFixed(2)}万
                </div>
                {comprehensiveData.money_flow.super_large_net_ratio && (
                  <div className="text-xs text-gray-400 mt-1">
                    占比: {comprehensiveData.money_flow.super_large_net_ratio.toFixed(2)}%
                  </div>
                )}
              </div>
            )}
            {comprehensiveData.money_flow.large_net_inflow != null && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">大单净流入</div>
                <div className={`text-lg font-semibold ${
                  comprehensiveData.money_flow.large_net_inflow >= 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {comprehensiveData.money_flow.large_net_inflow >= 0 ? '+' : ''}
                  {comprehensiveData.money_flow.large_net_inflow.toFixed(2)}万
                </div>
                {comprehensiveData.money_flow.large_net_ratio && (
                  <div className="text-xs text-gray-400 mt-1">
                    占比: {comprehensiveData.money_flow.large_net_ratio.toFixed(2)}%
                  </div>
                )}
              </div>
            )}
            {comprehensiveData.money_flow.medium_net_inflow != null && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">中单净流入</div>
                <div className={`text-lg font-semibold ${
                  comprehensiveData.money_flow.medium_net_inflow >= 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {comprehensiveData.money_flow.medium_net_inflow >= 0 ? '+' : ''}
                  {comprehensiveData.money_flow.medium_net_inflow.toFixed(2)}万
                </div>
              </div>
            )}
            {comprehensiveData.money_flow.small_net_inflow != null && (
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">小单净流入</div>
                <div className={`text-lg font-semibold ${
                  comprehensiveData.money_flow.small_net_inflow >= 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {comprehensiveData.money_flow.small_net_inflow >= 0 ? '+' : ''}
                  {comprehensiveData.money_flow.small_net_inflow.toFixed(2)}万
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 历史资金流向 */}
      {moneyFlowHistoryLoading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <LoadingSpinner text="加载历史资金流向..." />
        </div>
      ) : moneyFlowHistory && moneyFlowHistory.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">历史资金流向（近60天）</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400">日期</th>
                  <th className="text-right py-2 px-3 text-gray-500 dark:text-gray-400">主力净流入</th>
                  <th className="text-right py-2 px-3 text-gray-500 dark:text-gray-400">超大单</th>
                  <th className="text-right py-2 px-3 text-gray-500 dark:text-gray-400">大单</th>
                  <th className="text-right py-2 px-3 text-gray-500 dark:text-gray-400">收盘价</th>
                  <th className="text-right py-2 px-3 text-gray-500 dark:text-gray-400">涨跌幅</th>
                </tr>
              </thead>
              <tbody>
                {moneyFlowHistory.slice(0, 30).map((item: any, index: number) => (
                  <tr key={index} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-2 px-3 text-gray-900 dark:text-white">{item.date}</td>
                    <td className={`py-2 px-3 text-right ${
                      (item.main_net_inflow || 0) >= 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-green-400'
                    }`}>
                      {item.main_net_inflow != null ? (item.main_net_inflow >= 0 ? '+' : '') + item.main_net_inflow.toFixed(2) + '万' : '--'}
                    </td>
                    <td className={`py-2 px-3 text-right ${
                      (item.super_large_net_inflow || 0) >= 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-green-400'
                    }`}>
                      {item.super_large_net_inflow != null ? (item.super_large_net_inflow >= 0 ? '+' : '') + item.super_large_net_inflow.toFixed(2) + '万' : '--'}
                    </td>
                    <td className={`py-2 px-3 text-right ${
                      (item.large_net_inflow || 0) >= 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-green-400'
                    }`}>
                      {item.large_net_inflow != null ? (item.large_net_inflow >= 0 ? '+' : '') + item.large_net_inflow.toFixed(2) + '万' : '--'}
                    </td>
                    <td className="py-2 px-3 text-right text-gray-900 dark:text-white">
                      {item.close != null ? item.close.toFixed(2) : '--'}
                    </td>
                    <td className={`py-2 px-3 text-right ${
                      (item.change_percent || 0) >= 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-green-400'
                    }`}>
                      {item.change_percent != null ? (item.change_percent >= 0 ? '+' : '') + item.change_percent.toFixed(2) + '%' : '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* 舆情数据 */}
      {sentimentLoading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <LoadingSpinner text="加载舆情数据..." />
        </div>
      ) : sentimentData ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">舆情数据</h2>
          
          {/* 新闻 */}
          {sentimentData.news && sentimentData.news.list && sentimentData.news.list.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">相关新闻</h3>
              <div className="space-y-3">
                {sentimentData.news.list.slice(0, 10).map((news: any, index: number) => (
                  <div key={index} className="border-b border-gray-200 dark:border-gray-700 pb-3">
                    <a
                      href={news.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      <div className="font-medium">{news.title}</div>
                    </a>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {news.source} · {news.time}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 股吧帖子 */}
          {sentimentData.posts && (
            <>
              {sentimentData.posts.latest_posts && sentimentData.posts.latest_posts.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">最新帖子</h3>
                  <div className="space-y-3">
                    {sentimentData.posts.latest_posts.slice(0, 10).map((post: any, index: number) => (
                      <div key={index} className="border-b border-gray-200 dark:border-gray-700 pb-3">
                        <div className="font-medium text-gray-900 dark:text-white">{post.title}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          {post.author} · {post.time} · 阅读 {post.read_count}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {sentimentData.posts.hot_posts && sentimentData.posts.hot_posts.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">热门帖子</h3>
                  <div className="space-y-3">
                    {sentimentData.posts.hot_posts.slice(0, 10).map((post: any, index: number) => (
                      <div key={index} className="border-b border-gray-200 dark:border-gray-700 pb-3">
                        <div className="font-medium text-gray-900 dark:text-white">{post.title}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          {post.author} · {post.time} · 阅读 {post.read_count}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      ) : null}

      {/* Agent分析区域（待实现） */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">AI分析</h2>
        <p className="text-gray-500 dark:text-gray-400">Agent分析功能开发中...</p>
      </div>
    </div>
  );
}
