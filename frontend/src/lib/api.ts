import axios from 'axios';
import type {
  User,
  TokenResponse,
  PortfolioResponse,
  PortfolioInfo,
  PortfolioListResponse,
  PortfolioDetailResponse,
  PortfolioCreate,
  PortfolioUpdate,
  ProfitBookingRules,
  TrailingStopConfig,
  TrailingStopUpdate,
  TradeHistoryResponse,
  DailyPnLHistory,
  FundsResponse,
  FundsDepositRequest,
  FundsWithdrawRequest,
  FundsResetRequest,
  Order,
  OrderListResponse,
  OrderCreate,
  StockQuote,
  StockInfo,
  HistoricalDataResponse,
  SearchResult,
  Watchlist,
  WatchlistListResponse,
  WatchlistCreate,
  RiskLimits,
  RiskLimitsUpdate,
  RiskSummary,
  DailyRiskMetrics,
  TechnicalIndicators,
  AnalysisResult,
  Instrument,
  Alert,
  AlertCreate,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ user: User; token: TokenResponse }>('/auth/login', { email, password }),
  register: (email: string, password: string, fullName?: string) =>
    api.post<{ user: User; token: TokenResponse }>('/auth/register', { email, password, full_name: fullName }),
  me: () => api.get<User>('/auth/me'),
};

// Portfolio API
export const portfolioApi = {
  // Legacy endpoint - all positions combined
  getPortfolio: () =>
    api.get<PortfolioResponse>('/portfolio'),
  getTrades: (page = 1, pageSize = 50) =>
    api.get<TradeHistoryResponse>('/portfolio/trades', { params: { page, page_size: pageSize } }),
  getDailyPnL: (days = 30) =>
    api.get<DailyPnLHistory>('/portfolio/daily-pnl', { params: { days } }),

  // Portfolio management
  listPortfolios: () =>
    api.get<PortfolioListResponse>('/portfolio/portfolios'),
  getPortfolioDetail: (portfolioId: string) =>
    api.get<PortfolioDetailResponse>(`/portfolio/portfolios/${portfolioId}`),
  createPortfolio: (data: PortfolioCreate) =>
    api.post<PortfolioInfo>('/portfolio/portfolios', data),
  updatePortfolio: (portfolioId: string, data: PortfolioUpdate) =>
    api.patch<PortfolioInfo>(`/portfolio/portfolios/${portfolioId}`, data),
  deletePortfolio: (portfolioId: string) =>
    api.delete(`/portfolio/portfolios/${portfolioId}`),

  // Profit booking
  getProfitBookingRules: (positionId: string) =>
    api.get<ProfitBookingRules>(`/portfolio/positions/${positionId}/profit-booking`),
  updateProfitBookingRules: (positionId: string, rules: ProfitBookingRules) =>
    api.patch<ProfitBookingRules>(`/portfolio/positions/${positionId}/profit-booking`, rules),

  // Trailing stop
  getTrailingStopConfig: (positionId: string) =>
    api.get<TrailingStopConfig>(`/portfolio/positions/${positionId}/trailing-stop`),
  updateTrailingStop: (positionId: string, config: TrailingStopUpdate) =>
    api.patch<TrailingStopConfig>(`/portfolio/positions/${positionId}/trailing-stop`, config),

  // Funds management
  getFunds: () =>
    api.get<FundsResponse>('/portfolio/funds'),
  depositFunds: (data: FundsDepositRequest) =>
    api.post<FundsResponse>('/portfolio/funds/deposit', data),
  withdrawFunds: (data: FundsWithdrawRequest) =>
    api.post<FundsResponse>('/portfolio/funds/withdraw', data),
  resetFunds: (data?: FundsResetRequest) =>
    api.post<FundsResponse>('/portfolio/funds/reset', data || {}),
};

// Trading API
export const tradingApi = {
  createOrder: (order: OrderCreate) =>
    api.post<Order>('/orders', order),
  getOrders: (status?: string, page = 1, pageSize = 50) =>
    api.get<OrderListResponse>('/orders', { params: { status, page, page_size: pageSize } }),
  getOrder: (orderId: string) =>
    api.get<Order>(`/orders/${orderId}`),
  cancelOrder: (orderId: string) =>
    api.delete<{ message: string }>(`/orders/${orderId}`),
};

