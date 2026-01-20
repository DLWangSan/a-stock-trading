import { useQuery } from '@tanstack/react-query';
import { stockAPI, type DebateJobStatus } from '../services/api';
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';

export default function Tasks() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const navigate = useNavigate();
  const location = useLocation();

  const { data: jobsData, isLoading, error, refetch } = useQuery({
    queryKey: ['debate-jobs', statusFilter],
    queryFn: async () => {
      const filterParam = statusFilter !== 'all' ? statusFilter : undefined;
      return await stockAPI.listDebateJobs(filterParam);
    },
    refetchInterval: 5000, // 每5秒刷新一次
  });

  // 当路由切换时刷新任务列表
  useEffect(() => {
    refetch();
  }, [location.pathname, refetch]);

  const jobs: DebateJobStatus[] = jobsData || [];

  const handleStopJob = async (jobId: string) => {
    try {
      await stockAPI.stopDebateJob(jobId);
      refetch();
    } catch (error) {
      console.error('终止任务失败:', error);
      alert('终止任务失败');
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!confirm('确定要删除这个任务吗？')) return;
    try {
      await stockAPI.deleteDebateJob(jobId);
      refetch();
    } catch (error) {
      console.error('删除任务失败:', error);
      alert('删除任务失败');
    }
  };

  const handleViewJob = (jobId: string, code?: string) => {
    const params = new URLSearchParams();
    params.set('job_id', jobId);
    if (code) params.set('code', code);
    navigate(`/ai-debate?${params.toString()}`);
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      queued: { label: '排队中', className: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300' },
      running: { label: '进行中', className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' },
      completed: { label: '已完成', className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' },
      failed: { label: '失败', className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' },
      canceled: { label: '已取消', className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' },
    };

    const config = statusConfig[status] || statusConfig.queued;
    return (
      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${config.className}`}>
        {config.label}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <h3 className="text-red-800 dark:text-red-300 font-medium">加载任务列表失败</h3>
        <p className="text-red-600 dark:text-red-400 text-sm mt-1">{String(error)}</p>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">AI 辩论任务</h1>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
            查看所有多专家辩论分析任务的状态和结果
          </p>
        </div>
      </div>

      {/* 状态筛选 */}
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => setStatusFilter('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            statusFilter === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          全部
        </button>
        <button
          onClick={() => setStatusFilter('running')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            statusFilter === 'running'
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          进行中
        </button>
        <button
          onClick={() => setStatusFilter('completed')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            statusFilter === 'completed'
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          已完成
        </button>
      </div>

      {/* 任务列表 */}
      <div className="mt-6 flow-root">
        {jobs.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg">
            <p className="text-gray-500 dark:text-gray-400">暂无任务记录</p>
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job.job_id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                        {job.name}
                      </h3>
                      {getStatusBadge(job.status)}
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <span>股票代码: {job.code}</span>
                      <span>·</span>
                      <span>创建时间: {new Date(job.created_at).toLocaleString('zh-CN')}</span>
                      <span>·</span>
                      <span>分析轮数: {job.analysis_rounds}</span>
                      <span>·</span>
                      <span>辩论轮数: {job.debate_rounds}</span>
                    </div>
                    {job.status === 'running' && (
                      <div className="mt-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${job.progress || 0}%` }}
                            ></div>
                          </div>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {job.progress || 0}%
                          </span>
                        </div>
                      </div>
                    )}
                    {job.error && (
                      <div className="mt-2 text-sm text-red-600 dark:text-red-400">
                        错误: {job.error}
                      </div>
                    )}
                  </div>
                  <div className="ml-4 flex gap-2">
                    <button
                      onClick={() => handleViewJob(job.job_id, job.code)}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                    >
                      查看详情
                    </button>
                    {job.status === 'running' && (
                      <button
                        onClick={() => handleStopJob(job.job_id)}
                        className="px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors"
                      >
                        终止
                      </button>
                    )}
                    {(job.status === 'completed' || job.status === 'failed' || job.status === 'canceled') && (
                      <button
                        onClick={() => handleDeleteJob(job.job_id)}
                        className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                      >
                        删除
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

