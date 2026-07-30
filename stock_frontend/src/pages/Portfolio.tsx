import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { stockAPI, type Position, type RiskLevel, type TradingProfile, type TradingStyle } from '../services/api';
import { getDefaultAgentIds } from '../utils/agentSelection';

const styleOptions: Array<{ value: TradingStyle; label: string; detail: string }> = [
  { value: 'ultra_short', label: '超短线', detail: '盘中至2日' },
  { value: 'short', label: '短线', detail: '3至20日' },
  { value: 'medium', label: '中线', detail: '1至6个月' },
  { value: 'long', label: '长线', detail: '6个月以上' },
];

const emptyForm = {
  code: '',
  name: '',
  quantity: '',
  available_quantity: '',
  avg_cost: '',
  opened_at: '',
  target_price: '',
  stop_loss_price: '',
  thesis: '',
  notes: '',
};

const SELL_FEE_RATE = 0.0005;
const SELL_FEE_MIN = 5;

function money(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '--';
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function calcSellFee(price: number, quantity: number) {
  const amount = price * quantity;
  if (!amount || amount <= 0) return 0;
  return Math.max(amount * SELL_FEE_RATE, SELL_FEE_MIN);
}

export default function PortfolioPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [analyzingAll, setAnalyzingAll] = useState(false);
  const [error, setError] = useState('');
  const [sellingId, setSellingId] = useState<number | null>(null);
  const [sellQuantity, setSellQuantity] = useState('');
  const [sellPrice, setSellPrice] = useState('');
  const [selling, setSelling] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => stockAPI.getPortfolio(),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ['agents', 'enabled'],
    queryFn: () => stockAPI.getAgents(true),
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['portfolio'] });

  const submitPosition = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        code: form.code.trim(),
        name: form.name.trim(),
        quantity: Number(form.quantity),
        available_quantity: Number(form.available_quantity || form.quantity),
        avg_cost: Number(form.avg_cost),
        opened_at: form.opened_at || null,
        target_price: form.target_price ? Number(form.target_price) : null,
        stop_loss_price: form.stop_loss_price ? Number(form.stop_loss_price) : null,
        thesis: form.thesis.trim(),
        notes: form.notes.trim(),
      };
      if (editingId) {
        await stockAPI.updatePosition(editingId, payload);
      } else {
        await stockAPI.addPosition(payload);
      }
      setForm(emptyForm);
      setEditingId(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const editPosition = (position: Position) => {
    setEditingId(position.id);
    setSellingId(null);
    setForm({
      code: position.code,
      name: position.name,
      quantity: String(position.quantity),
      available_quantity: String(position.available_quantity),
      avg_cost: String(position.avg_cost),
      opened_at: position.opened_at ? position.opened_at.slice(0, 10) : '',
      target_price: position.target_price == null ? '' : String(position.target_price),
      stop_loss_price: position.stop_loss_price == null ? '' : String(position.stop_loss_price),
      thesis: position.thesis,
      notes: position.notes,
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const openSell = (position: Position) => {
    setSellingId(position.id);
    setSellQuantity(String(position.available_quantity || ''));
    setSellPrice(
      position.current_price != null ? String(position.current_price) : String(position.avg_cost),
    );
    setError('');
  };

  const submitSell = async (position: Position) => {
    const quantity = Number(sellQuantity);
    const price = Number(sellPrice);
    if (!Number.isInteger(quantity) || quantity <= 0) {
      setError('卖出数量必须是正整数');
      return;
    }
    if (!(price > 0)) {
      setError('卖出价格必须大于0');
      return;
    }
    if (quantity > position.available_quantity) {
      setError(`卖出数量不能超过今日可卖 ${position.available_quantity} 股`);
      return;
    }
    const fee = calcSellFee(price, quantity);
    const net = price * quantity - fee;
    if (!window.confirm(
      `确认卖出 ${position.name} ${quantity} 股？\n`
      + `成交价 ¥${price.toFixed(3)}，手续费 ¥${fee.toFixed(2)}（万五，最低5元）\n`
      + `预计回笼现金 ¥${net.toFixed(2)}；剩余持仓成本价不变。`,
    )) {
      return;
    }
    setSelling(true);
    setError('');
    try {
      const result = await stockAPI.sellPosition(position.id, quantity, price);
      setSellingId(null);
      setSellQuantity('');
      setSellPrice('');
      await refresh();
      window.alert(
        `卖出成功：净回笼 ¥${money(result.trade.net_amount)}，手续费 ¥${money(result.trade.fee)}，`
        + `可用现金现为 ¥${money(result.trade.available_cash)}`
        + (result.deleted ? '；该持仓已清仓。' : `；剩余 ${result.trade.remaining_quantity} 股。`),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : '卖出失败');
    } finally {
      setSelling(false);
    }
  };

  const startAnalysis = async (position: Position) => {
    if (agents.length < 2) {
      setError('至少需要启用2个 Agent 才能启动持仓分析');
      return;
    }
    setError('');
    try {
      const res = await stockAPI.startDebateJob(position.code, getDefaultAgentIds(agents), 1, 1);
      navigate(`/ai-debate?code=${position.code}&job_id=${res.job_id}&ar=1&dr=1`);
    } catch (e) {
      setError(e instanceof Error ? e.message : '启动分析失败');
    }
  };

  const startPortfolioAnalysis = async () => {
    if (agents.length < 2) {
      setError('至少需要启用2个 Agent 才能启动整体分析');
      return;
    }
    setAnalyzingAll(true);
    setError('');
    try {
      const res = await stockAPI.startPortfolioAnalysis(getDefaultAgentIds(agents));
      navigate(`/ai-debate?job_id=${res.job_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : '启动整体持仓分析失败');
    } finally {
      setAnalyzingAll(false);
    }
  };

  const saveProfile = async (updates: Partial<TradingProfile>) => {
    setError('');
    try {
      await stockAPI.updateTradingProfile(updates);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : '交易画像保存失败');
    }
  };

  if (isLoading || !data) {
    return <div className="py-20 text-center text-gray-500">正在加载持仓...</div>;
  }

  const { profile, positions, summary } = data;
  const totalUp = (summary.total_profit || 0) >= 0;

  return (
    <div className="space-y-6 px-4 sm:px-0">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">持仓管理</h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            持仓成本、今日可卖数量和交易风格会自动注入 AI 分析。
          </p>
        </div>
        <button
          onClick={startPortfolioAnalysis}
          disabled={analyzingAll || positions.length === 0}
          className="rounded-lg bg-gradient-to-r from-red-600 to-purple-600 px-5 py-3 font-semibold text-white shadow hover:from-red-700 hover:to-purple-700 disabled:opacity-50"
        >
          {analyzingAll ? '正在启动...' : '一键分析全部持仓'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <Summary label="持仓数量" value={`${summary.position_count} 只`} />
        <Summary label="估算总资产" value={`¥${money(summary.total_assets)}`} />
        <Summary label="可用现金" value={`¥${money(summary.available_cash)}`} />
        <Summary label="当前市值" value={`¥${money(summary.total_market_value)}`} />
        <Summary label="总仓位" value={`${money(summary.total_position_pct)}%`} />
        <Summary
          label="浮动盈亏"
          value={`${totalUp ? '+' : ''}¥${money(summary.total_profit)} (${money(summary.total_profit_pct)}%)`}
          tone={totalUp ? 'up' : 'down'}
        />
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">交易画像</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">{profile.focus}</p>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
            <input
              type="checkbox"
              checked={profile.allow_intraday_t}
              onChange={(e) => saveProfile({ allow_intraday_t: e.target.checked })}
            />
            允许日内做T
          </label>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm text-gray-600 dark:text-gray-300">
            可用现金（元）
            <input
              type="number"
              defaultValue={profile.available_cash}
              min={0}
              step="0.01"
              onBlur={(e) => saveProfile({ available_cash: Number(e.target.value) })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            />
          </label>
          <label className="text-sm text-gray-600 dark:text-gray-300">
            操作风格
            <select
              value={profile.style}
              onChange={(e) => saveProfile({ style: e.target.value as TradingStyle })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            >
              {styleOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.label} · {item.detail}</option>
              ))}
            </select>
          </label>
          <label className="text-sm text-gray-600 dark:text-gray-300">
            风险偏好
            <select
              value={profile.risk_level}
              onChange={(e) => saveProfile({ risk_level: e.target.value as RiskLevel })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            >
              <option value="conservative">稳健</option>
              <option value="balanced">均衡</option>
              <option value="aggressive">进取</option>
            </select>
          </label>
          <label className="text-sm text-gray-600 dark:text-gray-300">
            单票仓位上限（%）
            <input
              type="number"
              defaultValue={profile.max_single_position_pct}
              min={0}
              max={100}
              onBlur={(e) => saveProfile({ max_single_position_pct: Number(e.target.value) })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            />
          </label>
          <label className="text-sm text-gray-600 dark:text-gray-300">
            总仓位上限（%）
            <input
              type="number"
              defaultValue={profile.max_total_position_pct}
              min={0}
              max={100}
              onBlur={(e) => saveProfile({ max_total_position_pct: Number(e.target.value) })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            />
          </label>
        </div>
        <p className="mt-3 text-xs text-gray-500">
          当前可用现金 ¥{money(summary.available_cash)}；
          受总仓位上限约束后，最多还可新开仓 ¥{money(summary.available_for_new_position)}。
          AI 会区分“账户现金”和“可新开仓额度”，不会把后者当成现金余额。
        </p>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
          {editingId ? '编辑持仓' : '录入持仓'}
        </h2>
        <form onSubmit={submitPosition} className="grid gap-4 md:grid-cols-4">
          <Field label="股票代码" value={form.code} required maxLength={6} onChange={(value) => setForm({ ...form, code: value })} />
          <Field label="股票名称（可留空）" value={form.name} onChange={(value) => setForm({ ...form, name: value })} />
          <Field label="持仓数量" type="number" value={form.quantity} required onChange={(value) => setForm({ ...form, quantity: value })} />
          <Field label="今日可卖" type="number" value={form.available_quantity} onChange={(value) => setForm({ ...form, available_quantity: value })} />
          <Field label="平均成本" type="number" step="0.001" value={form.avg_cost} required onChange={(value) => setForm({ ...form, avg_cost: value })} />
          <Field label="建仓日期" type="date" value={form.opened_at} onChange={(value) => setForm({ ...form, opened_at: value })} />
          <Field label="目标价" type="number" step="0.001" value={form.target_price} onChange={(value) => setForm({ ...form, target_price: value })} />
          <Field label="止损价" type="number" step="0.001" value={form.stop_loss_price} onChange={(value) => setForm({ ...form, stop_loss_price: value })} />
          <label className="text-sm text-gray-600 dark:text-gray-300 md:col-span-2">
            持仓逻辑
            <textarea
              value={form.thesis}
              onChange={(e) => setForm({ ...form, thesis: e.target.value })}
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            />
          </label>
          <label className="text-sm text-gray-600 dark:text-gray-300 md:col-span-2">
            备注
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            />
          </label>
          <div className="flex gap-2 md:col-span-4">
            <button disabled={saving} className="rounded-lg bg-blue-600 px-5 py-2 text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? '保存中...' : editingId ? '保存修改' : '添加持仓'}
            </button>
            {editingId && (
              <button
                type="button"
                onClick={() => { setEditingId(null); setForm(emptyForm); }}
                className="rounded-lg border border-gray-300 px-5 py-2 text-gray-600 dark:border-gray-600 dark:text-gray-300"
              >
                取消
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="space-y-3">
        {positions.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 py-16 text-center text-gray-500 dark:border-gray-700">
            暂无持仓，请先录入股票、数量和成本。
          </div>
        ) : positions.map((position) => {
          const up = (position.profit || 0) >= 0;
          return (
            <article key={position.id} className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white">{position.name}</div>
                  <div className="text-sm text-gray-500">{position.code} · 持仓 {position.quantity} 股 · 今日可卖 {position.available_quantity} 股</div>
                </div>
                <div className={`text-right ${up ? 'text-red-600' : 'text-green-600'}`}>
                  <div className="text-xl font-bold">{money(position.current_price)}</div>
                  <div className="text-sm">{up ? '+' : ''}{money(position.profit)} / {money(position.profit_pct)}%</div>
                </div>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-gray-600 dark:text-gray-300 sm:grid-cols-5">
                <div>成本 <strong>{money(position.avg_cost)}</strong></div>
                <div>市值 <strong>{money(position.market_value)}</strong></div>
                <div>仓位 <strong>{money(position.position_pct)}%</strong></div>
                <div>目标价 <strong>{money(position.target_price)}</strong></div>
                <div>止损价 <strong>{money(position.stop_loss_price)}</strong></div>
              </div>
              {position.thesis && <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">持仓逻辑：{position.thesis}</p>}
              <div className="mt-4 flex flex-wrap gap-2">
                <button onClick={() => startAnalysis(position)} className="rounded-lg bg-purple-600 px-4 py-2 text-sm text-white hover:bg-purple-700">
                  AI 持仓分析
                </button>
                <button
                  onClick={() => openSell(position)}
                  disabled={position.available_quantity <= 0}
                  className="rounded-lg bg-rose-600 px-4 py-2 text-sm text-white hover:bg-rose-700 disabled:opacity-50"
                >
                  卖出
                </button>
                <button onClick={() => editPosition(position)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm dark:border-gray-600">
                  编辑成本/数量
                </button>
                <button
                  onClick={async () => {
                    if (!window.confirm(`确定删除 ${position.name} 的持仓记录？`)) return;
                    await stockAPI.removePosition(position.id);
                    await refresh();
                  }}
                  className="rounded-lg border border-red-300 px-4 py-2 text-sm text-red-600 dark:border-red-800"
                >
                  删除
                </button>
              </div>
              {sellingId === position.id && (
                <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4 dark:border-rose-800 dark:bg-rose-900/20">
                  <div className="mb-3 text-sm font-medium text-rose-800 dark:text-rose-200">
                    卖出 {position.name}（手续费万五，最低5元；剩余股数成本价不变）
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <label className="text-sm text-gray-600 dark:text-gray-300">
                      卖出数量（可卖 {position.available_quantity}）
                      <input
                        type="number"
                        min={1}
                        max={position.available_quantity}
                        step={100}
                        value={sellQuantity}
                        onChange={(e) => setSellQuantity(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
                      />
                    </label>
                    <label className="text-sm text-gray-600 dark:text-gray-300">
                      卖出价格
                      <input
                        type="number"
                        min={0.001}
                        step={0.001}
                        value={sellPrice}
                        onChange={(e) => setSellPrice(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
                      />
                    </label>
                    <div className="text-sm text-gray-600 dark:text-gray-300">
                      预计明细
                      <div className="mt-1 rounded-lg border border-rose-100 bg-white px-3 py-2 dark:border-rose-900 dark:bg-gray-800">
                        {(() => {
                          const qty = Number(sellQuantity) || 0;
                          const price = Number(sellPrice) || 0;
                          const fee = calcSellFee(price, qty);
                          const net = Math.max(0, price * qty - fee);
                          return (
                            <>
                              <div>成交额 ¥{money(price * qty)}</div>
                              <div>手续费 ¥{money(fee)}</div>
                              <div>净回笼 ¥{money(net)}</div>
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => void submitSell(position)}
                      disabled={selling}
                      className="rounded-lg bg-rose-600 px-4 py-2 text-sm text-white hover:bg-rose-700 disabled:opacity-50"
                    >
                      {selling ? '卖出中...' : '确认卖出'}
                    </button>
                    <button
                      onClick={() => setSellingId(null)}
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm dark:border-gray-600"
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
}

function Summary({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' }) {
  const color = tone === 'up' ? 'text-red-600' : tone === 'down' ? 'text-green-600' : 'text-gray-900 dark:text-white';
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${color}`}>{value}</div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  ...props
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  maxLength?: number;
  step?: string;
}) {
  return (
    <label className="text-sm text-gray-600 dark:text-gray-300">
      {label}
      <input
        {...props}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
      />
    </label>
  );
}