// Market Data API
export const marketDataApi = {
  getQuote: (symbol: string) =>
    api.get<StockQuote>(`/stocks/${symbol}/quote`),
  getInfo: (symbol: string) =>
    api.get<StockInfo>(`/stocks/${symbol}/info`),
  getHistory: (symbol: string, period = '1mo', interval = '1d') =>
    api.get<HistoricalDataResponse>(`/stocks/${symbol}/history`, { params: { period, interval } }),
  search: (query: string) =>
    api.get<SearchResult[]>('/stocks/search', { params: { q: query } }),
};

// Analysis API
export const analysisApi = {
  getAnalysis: (symbol: string) =>
    api.get<AnalysisResult>(`/analysis/${symbol}`),
  getIndicators: (symbol: string) =>
    api.get<TechnicalIndicators>(`/analysis/${symbol}/indicators`),
  getStockInfo: (symbol: string) =>
    api.get<StockInfo>(`/analysis/${symbol}/info`),
};

// Watchlist API
export const watchlistApi = {
  getWatchlists: () =>
    api.get<WatchlistListResponse>('/watchlist'),
  getWatchlist: (id: string) =>
    api.get<Watchlist>(`/watchlist/${id}`),
  createWatchlist: (data: WatchlistCreate) =>
    api.post<Watchlist>('/watchlist', data),
  updateWatchlist: (id: string, data: Partial<WatchlistCreate>) =>
    api.patch<Watchlist>(`/watchlist/${id}`, data),
  deleteWatchlist: (id: string) =>
    api.delete<{ message: string }>(`/watchlist/${id}`),
  addItem: (watchlistId: string, symbol: string, notes?: string) =>
    api.post<Watchlist>(`/watchlist/${watchlistId}/items`, { symbol, notes }),
  removeItem: (watchlistId: string, symbol: string) =>
    api.delete<Watchlist>(`/watchlist/${watchlistId}/items/${symbol}`),
};

// Risk Management API
export const riskApi = {
  getLimits: () =>
    api.get<RiskLimits>('/risk/limits'),
  updateLimits: (data: RiskLimitsUpdate) =>
    api.patch<RiskLimits>('/risk/limits', data),
  getSummary: () =>
    api.get<RiskSummary>('/risk/summary'),
  getDailyMetrics: (date?: string) =>
    api.get<DailyRiskMetrics>('/risk/daily-metrics', { params: { date } }),
};

// Instruments API
export const instrumentsApi = {
  search: (query: string, exchange?: string, limit = 20) =>
    api.get<Instrument[]>('/instruments/search', { params: { q: query, exchange, limit } }),
  getBySymbol: (symbol: string) =>
    api.get<Instrument>(`/instruments/${symbol}`),
  getSectors: () =>
    api.get<string[]>('/instruments/sectors'),
};

// Alerts API
export const alertsApi = {
  getAlerts: (status?: string) =>
    api.get<{ alerts: Alert[] }>('/alerts', { params: { status } }),
  getAlert: (id: string) =>
    api.get<Alert>(`/alerts/${id}`),
  createAlert: (data: AlertCreate) =>
    api.post<Alert>('/alerts', data),
  updateAlert: (id: string, data: Partial<AlertCreate> & { enabled?: boolean }) =>
    api.patch<Alert>(`/alerts/${id}`, data),
  deleteAlert: (id: string) =>
    api.delete<{ message: string }>(`/alerts/${id}`),
};

// Signals API
export interface Signal {
  id: string;
  symbol: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  status: string;
  strategy_name: string;
  timeframe: string;
  strength: number;
  confidence: number;
  price_at_signal: number;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  risk_reward_ratio: number | null;
  indicators: Record<string, unknown>;
  notes: string | null;
  generated_at: string;
  expires_at: string | null;
  is_executed: boolean;
}

export interface SignalGenerateRequest {
  symbols: string[];
  strategy_name?: string;
  timeframe?: string;
}

