import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useWatchlistStore } from '../store/watchlistStore';
import { stockAPI } from '../services/api';
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

export default function Watchlist() {
  const { items, loading, addStock, removeStock } = useWatchlistStore();
  const [codeInput, setCodeInput] = useState('');
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    const code = codeInput.trim();
    if (!code || code.length !== 6) {
      alert('请输入6位股票代码');
      return;
    }

    setAdding(true);
    try {
      // 先获取股票名称
      const realtime = await stockAPI.getRealtime(code);
      await addStock(code, realtime.name);
      setCodeInput('');
    } catch (error) {
      alert(`添加失败: ${(error as Error).message}`);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">自选股管理</h1>

      {/* 添加自选股 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">添加自选股</h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)}
            placeholder="输入6位股票代码，如：000001"
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            maxLength={6}
          />
          <button
            onClick={handleAdd}
            disabled={adding}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {adding ? '添加中...' : '添加'}
          </button>
        </div>
      </div>

      {/* 自选股列表 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">我的自选</h2>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : items.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无自选股</div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <WatchlistItem
                  key={item.id}
                  item={item}
                  onRemove={() => removeStock(item.code)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WatchlistItem({ item, onRemove }: { item: any; onRemove: () => void }) {
  // 获取实时行情数据
  const { data: realtimeData, isLoading } = useQuery({
    queryKey: ['realtime', item.code],
    queryFn: () => stockAPI.getRealtime(item.code),
    refetchInterval: getRefetchInterval(),
    enabled: !!item.code,
  });

  const changePercent = realtimeData?.change_percent ?? 0;
  const changeValue = realtimeData?.current_price && realtimeData?.yesterday_close
    ? realtimeData.current_price - realtimeData.yesterday_close
    : 0;
  const isUp = changePercent >= 0;

  return (
    <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
      <Link to={`/stock/${item.code}`} className="flex-1 flex items-center justify-between">
        <div className="flex-1">
          <div className="font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400">
            {item.name || item.code}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">{item.code}</div>
        </div>
        
        {/* 实时行情信息 */}
        {isLoading ? (
          <div className="text-gray-400 text-sm">加载中...</div>
        ) : realtimeData ? (
          <div className="flex items-center gap-4 text-right">
            <div>
              <div className={`text-lg font-bold ${isUp ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                {realtimeData.current_price?.toFixed(2) || '--'}
              </div>
            </div>
            <div>
              <div className={`text-sm font-semibold ${isUp ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                {isUp ? '+' : ''}{changePercent.toFixed(2)}%
              </div>
              <div className={`text-xs ${isUp ? 'text-red-500 dark:text-red-500' : 'text-green-500 dark:text-green-500'}`}>
                {isUp ? '+' : ''}{changeValue.toFixed(2)}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-gray-400 text-sm">--</div>
        )}
      </Link>
      
      <div className="ml-4 flex items-center gap-2">
        <AIAnalyzeButton code={item.code} className="text-sm px-3 py-1.5" />
        <button
          onClick={(e) => {
            e.preventDefault();
            onRemove();
          }}
          className="px-4 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
        >
          删除
        </button>
      </div>
    </div>
  );
}

