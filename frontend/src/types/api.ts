// ============== Common Types ==============

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT' | 'SL' | 'SL_M';
export type OrderStatus = 'PENDING' | 'OPEN' | 'FILLED' | 'PARTIALLY_FILLED' | 'CANCELLED' | 'REJECTED' | 'EXPIRED';
export type ProductType = 'DELIVERY' | 'INTRADAY';
export type TrendType = 'BULLISH' | 'BEARISH' | 'NEUTRAL';
export type SignalType = 'BUY' | 'SELL' | 'HOLD';

// ============== Auth Types ==============

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: User;
  token: TokenResponse;
}

// ============== Portfolio Types ==============

export interface PortfolioInfo {
  id: string;
  name: string;
  description: string | null;
  currency: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface PortfolioCreate {
  name: string;
  description?: string | null;
  currency?: string;
  is_default?: boolean;
}

export interface PortfolioUpdate {
  name?: string;
  description?: string | null;
  currency?: string;
  is_default?: boolean;
}

export interface PortfolioListResponse {
  portfolios: PortfolioInfo[];
  total_count: number;
}

export interface ProfitBookingRule {
  target_pct: number;
  quantity_pct: number;
}

export interface ProfitBookingRules {
  enabled: boolean;
  rules: ProfitBookingRule[];
  executed: number[];
}

export interface TrailingStopConfig {
  enabled: boolean;
  percentage: number | null;
  current_stop_price: number | null;
  highest_price: number | null;
  lowest_price: number | null;
}

export interface TrailingStopUpdate {
  enabled: boolean;
  percentage?: number | null;
}

export interface Position {
  id: string;
  portfolio_id?: string | null;
  symbol: string;
  quantity: number;
  avg_cost: number;
  product_type: ProductType;
  realized_pnl: number;
  current_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  trailing_stop?: TrailingStopConfig | null;
  sector?: string;
  profit_booking_rules?: ProfitBookingRules | null;
}

export interface PortfolioSummary {
  portfolio_id?: string | null;
  portfolio_name?: string | null;
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  cash_balance: number;
  positions_count: number;
  day_change: number | null;
  day_change_pct: number | null;
}

export interface PortfolioResponse {
  summary: PortfolioSummary;
  positions: Position[];
}

export interface PortfolioDetailResponse {
  portfolio: PortfolioInfo;
  summary: PortfolioSummary;
  positions: Position[];
}

export interface Trade {
  id: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  fees: number;
  total_value: number | null;
  executed_at: string;
}

export interface TradeHistoryResponse {
  trades: Trade[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface DailyPnL {
  id: string;
  date: string;
  total_value: number;
  total_cost: number;
  total_pnl: number;
  cash_balance: number;
  day_pnl: number;
  trades_count: number;
}

export interface DailyPnLHistory {
  records: DailyPnL[];
  total_count: number;
  period_pnl: number;
  period_return_pct: number;
}

// ============== Funds Types ==============

export interface FundsResponse {
  id: string;
  user_id: string;
  cash_balance: number;
  margin_used: number;
  collateral: number;
  available_cash: number;
  total_balance: number;
  available_margin: number;
}

export interface FundsDepositRequest {
  amount: number;
  note?: string;
}

export interface FundsWithdrawRequest {
  amount: number;
  note?: string;
}

export interface FundsResetRequest {
  initial_balance?: number;
}

// ============== Order Types ==============

export interface Order {
  id: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: number;
  price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  status: OrderStatus;
  filled_quantity: number;
  filled_price: number | null;
  fees: number;
  notes: string | null;
  created_at: string;
  filled_at: string | null;
  is_amo: boolean;
  scheduled_for: string | null;
}

export interface OrderListResponse {
  orders: Order[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface OrderCreate {
  symbol: string;
  side: OrderSide;
  quantity: number;
  order_type?: OrderType;
  price?: number;
  stop_loss?: number;
  take_profit?: number;
  product_type?: ProductType;
  is_amo?: boolean;
}

// ============== Market Data Types ==============

export type MarketSession = 'pre_market' | 'regular' | 'post_market' | 'closed';

export interface StockQuote {
  symbol: string;
  price: number;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  change: number | null;
  change_pct: number | null;
  timestamp: string | null;
  // Extended hours (pre-market) data
  pre_market_price: number | null;
  pre_market_change: number | null;
  pre_market_change_pct: number | null;
  pre_market_time: string | null;
  // Extended hours (post-market/after-hours) data
  post_market_price: number | null;
  post_market_change: number | null;
  post_market_change_pct: number | null;
  post_market_time: string | null;
  // Current market session
  market_session: MarketSession | null;
}

export interface StockInfo {
  symbol: string;
  name: string | null;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  dividend_yield: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
}

export interface HistoricalDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoricalDataResponse {
  symbol: string;
  interval: string;
  data: HistoricalDataPoint[];
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

// ============== Watchlist Types ==============

export interface WatchlistItem {
  id: string;
  symbol: string;
  notes: string | null;
  added_at: string;
  current_price: number | null;
  change: number | null;
  change_pct: number | null;
}

export interface Watchlist {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  items: WatchlistItem[];
  items_count: number;
}

export interface WatchlistListResponse {
  watchlists: Watchlist[];
}

export interface WatchlistCreate {
  name: string;
  description?: string;
}

// ============== Risk Types ==============

export interface RiskLimits {
  id: string;
  user_id: string;
  max_position_size: number;
  max_position_pct: number;
  max_positions: number;
  max_daily_loss: number;
  max_daily_loss_pct: number;
  max_order_value: number;
  max_orders_per_day: number;
  allow_intraday: boolean;
  allow_short_selling: boolean;
}

export interface RiskLimitsUpdate {
  max_position_size?: number;
  max_position_pct?: number;
  max_positions?: number;
  max_daily_loss?: number;
  max_daily_loss_pct?: number;
  max_order_value?: number;
  max_orders_per_day?: number;
  allow_intraday?: boolean;
  allow_short_selling?: boolean;
}

export interface RiskSummary {
  daily_pnl: number;
  daily_pnl_pct: number;
  daily_loss_remaining: number;
  orders_today: number;
  orders_remaining: number;
  positions_count: number;
  positions_remaining: number;
  largest_position_pct: number;
  is_trading_blocked: boolean;
  block_reason: string | null;
}

export interface DailyRiskMetrics {
  id: string;
  user_id: string;
  date: string;
  orders_count: number;
  trades_count: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_traded_value: number;
  daily_loss_limit_breached: boolean;
  position_limit_breached: boolean;
}

// ============== Analysis Types ==============

export interface TechnicalIndicators {
  symbol: string;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_12: number | null;
  ema_26: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  rsi_14: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  atr_14: number | null;
  volume_sma_20: number | null;
}

export interface SignalStrength {
  signal: SignalType;
  strength: number;
  confidence: number;
}

export interface AnalysisResult {
  symbol: string;
  current_price: number;
  indicators: TechnicalIndicators;
  signal: SignalStrength;
  support_levels: number[];
  resistance_levels: number[];
  trend: TrendType;
}

export interface StockInfo {
  symbol: string;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  sector: string | null;
  industry: string | null;

  // Price info
  current_price: number | null;
  previous_close: number | null;
  open: number | null;
  day_high: number | null;
  day_low: number | null;

  // 52-week range
  week_52_high: number | null;
  week_52_low: number | null;

  // Volume
  volume: number | null;
  avg_volume: number | null;
  avg_volume_10d: number | null;

  // Market cap and shares
  market_cap: number | null;
  shares_outstanding: number | null;
  float_shares: number | null;

  // Fundamentals
  pe_ratio: number | null;
  forward_pe: number | null;
  peg_ratio: number | null;
  price_to_book: number | null;
  eps: number | null;
  forward_eps: number | null;

  // Dividends
  dividend_yield: number | null;
  dividend_rate: number | null;
  ex_dividend_date: string | null;

  // Analyst recommendations
  target_mean_price: number | null;
  target_high_price: number | null;
  target_low_price: number | null;
  recommendation: string | null;
  num_analyst_opinions: number | null;

  // Beta and other metrics
  beta: number | null;
  trailing_annual_return: number | null;
}

// ============== Instrument Types ==============

export interface Instrument {
  id: string;
  symbol: string;
  name: string;
  exchange: string;
  segment: string;
  token: string | null;
  isin: string | null;
  lot_size: number;
  tick_size: number;
  expiry: string | null;
  strike: number | null;
  option_type: string | null;
  underlying: string | null;
  instrument_type: string;
  series: string | null;
  is_active: boolean;
  is_tradeable: boolean;
  sector: string | null;
  industry: string | null;
}

// ============== Alert Types ==============

export type AlertCondition = 'ABOVE' | 'BELOW';
export type AlertStatus = 'ACTIVE' | 'TRIGGERED' | 'EXPIRED' | 'DISABLED';

export interface Alert {
  id: string;
  user_id: string;
  symbol: string;
  condition: AlertCondition;
  target_price: number;
  status: AlertStatus;
  triggered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertCreate {
  symbol: string;
  condition: AlertCondition;
  target_price: number;
}

export interface PriceAlert {
  id: string;
  symbol: string;
  target_price: number;
  condition: AlertCondition;
  status: AlertStatus;
  created_at: string;
  triggered_at: string | null;
}

export interface NotificationPreferences {
  order_execution: boolean;
  price_alerts: boolean;
  daily_summary: boolean;
  risk_breaches: boolean;
}

// ============== WebSocket Types ==============

export interface WebSocketMessage {
  type: 'quote' | 'order_update' | 'alert' | 'notification';
  data: unknown;
}

export interface QuoteUpdate {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  timestamp: string;
}

export interface OrderUpdateMessage {
  order_id: string;
  status: OrderStatus;
  filled_quantity: number;
  filled_price: number | null;
}

// ============== API Error Types ==============

export interface ApiError {
  detail: string;
  status_code?: number;
}

// ============== Algo Trading Types ==============

export type StrategyStatus = 'ACTIVE' | 'DISABLED' | 'PAUSED' | 'ERROR' | 'KILLED';
export type ScheduleType = 'INTERVAL' | 'CRON' | 'MARKET_OPEN' | 'MARKET_CLOSE' | 'CONTINUOUS';
export type PositionSizingMethod = 'FIXED_QUANTITY' | 'FIXED_AMOUNT' | 'PERCENT_OF_PORTFOLIO' | 'RISK_BASED' | 'VOLATILITY_ADJUSTED';
export type ExecutionStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type ProfitCutoffAction = 'PAUSE_STRATEGY' | 'CLOSE_POSITIONS_AND_PAUSE' | 'CLOSE_POSITIONS_AND_CONTINUE' | 'NOTIFY_ONLY';

export interface AlgoStrategy {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  strategy_type: string;
  strategy_config: Record<string, unknown> | null;
  status: StrategyStatus;
  universe_id: string | null;
  symbols: string[] | null;
  schedule_type: ScheduleType;
  interval_seconds: number | null;
  cron_expression: string | null;
  position_sizing_method: PositionSizingMethod;
  position_size_value: number;
  max_position_value: number | null;
  max_daily_loss: number;
  max_consecutive_losses: number;
  // Profit cutoff settings
  max_daily_profit: number | null;
  overall_profit_target: number | null;
  profit_cutoff_action: ProfitCutoffAction;
  is_paper_trading: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  total_trades: number;
  winning_trades: number;
  total_pnl: number;
  created_at: string;
  updated_at: string;
}

export interface AlgoStrategyCreate {
  name: string;
  description?: string;
  strategy_type: string;
  strategy_config?: Record<string, unknown>;
  universe_id?: string;
  symbols?: string[];
  schedule_type?: ScheduleType;
  interval_seconds?: number;
  cron_expression?: string;
  position_sizing_method?: PositionSizingMethod;
  position_size_value?: number;
  max_position_value?: number;
  max_daily_loss?: number;
  max_consecutive_losses?: number;
  // Profit cutoff settings
  max_daily_profit?: number;
  overall_profit_target?: number;
  profit_cutoff_action?: ProfitCutoffAction;
  is_paper_trading?: boolean;
}

export interface AlgoStrategyUpdate {
  name?: string;
  description?: string;
  strategy_config?: Record<string, unknown>;
  universe_id?: string;
  symbols?: string[];
  schedule_type?: ScheduleType;
  interval_seconds?: number;
  cron_expression?: string;
  position_sizing_method?: PositionSizingMethod;
  position_size_value?: number;
  max_position_value?: number;
  max_daily_loss?: number;
  max_consecutive_losses?: number;
  // Profit cutoff settings
  max_daily_profit?: number;
  overall_profit_target?: number;
  profit_cutoff_action?: ProfitCutoffAction;
  is_paper_trading?: boolean;
}

export interface AlgoOrderDetail {
  id: string;
  execution_id: string;
  order_id: string | null;
  strategy_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  order_type: string;
  price: number | null;
  order_status: string;
  filled_quantity: number;
  filled_price: number | null;
  order_value: number;
  filled_at: string | null;
  signal_type: string | null;
  signal_strength: number | null;
  sizing_method: string | null;
  created_at: string;
}

export interface StrategyExecution {
  id: string;
  strategy_id: string;
  status: ExecutionStatus;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  symbols_analyzed: number;
  signals_generated: number;
  orders_placed: number;
  orders_filled: number;
  orders_rejected: number;
  error_message: string | null;
  // P&L tracking
  realized_pnl: number;
  unrealized_pnl: number;
  total_order_value: number;
  positions_opened: number;
  positions_closed: number;
  // Order details - includes symbol, price, quantity, side, filled info
  orders: AlgoOrderDetail[];
}

export interface AlgoOrder {
  id: string;
  execution_id: string;
  order_id: string | null;
  strategy_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  order_type: string;
  price: number | null;
  order_status: 'PENDING' | 'SUBMITTED' | 'FILLED' | 'PARTIALLY_FILLED' | 'REJECTED' | 'CANCELLED';
  filled_quantity: number;
  filled_price: number | null;
  order_value: number;
  filled_at: string | null;
  signal_type: string | null;
  signal_strength: number | null;
  sizing_method: string | null;
  created_at: string;
}

export interface Universe {
  id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  symbols: string[] | null;
  filter_criteria: Record<string, unknown> | null;
  is_system: boolean;
  is_dynamic: boolean;
  created_at: string;
  updated_at: string;
}

export interface UniverseCreate {
  name: string;
  description?: string;
  symbols?: string[];
  filter_criteria?: Record<string, unknown>;
  is_dynamic?: boolean;
}

export interface KillSwitchState {
  is_active: boolean;
  activated_at: string | null;
  reason: string | null;
  square_off_initiated: boolean;
}

export interface CircuitBreakerStatus {
  strategy_id: string;
  is_triggered: boolean;
  trigger_reason: string | null;
  triggered_at: string | null;
  daily_loss: number;
  max_daily_loss: number;
  consecutive_losses: number;
  max_consecutive_losses: number;
  current_drawdown_percent: number;
  max_drawdown_percent: number;
  // Profit cutoff tracking
  daily_profit: number;
  max_daily_profit: number | null;
  overall_profit: number;
  overall_profit_target: number | null;
  profit_cutoff_triggered: boolean;
}

// ============== Algo P&L Types ==============

export interface AlgoPnLSummary {
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  open_positions: number;
  closed_positions: number;
}

export interface StrategyPnL {
  strategy_id: string;
  strategy_name: string;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  open_positions: number;
  closed_positions: number;
  status: StrategyStatus;
}

export interface PnLByStrategyResponse {
  strategies: StrategyPnL[];
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  total_pnl: number;
}

export interface AlgoDailyPnL {
  date: string;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  trades_opened: number;
  trades_closed: number;
  cumulative_pnl: number;
}

export interface PnLHistoryResponse {
  daily_pnl: AlgoDailyPnL[];
  period_start: string;
  period_end: string;
  total_realized_pnl: number;
  total_days: number;
  profitable_days: number;
  losing_days: number;
}

export interface UnrealizedPnLPosition {
  position_id: string;
  strategy_id: string;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  entry_value: number;
  current_value: number;
}

export interface UnrealizedPnLResponse {
  positions: UnrealizedPnLPosition[];
  total_unrealized_pnl: number;
  total_entry_value: number;
  total_current_value: number;
  positions_count: number;
}

export interface AlgoPosition {
  id: string;
  strategy_id: string;
  user_id: string;
  symbol: string;
  side: string;
  status: string;
  entry_quantity: number;
  entry_price: number;
  entry_at: string;
  exit_quantity: number | null;
  exit_price: number | null;
  exit_at: string | null;
  remaining_quantity: number;
  realized_pnl: number;
  realized_pnl_percent: number;
  // Unrealized P&L fields (for open positions)
  current_price: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_percent: number | null;
  is_winner: boolean | null;
  stop_loss: number | null;
  take_profit: number | null;
  trailing_stop?: TrailingStopConfig | null;
  profit_booking_rules?: ProfitBookingRules | null;
  created_at: string;
  updated_at: string;
}

// ============== Close Position Types ==============

export interface ClosePositionRequest {
  exit_price?: number | null;
  quantity?: number | null;
}

export interface ClosePositionResponse {
  position_id: string;
  symbol: string;
  side: string;
  closed_quantity: number;
  remaining_quantity: number;
  entry_price: number;
  exit_price: number;
  realized_pnl: number;
  realized_pnl_percent: number;
  is_winner: boolean;
  status: string;
  message: string;
}

export interface SquareOffStrategyRequest {
  exit_prices?: Record<string, number> | null;
}

export interface SquareOffStrategyResponse {
  strategy_id: string;
  strategy_name: string;
  positions_closed: number;
  total_realized_pnl: number;
  closed_positions: ClosePositionResponse[];
  message: string;
}