export const signalsApi = {
  getSignals: (status?: string, symbol?: string, limit = 50, offset = 0) =>
    api.get<{ signals: Signal[]; total: number }>('/signals', {
      params: { status, symbol, limit, offset },
    }),
  getSignal: (id: string) =>
    api.get<Signal>(`/signals/${id}`),
  generateSignals: (data: SignalGenerateRequest) =>
    api.post<{ signals: Signal[]; signals_generated: number }>('/signals/generate', data),
  getStrategies: () =>
    api.get<{ strategies: { name: string; description: string; default_timeframe: string; parameters: Record<string, unknown> }[] }>('/signals/strategies'),
};

// Backtest API
export interface BacktestRequest {
  symbol: string;
  strategy_name: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  timeframe?: string;
  strategy_params?: Record<string, unknown>;
}

export interface BacktestPerformance {
  total_return: number | null;
  annualized_return: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number | null;
  calmar_ratio: number | null;
}

export interface BacktestTradeStats {
  total_trades: number | null;
  winning_trades: number | null;
  losing_trades: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  avg_trade: number | null;
  largest_win: number | null;
  largest_loss: number | null;
}

export interface BacktestTrade {
  id: string;
  symbol: string;
  side: string;
  entry_date: string;
  entry_price: number;
  exit_date: string | null;
  exit_price: number | null;
  quantity: number;
  pnl: number | null;
  pnl_pct: number | null;
  is_winner: boolean | null;
  exit_reason: string | null;
}

export interface BacktestResult {
  id: string;
  user_id: string;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number | null;
  status: string;
  error_message: string | null;
  performance: BacktestPerformance;
  trade_stats: BacktestTradeStats;
  equity_curve: { date: string; equity: number }[] | null;
  drawdown_curve: { date: string; drawdown: number }[] | null;
  trades: BacktestTrade[] | null;
  created_at: string;
  completed_at: string | null;
}

export interface BacktestListItem {
  id: string;
  strategy_name: string;
  symbol: string;
  status: string;
  total_return: number | null;
  sharpe_ratio: number | null;
  total_trades: number | null;
  win_rate: number | null;
  created_at: string;
  completed_at: string | null;
}

export const backtestApi = {
  runBacktest: (data: BacktestRequest) =>
    api.post<BacktestResult>('/backtest', data),
  getBacktests: (limit = 50, offset = 0) =>
    api.get<BacktestListItem[]>('/backtest', { params: { limit, offset } }),
  getBacktest: (id: string, includeTrades = true) =>
    api.get<BacktestResult>(`/backtest/${id}`, { params: { include_trades: includeTrades } }),
  deleteBacktest: (id: string) =>
    api.delete(`/backtest/${id}`),
  getStrategies: () =>
    api.get<{ name: string; description: string }[]>('/backtest/strategies'),
};

// Algo Trading API
import type {
  AlgoStrategy,
  AlgoStrategyCreate,
  AlgoStrategyUpdate,
  CircuitBreakerStatus,
  ClosePositionRequest,
  ClosePositionResponse,
  StrategyExecution,
  Universe,
  UniverseCreate,
  KillSwitchState,
  StrategyStatus,
  AlgoPnLSummary,
  PnLByStrategyResponse,
  PnLHistoryResponse,
  UnrealizedPnLResponse,
  AlgoPosition,
  SquareOffStrategyRequest,
  SquareOffStrategyResponse,
} from '@/types';

