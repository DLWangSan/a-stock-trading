/**
 * API服务 - 与后端通信
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

export interface StockRealtime {
  code: string;
  name: string;
  current_price: number;
  change_percent: number;
  volume: number;
  amount: number;
  high: number;
  low: number;
  open: number;
  yesterday_close: number;
}

export interface StockComprehensive {
  code: string;
  realtime: StockRealtime;
  daily_count: number;
  indicators?: any;
  money_flow?: any;
  fundamental?: any;
  industry_comparison?: any;
}

export interface WatchlistItem {
  id: number;
  code: string;
  name: string;
  sort_order: number;
}

export interface Agent {
  id: number;
  name: string;
  type: 'default' | 'intraday_t' | 'review';
  prompt: string;
  enabled: boolean;
  ai_provider: string | null;
  model: string | null;
  sort_order: number;
}

export interface AnalysisResult {
  analysis: string;
  agent_name: string;
  agent_type: string;
  timestamp: string;
  recommendation?: {
    buy_price: number;
    sell_price: number;
  };
}

export interface DebateStep {
  phase: 'analysis' | 'debate';
  round: number;
  agent_id: number;
  agent_name: string;
  content: string;
  timestamp: string;
}

export interface DebateResult {
  steps: DebateStep[];
  report_md: string;
  analysis_rounds: number;
  debate_rounds: number;
}

export interface DebateJobStatus {
  job_id: string;
  code: string;
  name: string;
  agent_ids: number[];
  analysis_rounds: number;
  debate_rounds: number;
  meta?: {
    mode?: string;
    codes?: string[];
    decision_agent_id?: number;
  };
  status: 'queued' | 'running' | 'completed' | 'failed' | 'canceled';
  progress: number;
  steps: DebateStep[];
  report_md: string;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

class StockAPI {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  getBaseURL() {
    return this.baseURL;
  }

  setBaseURL(url: string) {
    this.baseURL = url;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // 数据获取API
  async getRealtime(code: string): Promise<StockRealtime> {
    const response = await this.request<any>(`/api/sina/realtime/${code}`);
    // 后端返回格式可能是 { data: {...} } 或直接返回数据
    return response.data || response;
  }

  async getComprehensive(code: string): Promise<StockComprehensive> {
    const response = await this.request<any>(`/api/sina/comprehensive_with_indicators/${code}`);
    // 后端返回格式可能是 { data: {...} } 或直接返回数据
    return response.data || response;
  }

  async getSentiment(code: string, days: number = 7): Promise<any> {
    return this.request(`/api/sentiment/all/${code}?days=${days}&latest=10&hot=10`);
  }

  // 自选股API
  async getWatchlist(): Promise<WatchlistItem[]> {
    const data = await this.request<{ success: boolean; data: WatchlistItem[] }>('/api/watchlist');
    return data.data;
  }

  async addWatchlist(code: string, name?: string): Promise<WatchlistItem> {
    const data = await this.request<{ success: boolean; data: WatchlistItem }>('/api/watchlist', {
      method: 'POST',
      body: JSON.stringify({ code, name }),
    });
    return data.data;
  }

  async removeWatchlist(code: string): Promise<boolean> {
    const data = await this.request<{ success: boolean }>(`/api/watchlist/${code}`, {
      method: 'DELETE',
    });
    return data.success;
  }

  async updateWatchlistOrder(orders: Array<{ code: string; sort_order: number }>): Promise<boolean> {
    const data = await this.request<{ success: boolean }>('/api/watchlist/order', {
      method: 'POST',
      body: JSON.stringify({ orders }),
    });
    return data.success;
  }

  // 配置API
  async getConfig(key: string): Promise<string | null> {
    const data = await this.request<{ success: boolean; data: Record<string, string> }>(`/api/config/${key}`);
    return data.data[key] || null;
  }

  async getAllConfigs(): Promise<Record<string, string>> {
    const data = await this.request<{ success: boolean; data: Record<string, string> }>('/api/config');
    return data.data;
  }

  async setConfig(key: string, value: string): Promise<boolean> {
    const data = await this.request<{ success: boolean }>(`/api/config/${key}`, {
      method: 'POST',
      body: JSON.stringify({ value }),
    });
    return data.success;
  }

  // Agent API
  async getAgents(enabledOnly: boolean = false): Promise<Agent[]> {
    const data = await this.request<{ success: boolean; data: Agent[] }>(
      `/api/agents?enabled_only=${enabledOnly}`
    );
    return data.data;
  }

  async createAgent(agent: Partial<Agent>): Promise<number> {
    const data = await this.request<{ success: boolean; data: { id: number } }>('/api/agents', {
      method: 'POST',
      body: JSON.stringify(agent),
    });
    return data.data.id;
  }

  async updateAgent(id: number, updates: Partial<Agent>): Promise<boolean> {
    const data = await this.request<{ success: boolean }>(`/api/agents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
    return data.success;
  }

  async deleteAgent(id: number): Promise<boolean> {
    const data = await this.request<{ success: boolean }>(`/api/agents/${id}`, {
      method: 'DELETE',
    });
    return data.success;
  }

  // AI分析API
  async analyzeStock(code: string, agentId: number, useCache: boolean = true): Promise<AnalysisResult> {
    const data = await this.request<{ success: boolean; data: AnalysisResult }>(`/api/ai/analyze/${code}`, {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId, use_cache: useCache }),
    });
    return data.data;
  }

  async debateStock(
    code: string,
    agentIds: number[],
    analysisRounds: number = 3,
    debateRounds: number = 3
  ): Promise<DebateResult> {
    const data = await this.request<{ success: boolean; data: DebateResult }>(`/api/ai/debate/${code}`, {
      method: 'POST',
      body: JSON.stringify({
        agent_ids: agentIds,
        analysis_rounds: analysisRounds,
        debate_rounds: debateRounds,
      }),
    });
    return data.data;
  }

  async startDebateJob(
    code: string,
    agentIds: number[],
    analysisRounds: number = 3,
    debateRounds: number = 3
  ): Promise<{ job_id: string; name: string }> {
    const data = await this.request<{ success: boolean; data: { job_id: string; name: string } }>(`/api/ai/debate/start/${code}`, {
      method: 'POST',
      body: JSON.stringify({
        agent_ids: agentIds,
        analysis_rounds: analysisRounds,
        debate_rounds: debateRounds,
      }),
    });
    return data.data;
  }

  async getDebateJobStatus(jobId: string): Promise<DebateJobStatus> {
    const data = await this.request<{ success: boolean; data: DebateJobStatus }>(`/api/ai/debate/status/${jobId}`);
    return data.data;
  }

  async listDebateJobs(status?: string, limit: number = 50): Promise<DebateJobStatus[]> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', String(limit));
    const data = await this.request<{ success: boolean; data: DebateJobStatus[] }>(`/api/ai/debate/jobs?${params.toString()}`);
    return data.data;
  }

  async startMultiSelectDebate(
    codes: string[],
    agentIds: number[],
    analysisRounds: number = 2,
    debateRounds: number = 1
  ): Promise<{ job_id: string; name: string }> {
    const data = await this.request<{ success: boolean; data: { job_id: string; name: string } }>('/api/ai/debate/start_multi', {
      method: 'POST',
      body: JSON.stringify({
        codes,
        agent_ids: agentIds,
        analysis_rounds: analysisRounds,
        debate_rounds: debateRounds,
      }),
    });
    return data.data;
  }

  async getStrongStocks(limitTime: string): Promise<any> {
    return this.request(`/api/strategy/strong_stocks?limit_time=${encodeURIComponent(limitTime)}`);
  }

  async stopDebateJob(jobId: string): Promise<boolean> {
    const data = await this.request<{ success: boolean }>(`/api/ai/debate/stop/${jobId}`, {
      method: 'POST',
    });
    return data.success;
  }

  async deleteDebateJob(jobId: string): Promise<boolean> {
    const data = await this.request<{ success: boolean }>(`/api/ai/debate/delete/${jobId}`, {
      method: 'DELETE',
    });
    return data.success;
  }

  // AI服务工具API
  async getAIModels(provider: string, apiKey?: string): Promise<string[]> {
    const params = new URLSearchParams({ provider });
    if (apiKey) {
      params.append('api_key', apiKey);
    }
    const data = await this.request<{ success: boolean; data: string[] }>(`/api/ai/models?${params.toString()}`);
    return data.data;
  }

  async testAIConnection(provider: string, apiKey: string, model?: string): Promise<{ success: boolean; message: string; response?: string }> {
    const data = await this.request<{ success: boolean; message: string; response?: string }>('/api/ai/test', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey, model }),
    });
    return data;
  }
}

export const stockAPI = new StockAPI();

