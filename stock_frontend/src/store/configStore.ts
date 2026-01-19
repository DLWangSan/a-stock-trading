/**
 * 配置状态管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ConfigState {
  apiBaseURL: string;
  openaiApiKey: string;
  deepseekApiKey: string;
  qwenApiKey: string;
  geminiApiKey: string;
  defaultAiProvider: string;
  setApiBaseURL: (url: string) => void;
  setOpenaiApiKey: (key: string) => void;
  setDeepseekApiKey: (key: string) => void;
  setQwenApiKey: (key: string) => void;
  setGeminiApiKey: (key: string) => void;
  setDefaultAiProvider: (provider: string) => void;
}

export const useConfigStore = create<ConfigState>()(
  persist(
    (set) => ({
      apiBaseURL: 'http://127.0.0.1:5000',
      openaiApiKey: '',
      deepseekApiKey: '',
      qwenApiKey: '',
      geminiApiKey: '',
      defaultAiProvider: 'openai',
      setApiBaseURL: (url) => set({ apiBaseURL: url }),
      setOpenaiApiKey: (key) => set({ openaiApiKey: key }),
      setDeepseekApiKey: (key) => set({ deepseekApiKey: key }),
      setQwenApiKey: (key) => set({ qwenApiKey: key }),
      setGeminiApiKey: (key) => set({ geminiApiKey: key }),
      setDefaultAiProvider: (provider) => set({ defaultAiProvider: provider }),
    }),
    {
      name: 'stock-config',
    }
  )
);