export const algoApi = {
  // Strategies
  getStrategies: (status?: StrategyStatus) =>
    api.get<AlgoStrategy[]>('/algo/strategies', { params: { status_filter: status } }),
  getStrategy: (id: string) =>
    api.get<AlgoStrategy>(`/algo/strategies/${id}`),
  createStrategy: (data: AlgoStrategyCreate) =>
    api.post<AlgoStrategy>('/algo/strategies', data),
  updateStrategy: (id: string, data: AlgoStrategyUpdate) =>
    api.patch<AlgoStrategy>(`/algo/strategies/${id}`, data),
  deleteStrategy: (id: string) =>
    api.delete(`/algo/strategies/${id}`),
  enableStrategy: (id: string) =>
    api.post<AlgoStrategy>(`/algo/strategies/${id}/enable`),
  disableStrategy: (id: string) =>
    api.post<AlgoStrategy>(`/algo/strategies/${id}/disable`),
  triggerStrategy: (id: string, symbols?: string[]) =>
    api.post<{ task_id: string; status: string }>(`/algo/strategies/${id}/trigger`, { symbols }),
  getExecutionHistory: (strategyId: string, limit = 50) =>
    api.get<StrategyExecution[]>(`/algo/strategies/${strategyId}/executions`, { params: { limit } }),

  // Kill Switch
  getKillSwitchStatus: () =>
    api.get<KillSwitchState>('/algo/kill-switch'),
  toggleKillSwitch: (activate: boolean, reason?: string, squareOff = false) =>
    api.post<KillSwitchState>('/algo/kill-switch', { activate, reason, square_off: squareOff }),
  emergencyStop: () =>
    api.post<{ status: string; strategies_disabled: number }>('/algo/emergency-stop'),

  // Circuit Breaker
  getCircuitBreakerStatus: (strategyId: string) =>
    api.get<CircuitBreakerStatus>(`/algo/strategies/${strategyId}/circuit-breaker`),
  resetCircuitBreaker: (strategyId: string) =>
    api.post<{ status: string; strategy_id: string }>(`/algo/strategies/${strategyId}/circuit-breaker/reset`),

  // Universes
  getUniverses: () =>
    api.get<Universe[]>('/algo/universes'),
  getUniverse: (id: string) =>
    api.get<Universe>(`/algo/universes/${id}`),
  createUniverse: (data: UniverseCreate) =>
    api.post<Universe>('/algo/universes', data),
  updateUniverse: (id: string, data: Partial<UniverseCreate>) =>
    api.patch<Universe>(`/algo/universes/${id}`, data),
  deleteUniverse: (id: string) =>
    api.delete(`/algo/universes/${id}`),
  getUniverseSymbols: (id: string) =>
    api.get<{ universe_id: string; name: string; symbols: string[]; count: number }>(`/algo/universes/${id}/symbols`),
  seedAllUniverses: () =>
    api.post<{
      message: string;
      predefined_count: number;
      dynamic_count: number;
      predefined_universes: string[];
      dynamic_universes: string[];
    }>('/algo/universes/seed-all'),
  refreshAllUniverses: () =>
    api.post<{
      message: string;
      refreshed_count: number;
      dynamic_universes: string[];
    }>('/algo/universes/refresh-all'),

  // Positions
  getPositions: (strategyId?: string, status?: string) =>
    api.get<AlgoPosition[]>('/algo/positions', { params: { strategy_id: strategyId, status } }),

  // Profit booking for algo positions
  getAlgoProfitBookingRules: (positionId: string) =>
    api.get<ProfitBookingRules>(`/algo/positions/${positionId}/profit-booking`),
  updateAlgoProfitBookingRules: (positionId: string, rules: ProfitBookingRules) =>
    api.patch<ProfitBookingRules>(`/algo/positions/${positionId}/profit-booking`, rules),

  // Trailing stop for algo positions
  getAlgoTrailingStopConfig: (positionId: string) =>
    api.get<TrailingStopConfig>(`/algo/positions/${positionId}/trailing-stop`),
  updateAlgoTrailingStop: (positionId: string, config: TrailingStopUpdate) =>
    api.patch<TrailingStopConfig>(`/algo/positions/${positionId}/trailing-stop`, config),

  // Position Exit Endpoints
  closePosition: (strategyId: string, symbol: string, data?: ClosePositionRequest) =>
    api.post<ClosePositionResponse>(`/algo/strategies/${strategyId}/positions/${symbol}/close`, data || {}),
  squareOffStrategy: (strategyId: string, data?: SquareOffStrategyRequest) =>
    api.post<SquareOffStrategyResponse>(`/algo/strategies/${strategyId}/square-off`, data || {}),

  // P&L Endpoints
  getPnLSummary: () =>
    api.get<AlgoPnLSummary>('/algo/pnl/summary'),
  getPnLByStrategy: () =>
    api.get<PnLByStrategyResponse>('/algo/pnl/by-strategy'),
  getPnLHistory: (days = 30) =>
    api.get<PnLHistoryResponse>('/algo/pnl/history', { params: { days } }),
  getUnrealizedPnL: () =>
    api.get<UnrealizedPnLResponse>('/algo/pnl/unrealized'),
};

