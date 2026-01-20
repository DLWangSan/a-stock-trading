import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Home from './pages/Home';
import Watchlist from './pages/Watchlist';
import StockDetail from './pages/StockDetail';
import Tasks from './pages/Tasks';
import Strategy from './pages/Strategy';
import Settings from './pages/Settings';
import AIDebate from './pages/AIDebate';
import Layout from './components/Layout';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30秒
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/stock/:code" element={<StockDetail />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/strategy" element={<Strategy />} />
            <Route path="/ai-debate" element={<AIDebate />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
