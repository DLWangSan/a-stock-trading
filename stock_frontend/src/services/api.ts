/**
 * API服务 - 与后端通信
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5010';

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
  turnover_rate?: number; // 换手率
}

export interface StockComprehensive {
  code: string;
  realtime: StockRealtime;
  daily_count: number;
  daily?: any[];
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

export type TradingStyle = 'ultra_short' | 'short' | 'medium' | 'long';
export type RiskLevel = 'conservative' | 'balanced' | 'aggressive';

export interface TradingProfile {
  style: TradingStyle;
  style_label: string;
  holding_horizon: string;
  focus: string;
  risk_level: RiskLevel;
  max_single_position_pct: number;
  max_total_position_pct: number;
  default_stop_loss_pct: number;
  default_take_profit_pct: number;
  available_cash: number;
  allow_intraday_t: boolean;
  notes: string;
  updated_at?: string | null;
}

export interface Position {
  id: number;
  code: string;
  name: string;
  quantity: number;
  available_quantity: number;
  avg_cost: number;
  opened_at?: string | null;
  target_price?: number | null;
  stop_loss_price?: number | null;
  thesis: string;
  notes: string;
  current_price?: number | null;
  change_percent?: number | null;
  market_value?: number | null;
  cost_value: number;
  profit?: number | null;
  profit_pct?: number | null;
  position_pct?: number | null;
  updated_at?: string | null;
}

export interface Portfolio {
  profile: TradingProfile;
  positions: Position[];
  summary: {
    position_count: number;
    total_cost: number;
    total_market_value?: number | null;
    total_profit?: number | null;
    total_profit_pct?: number | null;
    market_data_complete: boolean;
    available_cash: number;
    total_assets: number;
    total_position_pct: number;
    remaining_position_capacity: number;
    available_for_new_position: number;
  };
}

export interface FourLightsCandidate {
  code: string;
  name: string;
  current_price: number;
  change_percent: number;
  amount: number;
  turnover_rate: number;
  score: number;
  rank: number;
  light_count: number;
  actionable: boolean;
  lights: Record<'trend' | 'momentum' | 'volume' | 'capital', boolean>;
  details: Record<string, number | string | null>;
  score_reasons: string[];
  risk_flags: string[];
}

export interface FourLightsScan {
  run_id: string;
  strategy: 'four_lights';
  description: string;
  strategy_style: 'short_ultra';
  holding_horizon: string;
  session: 'morning' | 'afternoon';
  scan_time: string;
  validation_target: string;
  universe_count: number;
  preselected_count: number;
  count: number;
  actionable_count: number;
  stocks: FourLightsCandidate[];
}

export interface FourLightsRun {
  run_id: string;
  strategy: string;
  session: 'morning' | 'afternoon';
  created_at: string;
  validation_status: 'pending' | 'validated';
  stocks: Array<{
    code: string;
    name: string;
    signal_price: number;
    score: number;
    light_count: number;
    lights: FourLightsCandidate['lights'] | Record<string, boolean>;
    validation_status: 'pending' | 'validated';
    validation_price?: number | null;
    validation_return_pct?: number | null;
    validated_at?: string | null;
  }>;
}

export interface OvernightCandidate {
  code: string;
  name: string;
  current_price: number;
  change_percent: number;
  amount: number;
  turnover_rate: number;
  score: number;
  rank: number;
  pass_count: number;
  actionable: boolean;
  recommended: boolean;
  checks: Record<'gain_band' | 'liquidity' | 'limit_memory' | 'above_ma5' | 'volume_active', boolean>;
  details: Record<string, number | string | null>;
  score_reasons: string[];
  risk_flags: string[];
  sell_plan: string;
  holding_horizon: string;
}

export interface OvernightScan {
  run_id: string;
  strategy: 'overnight';
  description: string;
  strategy_style: 'overnight_ultra';
  holding_horizon: string;
  session: 'afternoon';
  scan_time: string;
  validation_target: string;
  afternoon_ready: boolean;
  timing_note: string;
  universe_count: number;
  preselected_count: number;
  count: number;
  actionable_count: number;
  stocks: OvernightCandidate[];
  rules: Record<string, string>;
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
      let message = response.statusText;
      try {
        const body = await response.json();
        message = body?.error?.message || body?.error || body?.message || message;
      } catch {
        // 非 JSON 错误响应保留 HTTP 状态文本
      }
      throw new Error(`API Error: ${message}`);
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

  // 持仓与交易画像
  async getPortfolio(): Promise<Portfolio> {
    const data = await this.request<{ success: boolean; data: Portfolio }>('/api/portfolio');
    return data.data;
  }

  async updateTradingProfile(updates: Partial<TradingProfile>): Promise<TradingProfile> {
    const data = await this.request<{ success: boolean; data: TradingProfile }>('/api/trading-profile', {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
    return data.data;
  }

  async addPosition(position: {
    code: string;
    name?: string;
    quantity: number;
    available_quantity: number;
    avg_cost: number;
    opened_at?: string | null;
    target_price?: number | null;
    stop_loss_price?: number | null;
    thesis?: string;
    notes?: string;
  }): Promise<Position> {
    const data = await this.request<{ success: boolean; data: Position }>('/api/portfolio/positions', {
      method: 'POST',
      body: JSON.stringify(position),
    });
    return data.data;
  }

  async updatePosition(id: number, updates: Partial<Position>): Promise<Position> {
    const data = await this.request<{ success: boolean; data: Position }>(`/api/portfolio/positions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
    return data.data;
  }

  async removePosition(id: number): Promise<boolean> {
    const data = await this.request<{ success: boolean }>(`/api/portfolio/positions/${id}`, {
      method: 'DELETE',
    });
    return data.success;
  }

  async startPortfolioAnalysis(agentIds: number[]): Promise<{ job_id: string; name: string }> {
    const data = await this.request<{
      success: boolean;
      data: { job_id: string; name: string };
    }>('/api/portfolio/analyze', {
      method: 'POST',
      body: JSON.stringify({ agent_ids: agentIds }),
    });
    return data.data;
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
    debateRounds: number = 1,
    candidateContext?: string
  ): Promise<{ job_id: string; name: string }> {
    const data = await this.request<{ success: boolean; data: { job_id: string; name: string } }>('/api/ai/debate/start_multi', {
      method: 'POST',
      body: JSON.stringify({
        codes,
        agent_ids: agentIds,
        analysis_rounds: analysisRounds,
        debate_rounds: debateRounds,
        candidate_context: candidateContext,
      }),
    });
    return data.data;
  }

  async getStrongStocks(limitTime: string): Promise<any> {
    return this.request(`/api/strategy/strong_stocks?limit_time=${encodeURIComponent(limitTime)}`);
  }

  async scanFourLights(session: 'auto' | 'morning' | 'afternoon' = 'auto'): Promise<FourLightsScan> {
    const data = await this.request<{ success: boolean; data: FourLightsScan }>('/api/strategy/four_lights/scan', {
      method: 'POST',
      body: JSON.stringify({ session, top_n: 5 }),
    });
    return data.data;
  }

  async getFourLightsHistory(limit = 10): Promise<FourLightsRun[]> {
    const data = await this.request<{ success: boolean; data: FourLightsRun[] }>(
      `/api/strategy/four_lights/history?limit=${limit}&validate=true`
    );
    return data.data;
  }

  async deleteFourLightsHistory(runId: string): Promise<number> {
    const data = await this.request<{ success: boolean; data: { deleted: number } }>(
      `/api/strategy/four_lights/history/${encodeURIComponent(runId)}`,
      { method: 'DELETE' }
    );
    return data.data.deleted;
  }

  async clearFourLightsHistory(): Promise<number> {
    const data = await this.request<{ success: boolean; data: { deleted: number } }>(
      '/api/strategy/four_lights/history',
      { method: 'DELETE' }
    );
    return data.data.deleted;
  }

  async scanOvernight(): Promise<OvernightScan> {
    const data = await this.request<{ success: boolean; data: OvernightScan }>('/api/strategy/overnight/scan', {
      method: 'POST',
      body: JSON.stringify({ top_n: 5 }),
    });
    return data.data;
  }

  async getOvernightHistory(limit = 10): Promise<FourLightsRun[]> {
    const data = await this.request<{ success: boolean; data: FourLightsRun[] }>(
      `/api/strategy/overnight/history?limit=${limit}&validate=true`
    );
    return data.data;
  }

  async deleteOvernightHistory(runId: string): Promise<number> {
    const data = await this.request<{ success: boolean; data: { deleted: number } }>(
      `/api/strategy/overnight/history/${encodeURIComponent(runId)}`,
      { method: 'DELETE' }
    );
    return data.data.deleted;
  }

  async clearOvernightHistory(): Promise<number> {
    const data = await this.request<{ success: boolean; data: { deleted: number } }>(
      '/api/strategy/overnight/history',
      { method: 'DELETE' }
    );
    return data.data.deleted;
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