// ============================================================================
// Broker Integration API
// ============================================================================

export type BrokerType = 'fyers' | 'angelone' | 'dhan' | 'zerodha';

export interface BrokerCredentialStatus {
  broker_type: string;
  is_configured: boolean;
  is_connected: boolean;
  is_active: boolean;
  client_id?: string | null;
  last_used_at?: string | null;
  token_expires_at?: string | null;
}

export interface BrokerListResponse {
  brokers: BrokerCredentialStatus[];
}

export interface BrokerCredentialCreate {
  broker_type: BrokerType;
  client_id: string;
  secret_key: string;
  redirect_uri: string;
}

export interface BrokerCredentialResponse {
  id: string;
  broker_type: string;
  client_id: string;
  redirect_uri: string;
  is_connected: boolean;
  is_active: boolean;
  token_expires_at?: string | null;
  created_at: string;
  updated_at: string;
  last_used_at?: string | null;
}

export interface BrokerAuthUrlResponse {
  auth_url: string;
  broker_type: string;
  message: string;
}

export interface BrokerCallbackRequest {
  auth_code: string;
  state?: string;
}

export interface BrokerCallbackResponse {
  success: boolean;
  message: string;
  broker_type: string;
  is_connected: boolean;
}

export interface BrokerDisconnectResponse {
  success: boolean;
  message: string;
  broker_type: string;
}

export const brokersApi = {
  // List all broker integrations
  listBrokers: () =>
    api.get<BrokerListResponse>('/brokers'),

  // Get status of a specific broker
  getBrokerStatus: (brokerType: BrokerType) =>
    api.get<BrokerCredentialStatus>(`/brokers/${brokerType}`),

  // Save broker credentials
  saveCredentials: (data: BrokerCredentialCreate) =>
    api.post<BrokerCredentialResponse>('/brokers', data),

  // Delete broker credentials permanently
  deleteBroker: (brokerType: BrokerType) =>
    api.delete<BrokerDisconnectResponse>(`/brokers/${brokerType}`),

  // Disconnect broker (clear token but keep credentials)
  disconnectBroker: (brokerType: BrokerType) =>
    api.post<BrokerDisconnectResponse>(`/brokers/${brokerType}/disconnect`),

  // Fyers-specific endpoints
  getFyersAuthUrl: () =>
    api.get<BrokerAuthUrlResponse>('/brokers/fyers/auth-url'),

  fyersCallback: (data: BrokerCallbackRequest) =>
    api.post<BrokerCallbackResponse>('/brokers/fyers/callback', data),
};

// User Settings Types
export type DataProviderType = 'yahoo' | 'fyers' | 'nse';

export interface UserSettings {
  id: string;
  user_id: string;
  data_provider: DataProviderType;
  default_market: 'IN' | 'US';
  currency: 'INR' | 'USD' | 'EUR' | 'GBP';
  theme: 'light' | 'dark' | 'system';
  created_at: string;
  updated_at: string;
  data_provider_available: boolean;
  data_provider_message: string | null;
}

export interface UserSettingsUpdate {
  data_provider?: DataProviderType;
  default_market?: 'IN' | 'US';
  currency?: 'INR' | 'USD' | 'EUR' | 'GBP';
  theme?: 'light' | 'dark' | 'system';
}

export interface DataProviderInfo {
  id: DataProviderType;
  name: string;
  description: string;
  requires_auth: boolean;
  is_available: boolean;
  message: string | null;
}

export interface AvailableProvidersResponse {
  providers: DataProviderInfo[];
  current: DataProviderType;
}

// Settings API
export const settingsApi = {
  // Get user settings
  getSettings: () =>
    api.get<UserSettings>('/settings'),

  // Update user settings
  updateSettings: (data: UserSettingsUpdate) =>
    api.patch<UserSettings>('/settings', data),

  // Get available data providers
  getProviders: () =>
    api.get<AvailableProvidersResponse>('/settings/providers'),
};
