import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { stockAPI } from '../services/api';
import type { Agent } from '../services/api';

const AI_PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'qwen', label: '通义千问' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'siliconflow', label: '硅基流动' },
];

export default function Settings() {
  const [apiBaseURL, setApiBaseURL] = useState('http://127.0.0.1:5000');
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // 加载配置
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const url = await stockAPI.getConfig('api_base_url');
      if (url) setApiBaseURL(url);

      const provider = await stockAPI.getConfig('default_ai_provider');
      if (provider) {
        setSelectedProvider(provider);
        // 加载该provider的API key
        const key = await stockAPI.getConfig(`${provider}_api_key`);
        if (key) setApiKey(key);
        // 加载该provider的模型
        const model = await stockAPI.getConfig(`${provider}_model`);
        if (model) setSelectedModel(model);
      }
    } catch (error) {
      console.error('加载配置失败:', error);
    }
  };

  // 当provider改变时，加载对应的key和模型
  useEffect(() => {
    const loadProviderConfig = async () => {
      try {
        const key = await stockAPI.getConfig(`${selectedProvider}_api_key`);
        setApiKey(key || '');
        const model = await stockAPI.getConfig(`${selectedProvider}_model`);
        setSelectedModel(model || '');
      } catch (error) {
        console.error('加载provider配置失败:', error);
      }
    };
    loadProviderConfig();
  }, [selectedProvider]);

  // 获取模型列表
  const { data: models, isLoading: modelsLoading, refetch: refetchModels } = useQuery({
    queryKey: ['ai-models', selectedProvider, apiKey],
    queryFn: () => stockAPI.getAIModels(selectedProvider, apiKey || undefined),
    enabled: !!selectedProvider && !!apiKey,
  });

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      // 保存后端地址
      await stockAPI.setConfig('api_base_url', apiBaseURL);
      stockAPI.setBaseURL(apiBaseURL);

      // 保存AI服务配置
      await stockAPI.setConfig('default_ai_provider', selectedProvider);
      await stockAPI.setConfig(`${selectedProvider}_api_key`, apiKey);
      if (selectedModel) {
        await stockAPI.setConfig(`${selectedProvider}_model`, selectedModel);
      }

      setMessage('配置保存成功！');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage(`保存失败: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!apiKey) {
      setTestResult({ success: false, message: '请先输入API Key' });
      return;
    }

    setTesting(true);
    setTestResult(null);
    try {
      const result = await stockAPI.testAIConnection(
        selectedProvider,
        apiKey,
        selectedModel || undefined
      );
      setTestResult(result);
      // 如果测试成功，刷新模型列表
      if (result.success) {
        refetchModels();
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: `测试失败: ${(error as Error).message}`,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">系统配置</h1>

      {/* 后端地址配置 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">后端地址</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API基础地址
            </label>
            <input
              type="text"
              value={apiBaseURL}
              onChange={(e) => setApiBaseURL(e.target.value)}
              placeholder="http://127.0.0.1:5000"
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* AI服务配置 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">AI服务配置</h2>
        <div className="space-y-4">
          {/* 服务商选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              AI服务商
            </label>
            <select
              value={selectedProvider}
              onChange={(e) => {
                setSelectedProvider(e.target.value);
                setApiKey('');
                setSelectedModel('');
              }}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            >
              {AI_PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {/* API Key输入 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API Key
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setSelectedModel(''); // 清空模型选择
                }}
                placeholder={`输入${AI_PROVIDERS.find(p => p.value === selectedProvider)?.label}的API Key`}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              />
              <button
                onClick={handleTest}
                disabled={testing || !apiKey}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {testing ? '测试中...' : '测试连接'}
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !apiKey}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {saving ? '保存中...' : '保存AI配置'}
              </button>
            </div>
            {testResult && (
              <div
                className={`mt-2 p-3 rounded-lg text-sm ${
                  testResult.success
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                }`}
              >
                {testResult.message}
              </div>
            )}
          </div>

          {/* 模型选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              模型选择
            </label>
            {modelsLoading ? (
              <div className="text-gray-500 dark:text-gray-400">加载模型中...</div>
            ) : models && models.length > 0 ? (
              <div className="flex gap-2">
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                >
                  <option value="">请选择模型</option>
                  {models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => refetchModels()}
                  disabled={!apiKey}
                  className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 whitespace-nowrap"
                >
                  刷新模型
                </button>
              </div>
            ) : (
              <div className="text-gray-500 dark:text-gray-400">
                请先输入API Key并测试连接以加载模型列表
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Agent配置 */}
      <AgentConfigSection />

      {/* 保存按钮 */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>

      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.includes('成功')
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
          }`}
        >
          {message}
        </div>
      )}
    </div>
  );
}

// Agent配置组件
function AgentConfigSection() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [prompt, setPrompt] = useState('');

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const data = await stockAPI.getAgents(false);
      setAgents(data);
    } catch (error) {
      console.error('加载Agents失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setPrompt(agent.prompt);
  };

  const handleSavePrompt = async () => {
    if (!editingAgent) return;

    try {
      await stockAPI.updateAgent(editingAgent.id, { prompt });
      setEditingAgent(null);
      setPrompt('');
      loadAgents();
    } catch (error) {
      alert(`保存失败: ${(error as Error).message}`);
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="text-center py-8 text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Agent配置</h2>
      <div className="space-y-4">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white">{agent.name}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  类型: {agent.type} | 状态: {agent.enabled ? '启用' : '禁用'}
                </p>
              </div>
              <button
                onClick={() => handleEdit(agent)}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                编辑提示词
              </button>
            </div>
            {editingAgent?.id === agent.id ? (
              <div className="mt-4 space-y-2">
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={8}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white font-mono text-sm"
                  placeholder="输入Agent提示词..."
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleSavePrompt}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    保存
                  </button>
                  <button
                    onClick={() => {
                      setEditingAgent(null);
                      setPrompt('');
                    }}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-2 text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono bg-gray-50 dark:bg-gray-900 p-3 rounded">
                {agent.prompt.substring(0, 200)}
                {agent.prompt.length > 200 && '...'}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
