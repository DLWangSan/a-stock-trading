import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import { useQuery } from '@tanstack/react-query';
import { stockAPI } from '../../services/api';

interface CandlestickChartProps {
  code: string;
  buyZones?: Array<{ price: number; label: string }>;
  sellZones?: Array<{ price: number; label: string }>;
  indicatorsData?: any; // 包含MA等指标的数据
}

type KlineType = 'daily' | 'minute1' | 'minute5' | 'minute30';

export default function CandlestickChart({ code, buyZones, sellZones, indicatorsData }: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const legendRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const maSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const [klineType, setKlineType] = useState<KlineType>('daily'); // 默认显示日K

  // 获取日K线数据
  const { data: dailyKlineData } = useQuery({
    queryKey: ['daily-kline', code],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
      const response = await fetch(`${apiUrl}/api/sina/daily/${code}?count=240`);
      if (!response.ok) {
        throw new Error('Failed to fetch daily K-line data');
      }
      const result = await response.json();
      
      if (Array.isArray(result)) {
        return result;
      } else if (result && typeof result === 'object') {
        if (Array.isArray(result.data)) {
          return result.data;
        } else if (result.error) {
          throw new Error(result.message || result.error);
        } else {
          return [];
        }
      } else {
        return [];
      }
    },
    enabled: !!code && klineType === 'daily',
  });

  // 获取1分钟K线数据（分时）- 使用timeline API
  const { data: minute1KlineData } = useQuery({
    queryKey: ['minute1-kline', code],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
      const response = await fetch(`${apiUrl}/api/sina/timeline/${code}`);
      if (!response.ok) {
        throw new Error('Failed to fetch timeline data');
      }
      const result = await response.json();
      
      // timeline API返回格式: { code, data: [...], count }
      // timeline数据有price字段，需要转换为K线格式（open/high/low/close）
      let timelineData: any[] = [];
      if (Array.isArray(result)) {
        timelineData = result;
      } else if (result && typeof result === 'object') {
        if (Array.isArray(result.data)) {
          timelineData = result.data;
        } else if (result.error) {
          throw new Error(result.message || result.error);
        } else {
          return [];
        }
      } else {
        return [];
      }

      // 将timeline数据转换为K线格式
      // timeline数据格式: { datetime, price, volume, amount }
      // 转换为: { datetime, open, high, low, close, volume }
      return timelineData.map((item: any) => {
        const price = parseFloat(item.price || item.close || 0);
        // 处理时间：如果是字符串，需要转换为时间戳
        let datetime = item.datetime || item.date || item.time;
        // 如果datetime是字符串，转换为Date对象再转时间戳
        if (typeof datetime === 'string') {
          const date = new Date(datetime);
          datetime = Math.floor(date.getTime() / 1000);
        }
        return {
          datetime: datetime,
          open: price,
          high: price,
          low: price,
          close: price,
          volume: parseFloat(item.volume || 0),
          amount: parseFloat(item.amount || 0),
        };
      });
    },
    enabled: !!code && klineType === 'minute1',
    refetchInterval: klineType === 'minute1' ? 10000 : false, // 1分钟K线每10秒刷新一次
  });

  // 获取5分钟K线数据
  const { data: minute5KlineData } = useQuery({
    queryKey: ['minute5-kline', code],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
      const response = await fetch(`${apiUrl}/api/sina/minute/${code}?scale=5&datalen=240`);
      if (!response.ok) {
        throw new Error('Failed to fetch 5-minute K-line data');
      }
      const result = await response.json();
      
      if (Array.isArray(result)) {
        return result;
      } else if (result && typeof result === 'object') {
        if (Array.isArray(result.data)) {
          return result.data;
        } else if (result.error) {
          throw new Error(result.message || result.error);
        } else {
          return [];
        }
      } else {
        return [];
      }
    },
    enabled: !!code && klineType === 'minute5',
    refetchInterval: klineType === 'minute5' ? 30000 : false, // 5分钟K线每30秒刷新一次
  });

  // 获取30分钟K线数据
  const { data: minute30KlineData } = useQuery({
    queryKey: ['minute30-kline', code],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
      const response = await fetch(`${apiUrl}/api/sina/minute/${code}?scale=30&datalen=240`);
      if (!response.ok) {
        throw new Error('Failed to fetch 30-minute K-line data');
      }
      const result = await response.json();
      
      if (Array.isArray(result)) {
        return result;
      } else if (result && typeof result === 'object') {
        if (Array.isArray(result.data)) {
          return result.data;
        } else if (result.error) {
          throw new Error(result.message || result.error);
        } else {
          return [];
        }
      } else {
        return [];
      }
    },
    enabled: !!code && klineType === 'minute30',
    refetchInterval: klineType === 'minute30' ? 60000 : false, // 30分钟K线每60秒刷新一次
  });

  // 根据选择的类型获取对应的数据
  const klineData = 
    klineType === 'daily' ? dailyKlineData :
    klineType === 'minute1' ? minute1KlineData :
    klineType === 'minute5' ? minute5KlineData :
    minute30KlineData;

  useEffect(() => {
    // 检查数据格式
    if (!chartContainerRef.current || !klineData) {
      return;
    }

    // 确保klineData是数组
    const dataArray = Array.isArray(klineData) ? klineData : [];
    if (dataArray.length === 0) {
      console.warn('K线数据为空或格式错误:', klineData);
      return;
    }

    // 确保容器有宽度
    const container = chartContainerRef.current;
    if (container.clientWidth === 0) {
      console.warn('图表容器宽度为0，等待容器准备好');
      return;
    }

    let chart: IChartApi | null = null;
    let candlestickSeries: ISeriesApi<'Candlestick'> | null = null;

    try {
      chart = createChart(container, {
        layout: {
          background: { type: ColorType.Solid, color: '#ffffff' },
          textColor: '#333',
        },
        grid: {
          vertLines: { color: '#f0f0f0' },
          horzLines: { color: '#f0f0f0' },
        },
        width: container.clientWidth,
        height: 600,
        timeScale: {
          timeVisible: true,
          secondsVisible: klineType === 'minute5', // 5分钟K线显示秒数
        },
        // 设置图例位置在左上角
        localization: {
          priceFormatter: (price: number) => price.toFixed(2),
        },
      });

      // lightweight-charts v4 使用 addCandlestickSeries 方法
      // A股：涨红跌绿
      candlestickSeries = chart.addCandlestickSeries({
        upColor: '#ef5350',    // 上涨红色
        downColor: '#26a69a',  // 下跌绿色
        borderVisible: false,
        wickUpColor: '#ef5350',
        wickDownColor: '#26a69a',
        priceLineVisible: false,
        lastValueVisible: false, // 禁用右侧默认图例，使用左上角自定义图例
        // 图例位置设置
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });
    } catch (error) {
      console.error('创建图表失败:', error);
      if (chart) {
        chart.remove();
      }
      return;
    }

    if (!chart || !candlestickSeries) {
      console.error('图表或系列创建失败');
      return;
    }

    // 格式化K线数据
    // 日K线使用日期字符串格式 (YYYY-MM-DD)
    // 分钟K线使用时间戳格式 (Unix timestamp in seconds)
    const formattedData = (Array.isArray(dataArray) ? dataArray : [])
      .map((d: any) => {
        let timeValue: any = d.date || d.time || d.datetime || d.day;
        
        // 处理时间格式
        if (klineType === 'daily') {
          // 日K线：使用日期字符串格式 YYYY-MM-DD
          if (typeof timeValue === 'string') {
            timeValue = timeValue.split(' ')[0];
            if (!/^\d{4}-\d{2}-\d{2}$/.test(timeValue)) {
              return null;
            }
          } else if (typeof timeValue === 'number') {
            // 时间戳转换为日期字符串
            const date = new Date(timeValue * 1000); // 假设是秒级时间戳
            timeValue = date.toISOString().split('T')[0];
          } else {
            return null;
          }
        } else {
          // 分钟K线（1分钟/5分钟/30分钟）：使用时间戳格式（秒级）
          if (typeof timeValue === 'string') {
            // 字符串转换为时间戳
            const date = new Date(timeValue);
            if (isNaN(date.getTime())) {
              return null;
            }
            timeValue = Math.floor(date.getTime() / 1000); // 转换为秒级时间戳
          } else if (typeof timeValue === 'number') {
            // 如果已经是时间戳，确保是秒级
            if (timeValue > 1e12) {
              // 可能是毫秒级时间戳，转换为秒级
              timeValue = Math.floor(timeValue / 1000);
            }
          } else {
            return null;
          }
        }
        
        const open = parseFloat(d.open);
        const high = parseFloat(d.high);
        const low = parseFloat(d.low);
        const close = parseFloat(d.close);
        
        // 验证数据有效性
        if (
          isNaN(open) || open <= 0 ||
          isNaN(high) || high <= 0 ||
          isNaN(low) || low <= 0 ||
          isNaN(close) || close <= 0 ||
          high < low ||
          low > high ||
          open > high ||
          open < low ||
          close > high ||
          close < low
        ) {
          console.warn('无效的K线数据:', d);
          return null;
        }
        
        return {
          time: timeValue as string | number, // 日K线是string，分钟K线是number
          open: open,
          high: high,
          low: low,
          close: close,
        };
      })
      .filter((d: any) => d !== null)
      .sort((a: any, b: any) => {
        // 按时间排序：日K线用字符串比较，分钟K线用数字比较
        if (klineType === 'daily') {
          return (a.time as string).localeCompare(b.time as string);
        } else {
          return (a.time as number) - (b.time as number);
        }
      });

    if (formattedData.length > 0 && candlestickSeries) {
      try {
        candlestickSeries.setData(formattedData);
        console.log(`成功加载 ${formattedData.length} 条K线数据`, formattedData.slice(0, 3));
      } catch (error) {
        console.error('设置K线数据失败:', error, formattedData.slice(0, 3));
      }
    } else {
      console.warn('K线数据为空或格式错误，原始数据:', klineData?.slice(0, 3));
    }

    // 添加均线 - 从indicatorsData中提取MA数据（仅在日K线时显示）
    if (klineType === 'daily' && indicatorsData && Array.isArray(indicatorsData) && indicatorsData.length > 0) {
      const maConfigs = [
        { key: 'MA5', color: '#FF6B6B', title: 'MA5' },
        { key: 'MA10', color: '#4ECDC4', title: 'MA10' },
        { key: 'MA20', color: '#45B7D1', title: 'MA20' },
        { key: 'MA30', color: '#FFA07A', title: 'MA30' },
        { key: 'MA60', color: '#98D8C8', title: 'MA60' },
      ];

      maConfigs.forEach(({ key, color, title }) => {
        const maData = indicatorsData
          .map((d: any) => {
            // 使用与K线数据相同的时间处理逻辑
            let timeValue: any = d.date || d.time;
            if (typeof timeValue === 'string') {
              timeValue = timeValue.split(' ')[0];
              if (!/^\d{4}-\d{2}-\d{2}$/.test(timeValue)) {
                return null;
              }
            } else if (typeof timeValue === 'number') {
              const date = new Date(timeValue * 1000);
              timeValue = date.toISOString().split('T')[0];
            } else {
              return null;
            }

            // 提取MA值
            const maValue = parseFloat(d[key]);
            if (isNaN(maValue) || maValue <= 0) {
              return null;
            }

            return {
              time: timeValue as string,
              value: maValue,
            };
          })
          .filter((d: any) => d !== null)
          .sort((a: any, b: any) => a.time.localeCompare(b.time));

        if (maData.length > 0 && chart) {
          try {
                    // lightweight-charts v4 使用 addLineSeries
                    const maSeries = chart.addLineSeries({
                      color: color,
                      lineWidth: 2,
                      title: title,
                      priceLineVisible: false,
                      lastValueVisible: false, // 禁用右侧默认图例，使用左上角自定义图例
                      // 图例位置设置
                      priceFormat: {
                        type: 'price',
                        precision: 2,
                        minMove: 0.01,
                      },
                    });
            maSeries.setData(maData);
            maSeriesRef.current.set(key, maSeries);
            console.log(`成功添加${title}均线，共${maData.length}条数据`);
          } catch (error) {
            console.error(`添加${title}均线失败:`, error, maData.slice(0, 3));
            // 如果addLineSeries失败，尝试使用addSeries
            try {
              const maSeries = chart.addSeries('Line', {
                color: color,
                lineWidth: 2,
                title: title,
              }) as ISeriesApi<'Line'>;
              maSeries.setData(maData);
              maSeriesRef.current.set(key, maSeries);
              console.log(`使用addSeries成功添加${title}均线`);
            } catch (e2) {
              console.error(`使用addSeries也失败:`, e2);
            }
          }
        }
      });
    }

    // 自动调整时间轴范围以显示所有数据
    if (chart) {
      chart.timeScale().fitContent();
    }

    // 创建图例并放在左上角
    if (legendRef.current && chart) {
      // 更新图例内容的函数
      const updateLegend = (param: any) => {
        if (!legendRef.current) {
          return;
        }

        const legendItems: string[] = [];
        
        // 如果有crosshair数据，显示鼠标悬停位置的值
        if (param && param.seriesData && param.seriesData.size > 0) {
          // K线数据
          if (candlestickSeries && param.seriesData.has(candlestickSeries)) {
            const data = param.seriesData.get(candlestickSeries);
            if (data && 'close' in data) {
              legendItems.push(`<span style="color: #333; font-weight: bold;">价格: ${(data as any).close.toFixed(2)}</span>`);
            }
          }

          // 均线数据
          maSeriesRef.current.forEach((series, key) => {
            if (param.seriesData.has(series)) {
              const data = param.seriesData.get(series);
              if (data && 'value' in data) {
                const colors: { [key: string]: string } = {
                  'MA5': '#FF6B6B',
                  'MA10': '#4ECDC4',
                  'MA20': '#45B7D1',
                  'MA30': '#FFA07A',
                  'MA60': '#98D8C8',
                };
                const color = colors[key] || '#666';
                legendItems.push(`<span style="color: ${color};">${key}: ${(data as any).value.toFixed(2)}</span>`);
              }
            }
          });
        } else {
          // 没有crosshair时，显示最新值
          if (formattedData.length > 0) {
            const latest = formattedData[formattedData.length - 1];
            legendItems.push(`<span style="color: #333; font-weight: bold;">价格: ${latest.close.toFixed(2)}</span>`);
            
            // 显示均线最新值
            if (indicatorsData && Array.isArray(indicatorsData) && indicatorsData.length > 0) {
              const latestIndicator = indicatorsData[indicatorsData.length - 1];
              const maConfigs = [
                { key: 'MA5', color: '#FF6B6B' },
                { key: 'MA10', color: '#4ECDC4' },
                { key: 'MA20', color: '#45B7D1' },
                { key: 'MA30', color: '#FFA07A' },
                { key: 'MA60', color: '#98D8C8' },
              ];
              
              maConfigs.forEach(({ key, color }) => {
                const maValue = parseFloat(latestIndicator[key]);
                if (!isNaN(maValue) && maValue > 0) {
                  legendItems.push(`<span style="color: ${color};">${key}: ${maValue.toFixed(2)}</span>`);
                }
              });
            }
          }
        }

        if (legendItems.length > 0) {
          legendRef.current.innerHTML = legendItems.join(' | ');
        }
      };

      // 订阅crosshair移动事件
      chart.subscribeCrosshairMove(updateLegend);

      // 初始化图例显示最新值
      setTimeout(() => {
        updateLegend(null);
      }, 100);
    }

    // 添加买入卖出价格线
    if (buyZones && chart) {
      buyZones.forEach((zone) => {
        try {
          chart.createPriceLine({
            price: zone.price,
            color: '#10b981',
            lineWidth: 2,
            lineStyle: 2, // 虚线
            axisLabelVisible: true,
            title: `买入: ${zone.label}`,
          });
        } catch (error) {
          console.error('添加买入价格线失败:', error);
        }
      });
    }

    if (sellZones && chart) {
      sellZones.forEach((zone) => {
        try {
          chart.createPriceLine({
            price: zone.price,
            color: '#ef4444',
            lineWidth: 2,
            lineStyle: 2,
            axisLabelVisible: true,
            title: `卖出: ${zone.label}`,
          });
        } catch (error) {
          console.error('添加卖出价格线失败:', error);
        }
      });
    }

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    // 响应式调整
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      // 清理所有均线系列
      maSeriesRef.current.forEach((series) => {
        try {
          chart.removeSeries(series);
        } catch (e) {
          // 忽略清理错误
        }
      });
      maSeriesRef.current.clear();
      if (chart) {
        chart.remove();
      }
    };
  }, [klineData, klineType, indicatorsData, buyZones, sellZones]);

  // 检查数据格式
  if (!klineData) {
    return (
      <div className="h-[600px] flex items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-lg mb-2">加载K线数据中...</div>
          <div className="text-sm text-gray-400">请稍候</div>
        </div>
      </div>
    );
  }

  // 确保klineData是数组
  if (!Array.isArray(klineData)) {
    console.error('K线数据格式错误，期望数组，实际:', typeof klineData, klineData);
    // 尝试从对象中提取数组
    if (klineData && typeof klineData === 'object') {
      const keys = Object.keys(klineData);
      console.log('对象包含的键:', keys);
      // 如果对象有data字段且是数组，使用它
      if (Array.isArray((klineData as any).data)) {
        console.log('从klineData.data提取数组，长度:', (klineData as any).data.length);
        // 这里不能直接修改，需要在useQuery中处理
      }
    }
    return (
      <div className="h-[600px] flex items-center justify-center text-red-500">
        <div className="text-center">
          <div className="text-lg mb-2">K线数据格式错误</div>
          <div className="text-sm text-gray-400">数据类型: {typeof klineData}</div>
          <div className="text-xs text-gray-400 mt-2">
            {klineData && typeof klineData === 'object' ? `包含键: ${Object.keys(klineData).join(', ')}` : ''}
          </div>
        </div>
      </div>
    );
  }

  if (klineData.length === 0) {
    return (
      <div className="h-[600px] flex items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-lg mb-2">K线数据为空</div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-[600px]">
      {/* K线类型切换按钮 */}
      <div className="absolute top-3 right-3 z-20 flex gap-2 flex-wrap">
        <button
          onClick={() => setKlineType('daily')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            klineType === 'daily'
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          日K
        </button>
        <button
          onClick={() => setKlineType('minute1')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            klineType === 'minute1'
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          分时
        </button>
        <button
          onClick={() => setKlineType('minute5')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            klineType === 'minute5'
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          5分钟K
        </button>
        <button
          onClick={() => setKlineType('minute30')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            klineType === 'minute30'
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          30分钟K
        </button>
      </div>

      {/* 图例 - 放在左上角 */}
      <div
        ref={legendRef}
        className="absolute top-3 left-3 z-10 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm px-3 py-2 rounded-lg shadow-md text-sm font-mono"
        style={{
          pointerEvents: 'none',
        }}
      >
        {/* 初始内容会在useEffect中更新 */}
      </div>
      {/* 图表容器 */}
      <div ref={chartContainerRef} className="w-full h-full" />
    </div>
  );
}

