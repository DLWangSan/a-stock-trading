/**
 * 自选股状态管理
 */
import { create } from 'zustand';
import { stockAPI } from '../services/api';
import type { WatchlistItem } from '../services/api';

interface WatchlistState {
  items: WatchlistItem[];
  loading: boolean;
  error: string | null;
  fetchWatchlist: () => Promise<void>;
  addStock: (code: string, name?: string) => Promise<void>;
  removeStock: (code: string) => Promise<void>;
  updateOrder: (orders: Array<{ code: string; sort_order: number }>) => Promise<void>;
}

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  items: [],
  loading: false,
  error: null,

  fetchWatchlist: async () => {
    set({ loading: true, error: null });
    try {
      const items = await stockAPI.getWatchlist();
      set({ items, loading: false });
    } catch (error) {
      set({ error: (error as Error).message, loading: false });
    }
  },

  addStock: async (code: string, name?: string) => {
    try {
      await stockAPI.addWatchlist(code, name);
      await get().fetchWatchlist();
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  removeStock: async (code: string) => {
    try {
      await stockAPI.removeWatchlist(code);
      await get().fetchWatchlist();
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  updateOrder: async (orders: Array<{ code: string; sort_order: number }>) => {
    try {
      await stockAPI.updateWatchlistOrder(orders);
      await get().fetchWatchlist();
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },
}));

