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

export interface ProfitLockConfig {
  enabled: boolean;
  activated: boolean;
  profit_lock_price: number | null;
}

export interface ProfitLockUpdate {
  enabled: boolean;
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

// ============== Order Template Types ==============

export interface OrderTemplate {
  id: string;
  user_id: string;
  name: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: number | null;
  quantity_pct: number | null;
  stop_loss_pct: number | null;
  take_profit_pct: number | null;
  is_favorite: boolean;
  use_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrderTemplateCreate {
  name: string;
  symbol: string;
  side: OrderSide;
  order_type?: OrderType;
  quantity?: number | null;
  quantity_pct?: number | null;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  is_favorite?: boolean;
}

export interface OrderTemplateUpdate {
  name?: string;
  symbol?: string;
  side?: OrderSide;
  order_type?: OrderType;
  quantity?: number | null;
  quantity_pct?: number | null;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  is_favorite?: boolean;
}

export interface OrderTemplateListResponse {
  templates: OrderTemplate[];
  total_count: number;
}

export interface OrderFromTemplateExecute {
  current_price: number;
  quantity_override?: number | null;
  confirm?: boolean;
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
  sort_order: number;
  added_at: string;
  current_price: number | null;
  change: number | null;
  change_pct: number | null;
}

export interface Watchlist {
  id: string;
  name: string;
  description: string | null;
  sort_order: number;
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
export type StrategyProductType = 'DELIVERY' | 'INTRADAY' | 'MARGIN' | 'SLB';

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
  // Product type for orders (CNC/MIS/MTF)
  product_type: StrategyProductType;
  // Strategy-level default trailing stop and profit booking settings
  default_trailing_stop_enabled: boolean;
  default_trailing_stop_pct: number | null;
  default_profit_booking_rules: ProfitBookingRules | null;
  // Profit lock: locks stop loss at profit level once threshold is reached
  default_profit_lock_enabled: boolean;
  // Trading time window fields
  trading_start_time: string | null; // HH:MM:SS format
  trading_end_time: string | null; // HH:MM:SS format
  trading_timezone: string;
  active_trading_days: number[] | null; // 0=Monday, 6=Sunday
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
  // Product type for orders (CNC/MIS/MTF)
  product_type?: StrategyProductType;
  // Strategy-level default trailing stop and profit booking settings
  default_trailing_stop_enabled?: boolean;
  default_trailing_stop_pct?: number;
  default_profit_booking_rules?: ProfitBookingRules;
  // Profit lock: locks stop loss at profit level once threshold is reached
  default_profit_lock_enabled?: boolean;
  // Trading time window fields
  trading_start_time?: string; // HH:MM:SS format
  trading_end_time?: string; // HH:MM:SS format
  trading_timezone?: string; // IANA timezone, default: Asia/Kolkata
  active_trading_days?: number[]; // 0=Monday, 6=Sunday
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
  // Product type for orders (CNC/MIS/MTF)
  product_type?: StrategyProductType;
  // Strategy-level default trailing stop and profit booking settings
  default_trailing_stop_enabled?: boolean;
  default_trailing_stop_pct?: number;
  default_profit_booking_rules?: ProfitBookingRules;
  // Profit lock: locks stop loss at profit level once threshold is reached
  default_profit_lock_enabled?: boolean;
  // Trading time window fields
  trading_start_time?: string | null; // HH:MM:SS format
  trading_end_time?: string | null; // HH:MM:SS format
  trading_timezone?: string; // IANA timezone
  active_trading_days?: number[] | null; // 0=Monday, 6=Sunday
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

// ============== Composite Strategy Types ==============

export type CombineLogic = 'AND' | 'OR' | 'MAJORITY' | 'WEIGHTED';

export interface CompositeStrategyComponent {
  strategy: string;
  params?: Record<string, unknown>;
  weight?: number;
  required?: boolean;
}

export interface CompositeStrategyCreate {
  name: string;
  description?: string;
  components: CompositeStrategyComponent[];
  combine_logic: CombineLogic;
  min_agreement_pct?: number;
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
  product_type?: StrategyProductType;
  // Strategy-level default trailing stop and profit booking settings
  default_trailing_stop_enabled?: boolean;
  default_trailing_stop_pct?: number;
  default_profit_booking_rules?: ProfitBookingRules;
  // Profit lock: locks stop loss at profit level once threshold is reached
  default_profit_lock_enabled?: boolean;
  // Trading time window fields
  trading_start_time?: string; // HH:MM:SS format
  trading_end_time?: string; // HH:MM:SS format
  trading_timezone?: string; // IANA timezone, default: Asia/Kolkata
  active_trading_days?: number[]; // 0=Monday, 6=Sunday
}

export interface CompositeStrategyResponse {
  id: string;
  name: string;
  description: string | null;
  strategy_type: string;
  components: CompositeStrategyComponent[];
  combine_logic: string;
  message: string;
}

export interface CompositeStrategyDryRunRequest {
  components: CompositeStrategyComponent[];
  combine_logic: CombineLogic;
  min_agreement_pct?: number;
  symbol: string;
  days_back?: number;
}

export interface CompositeStrategyDryRunResponse {
  success: boolean;
  symbol: string;
  test_period_days: number;
  total_return: number | null;
  win_rate: number | null;
  total_trades: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  profit_factor: number | null;
  component_signals?: Array<Record<string, unknown>>;
  error_message: string | null;
}

// ============== DSL Strategy Types ==============

export interface DSLEntryRule {
  condition: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence?: number;
  strength?: number;
}

export interface DSLExitConfig {
  stop_loss_pct: number;
  take_profit_pct: number;
  trailing_stop_pct?: number;
}

export interface DSLRules {
  entry: DSLEntryRule[];
  exit: DSLExitConfig;
  filters?: string[];
}

export interface DSLIndicatorConfig {
  [indicator: string]: Record<string, number>;
}

export interface DSLStrategyDefinition {
  name: string;
  version?: number;
  description?: string;
  timeframe?: string;
  rules: DSLRules;
  indicators?: DSLIndicatorConfig[];
}

export interface DSLStrategyCreate {
  name: string;
  description?: string;
  definition: DSLStrategyDefinition;
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
  max_daily_profit?: number;
  overall_profit_target?: number;
  profit_cutoff_action?: ProfitCutoffAction;
  is_paper_trading?: boolean;
  product_type?: StrategyProductType;
  default_trailing_stop_enabled?: boolean;
  default_trailing_stop_pct?: number;
  default_profit_booking_rules?: ProfitBookingRules;
  // Profit lock: locks stop loss at profit level once threshold is reached
  default_profit_lock_enabled?: boolean;
  // Trading time window fields
  trading_start_time?: string; // HH:MM:SS format
  trading_end_time?: string; // HH:MM:SS format
  trading_timezone?: string; // IANA timezone, default: Asia/Kolkata
  active_trading_days?: number[]; // 0=Monday, 6=Sunday
}

export interface DSLStrategyResponse {
  id: string;
  name: string;
  description: string | null;
  strategy_type: string;
  definition: DSLStrategyDefinition;
  message: string;
}

// ============== Research Types ==============

export interface IndexPerformance {
  symbol: string;
  name?: string | null;
  close?: number | null;
  change?: number | null;
  change_pct?: number | null;
}

export interface MarketSummary {
  indices: IndexPerformance[];
  overall_trend?: string | null;
}

export interface TopMover {
  symbol: string;
  name?: string | null;
  close?: number | null;
  change_pct?: number | null;
  volume?: number | null;
  reason?: string | null;
}

export interface SectorDigest {
  sector: string;
  change_pct?: number | null;
  top_stock?: string | null;
  stock_count?: number | null;
}

export interface VolumeLeader {
  symbol: string;
  name?: string | null;
  volume?: number | null;
  avg_volume?: number | null;
  volume_ratio?: number | null;
  price_change_pct?: number | null;
}

export interface BreakoutCandidate {
  symbol: string;
  name?: string | null;
  pattern?: string | null;
  current_price?: number | null;
  breakout_level?: number | null;
  strength?: number | null;
}

export interface NewsHighlight {
  title: string;
  source?: string | null;
  url?: string | null;
  published_at?: string | null;
  sentiment?: string | null;
  related_symbols?: string[] | null;
}

export interface DailyDigestResponse {
  id: string;
  digest_date: string;
  market_summary?: MarketSummary | null;
  top_gainers?: TopMover[] | null;
  top_losers?: TopMover[] | null;
  sector_performance?: SectorDigest[] | null;
  volume_leaders?: VolumeLeader[] | null;
  breakout_candidates?: BreakoutCandidate[] | null;
  news_highlights?: NewsHighlight[] | null;
  market_sentiment?: number | null;
  created_at: string;
}

export interface DigestListResponse {
  digests: DailyDigestResponse[];
  total_count: number;
}

export interface SectorPerformance {
  sector: string;
  change_1d?: number | null;  // 1-day change %
  change_1w?: number | null;  // 1-week change %
  change_1m?: number | null;  // 1-month change %
  change_3m?: number | null;  // 3-month change %
  change_1y?: number | null;  // 1-year change %
  stock_count: number;
  top_gainer?: string | null;
  top_loser?: string | null;
}

export interface SectorListResponse {
  sectors: SectorPerformance[];
  last_updated?: string | null;
}

export interface SectorStock {
  symbol: string;
  name: string | null;
  current_price: number | null;
  price_change_pct: number | null;
  market_cap?: number | null;
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  dividend_yield?: number | null;
  roe?: number | null;
  revenue_growth?: number | null;
}

export interface SectorStocksResponse {
  sector: string;
  stocks: SectorStock[];
  total_count: number;
  last_updated?: string | null;
}

export interface FundamentalsResponse {
  symbol: string;
  pe_ratio?: number | null;
  forward_pe?: number | null;
  pb_ratio?: number | null;
  ps_ratio?: number | null;
  peg_ratio?: number | null;
  eps?: number | null;
  eps_growth?: number | null;
  revenue?: number | null;
  revenue_growth?: number | null;
  profit_margin?: number | null;
  operating_margin?: number | null;
  roe?: number | null;
  roa?: number | null;
  debt_to_equity?: number | null;
  current_ratio?: number | null;
  quick_ratio?: number | null;
  market_cap?: number | null;
  enterprise_value?: number | null;
  dividend_yield?: number | null;
  dividend_rate?: number | null;
  payout_ratio?: number | null;
  beta?: number | null;
  fifty_two_week_high?: number | null;
  fifty_two_week_low?: number | null;
  avg_volume?: number | null;
  shares_outstanding?: number | null;
  float_shares?: number | null;
  sector?: string | null;
  industry?: string | null;
  last_updated?: string | null;
}

export interface NewsArticle {
  title: string;
  url: string;
  source?: string | null;
  published_at?: string | null;
  summary?: string | null;
  sentiment?: string | null;
  sentiment_score?: number | null;
  related_symbols?: string[] | null;
}

export interface NewsResponse {
  symbol?: string | null;
  articles: NewsArticle[];
  total_count: number;
}

export interface PeerStock {
  symbol: string;
  name: string;
  close: number;
  change_pct: number;
  pe_ratio?: number | null;
  market_cap?: number | null;
  relative_strength?: number | null;
}

export interface PeerComparisonResponse {
  symbol: string;
  sector?: string | null;
  industry?: string | null;
  peers: PeerStock[];
  total_count: number;
}

export interface ResearchNote {
  id: string;
  symbol: string;
  title: string;
  content: string;
  rating?: string | null;
  target_price?: number | null;
  tags?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchNoteCreate {
  symbol: string;
  title: string;
  content: string;
  rating?: string | null;
  target_price?: number | null;
  tags?: string[] | null;
}

export interface ResearchNoteUpdate {
  title?: string | null;
  content?: string | null;
  rating?: string | null;
  target_price?: number | null;
  tags?: string[] | null;
}

export interface ResearchNoteListResponse {
  notes: ResearchNote[];
  total_count: number;
}

export interface StockResearchResponse {
  symbol: string;
  name?: string | null;
  fundamentals?: FundamentalsResponse | null;
  news?: NewsResponse | null;
  peers?: PeerComparisonResponse | null;
  last_updated?: string | null;
}

// ============== Recommendations Types ==============

export interface RecommendationStock {
  symbol: string;
  name?: string | null;
  sector?: string | null;
  industry?: string | null;
  current_price?: number | null;
  price_change_pct?: number | null;

  // Scores (0-100)
  fundamental_score: number;
  technical_score: number;
  combined_score: number;

  // Category
  category: string; // quality, momentum, value, dividend, breakout

  // Fundamental metrics
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  roe?: number | null;
  debt_to_equity?: number | null;
  dividend_yield?: number | null;
  eps_growth?: number | null;

  // Technical metrics
  rsi?: number | null;
  above_200ma?: boolean | null;
  volume_ratio?: number | null;
  pct_from_52w_high?: number | null;

  // Thesis
  thesis?: string | null;
  reasons: string[];
}

export interface RecommendationsResponse {
  date: string;
  recommendations: RecommendationStock[];
  total_count: number;
  by_category: Record<string, number>;
  avg_fundamental_score?: number | null;
  avg_technical_score?: number | null;
}

// ============== Universe Research Types ==============

export interface UniverseStock {
  symbol: string;
  name?: string | null;
  sector?: string | null;
  industry?: string | null;
  current_price?: number | null;
  price_change_pct?: number | null;
  volume?: number | null;

  // Fundamental metrics
  market_cap?: number | null;
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  ps_ratio?: number | null;
  roe?: number | null;
  roa?: number | null;
  profit_margin?: number | null;
  debt_to_equity?: number | null;
  current_ratio?: number | null;
  dividend_yield?: number | null;
  eps_growth?: number | null;
  revenue_growth?: number | null;

  // Score
  fundamental_score?: number | null;
}

export interface UniverseResearchResponse {
  universe: string;
  stocks: UniverseStock[];
  total_count: number;
  by_sector: Record<string, number>;
  filters_applied?: Record<string, string | number> | null;
  last_updated?: string | null;
}

export interface UniverseFilterParams {
  max_pe?: number;
  min_roe?: number;
  max_debt?: number;
  min_dividend?: number;
  sector?: string;
  limit?: number;
}

// ============== Strategy Parameter Customization Types ==============

export interface StrategyParameterSchema {
  name: string;
  type: 'int' | 'float' | 'bool' | 'select';
  default: number | boolean | string | null;
  min_value: number | null;
  max_value: number | null;
  options: string[] | null;
  description: string;
}

export interface StrategyTypeInfo {
  name: string;
  description: string;
  default_timeframe: string;
  parameters: Record<string, unknown>;
}

export interface StrategyTypeDetailResponse {
  name: string;
  description: string;
  default_timeframe: string;
  parameters: StrategyParameterSchema[];
}

// ============================================================================
// Reports & Ledger Types
// ============================================================================

// Transaction types enum
export type TransactionType =
  | 'DEPOSIT'
  | 'WITHDRAWAL'
  | 'BUY'
  | 'SELL'
  | 'DIVIDEND'
  | 'INTEREST'
  | 'FEE'
  | 'TAX'
  | 'TRANSFER_IN'
  | 'TRANSFER_OUT'
  | 'ADJUSTMENT';

// Ledger Entry
export interface LedgerEntry {
  id: string;
  transaction_type: TransactionType;
  amount: number;
  running_cash_balance: number;
  running_margin_used: number;
  running_total_balance: number;
  reference_type: string | null;
  reference_id: string | null;
  symbol: string | null;
  description: string;
  extra_data: Record<string, unknown> | null;
  transaction_date: string;
  created_at: string;
}

export interface LedgerResponse {
  entries: LedgerEntry[];
  total_count: number;
  page: number;
  page_size: number;
  total_in: number;
  total_out: number;
}

export interface LedgerStatementSummary {
  period_start: string;
  period_end: string;
  opening_balance: number;
  closing_balance: number;
  total_deposits: number;
  total_withdrawals: number;
  total_buys: number;
  total_sells: number;
  total_fees: number;
  total_dividends: number;
  net_change: number;
}

export interface LedgerStatementResponse {
  summary: LedgerStatementSummary;
  entries: LedgerEntry[];
}

// Capital Gains
export type TaxType = 'STCG' | 'LTCG' | 'SPECULATIVE';

export interface RealizedGain {
  id: string;
  symbol: string;
  quantity: number;
  cost_basis: number;
  sale_proceeds: number;
  fees: number;
  gain_loss: number;
  gain_loss_pct: number;
  purchase_date: string;
  sale_date: string;
  holding_days: number;
  is_long_term: boolean;
  tax_type: TaxType;
  financial_year: string;
  cost_lot_id: string | null;
  buy_trade_id: string | null;
  sell_trade_id: string | null;
  created_at: string;
}

export interface RealizedGainsListResponse {
  gains: RealizedGain[];
  total: number;
  page: number;
  page_size: number;
}

export interface GainsSummary {
  total_gains: number;
  total_losses: number;
  net_gain_loss: number;
  stcg: number;
  ltcg: number;
  speculative: number;
  stcg_count: number;
  ltcg_count: number;
  speculative_count: number;
  financial_year: string | null;
}

export interface GainsBySymbol {
  symbol: string;
  total_gain: number;
  total_quantity: number;
  trade_count: number;
}

export interface GainsBySymbolListResponse {
  gains: GainsBySymbol[];
  financial_year: string | null;
}

// Broker API Logs
export interface BrokerLog {
  id: string;
  broker_type: string;
  endpoint: string;
  method: string;
  action: string;
  status_code: number | null;
  is_success: boolean;
  error_message: string | null;
  latency_ms: number | null;
  reference_type: string | null;
  reference_id: string | null;
  request_at: string;
  response_at: string | null;
}

export interface BrokerLogDetail extends BrokerLog {
  request_data: Record<string, unknown> | null;
  response_data: Record<string, unknown> | null;
}

export interface BrokerLogListResponse {
  logs: BrokerLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BrokerLogStats {
  broker_type: string;
  action: string | null;
  total_calls: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
}

export interface BrokerLogStatsListResponse {
  stats: BrokerLogStats[];
}

// Activity Log
export type ActivityType =
  | 'LOGIN'
  | 'LOGOUT'
  | 'PASSWORD_CHANGED'
  | 'ORDER_PLACED'
  | 'ORDER_EXECUTED'
  | 'ORDER_CANCELLED'
  | 'ORDER_REJECTED'
  | 'TRADE_COMPLETED'
  | 'POSITION_OPENED'
  | 'POSITION_CLOSED'
  | 'DEPOSIT'
  | 'WITHDRAWAL'
  | 'DIVIDEND_RECEIVED'
  | 'STRATEGY_CREATED'
  | 'STRATEGY_STARTED'
  | 'STRATEGY_STOPPED'
  | 'STRATEGY_DELETED'
  | 'KILL_SWITCH_ACTIVATED'
  | 'CIRCUIT_BREAKER_TRIGGERED'
  | 'RISK_LIMIT_BREACHED'
  | 'RISK_LIMIT_UPDATED'
  | 'MARGIN_CALL'
  | 'BROKER_CONNECTED'
  | 'BROKER_DISCONNECTED'
  | 'BROKER_ERROR'
  | 'SETTINGS_UPDATED'
  | 'WATCHLIST_UPDATED'
  | 'ALERT_CREATED'
  | 'ALERT_TRIGGERED';

export type ActivityCategory =
  | 'auth'
  | 'trading'
  | 'portfolio'
  | 'algo'
  | 'risk'
  | 'broker'
  | 'settings';

export type ActivitySeverity = 'info' | 'warning' | 'error' | 'critical';

export interface ActivityLog {
  id: string;
  user_id: string;
  activity_type: ActivityType;
  category: ActivityCategory;
  title: string;
  description: string;
  entity_type: string | null;
  entity_id: string | null;
  extra_data: Record<string, unknown> | null;
  severity: ActivitySeverity;
  is_read: boolean;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface ActivityLogListResponse {
  activities: ActivityLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  unread_count: number;
}

export interface ActivityUnreadCountResponse {
  unread_count: number;
}

export interface ActivityMarkReadRequest {
  activity_ids?: string[];
  mark_all?: boolean;
}

export interface ActivityMarkReadResponse {
  marked_count: number;
}

// ============== Auto-Trade Types ==============

export type ConfirmationMode = 'AUTO' | 'NOTIFY' | 'DISABLED';
export type ScreenerSourceType = 'PRESET' | 'CUSTOM';
export type PendingTradeStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'EXECUTED';

export interface StrategyTemplate {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  strategy_type: string;
  default_quantity: number;
  position_sizing_method: PositionSizingMethod | null;
  position_size_value: number | null;
  max_position_value: number | null;
  stop_loss_pct: number | null;
  take_profit_pct: number | null;
  trailing_stop_enabled: boolean;
  trailing_stop_pct: number | null;
  parameters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StrategyTemplateCreate {
  name: string;
  description?: string | null;
  strategy_type: string;
  default_quantity?: number;
  position_sizing_method?: PositionSizingMethod | null;
  position_size_value?: number | null;
  max_position_value?: number | null;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  trailing_stop_enabled?: boolean;
  trailing_stop_pct?: number | null;
  parameters?: Record<string, unknown>;
}

export interface StrategyTemplateUpdate {
  name?: string;
  description?: string | null;
  strategy_type?: string;
  default_quantity?: number;
  position_sizing_method?: PositionSizingMethod | null;
  position_size_value?: number | null;
  max_position_value?: number | null;
  stop_loss_pct?: number | null;
  take_profit_pct?: number | null;
  trailing_stop_enabled?: boolean;
  trailing_stop_pct?: number | null;
  parameters?: Record<string, unknown>;
}

export interface AutoTradeConfig {
  id: string;
  user_id: string;
  category: string;
  enabled: boolean;
  confirmation_mode: string; // 'AUTO' | 'NOTIFY' | 'DISABLED'
  strategy_template_id: string | null;
  max_positions_per_day: number;
  max_capital_per_day: number;
  expiry_hours: number;
  weight_technical: number;
  weight_fundamental: number;
  weight_sentiment: number;
  min_confidence: string; // 'high' | 'medium' | 'low'
  screener_source_type: string; // 'PRESET' | 'CUSTOM'
  preset_category: string | null;
  saved_screener_id: string | null;
  run_time: string | null; // HH:MM format for scheduled run time
  created_at: string;
  updated_at: string;
  template?: StrategyTemplate | null;
}

export interface AutoTradeConfigCreate {
  category: string;
  enabled?: boolean;
  confirmation_mode?: string; // 'auto' | 'notify' | 'disabled'
  strategy_template_id?: string | null;
  max_positions_per_day?: number;
  max_capital_per_day?: number;
  expiry_hours?: number;
  weight_technical?: number;
  weight_fundamental?: number;
  weight_sentiment?: number;
  min_confidence?: string; // 'high' | 'medium' | 'low'
  screener_source_type?: string; // 'preset' | 'custom'
  preset_category?: string | null;
  saved_screener_id?: string | null;
  run_time?: string | null; // HH:MM format
}

export interface AutoTradeConfigUpdate {
  enabled?: boolean;
  confirmation_mode?: string; // 'auto' | 'notify' | 'disabled'
  strategy_template_id?: string | null;
  max_positions_per_day?: number;
  max_capital_per_day?: number;
  expiry_hours?: number;
  weight_technical?: number;
  weight_fundamental?: number;
  weight_sentiment?: number;
  min_confidence?: string; // 'high' | 'medium' | 'low'
  screener_source_type?: string; // 'preset' | 'custom'
  preset_category?: string | null;
  saved_screener_id?: string | null;
  run_time?: string | null; // HH:MM format
}

export interface WeightConfigUpdate {
  weight_technical: number;
  weight_fundamental: number;
  weight_sentiment: number;
  min_confidence?: string; // 'high' | 'medium' | 'low'
}

export interface WeightConfigResponse {
  category: string;
  weight_technical: number;
  weight_fundamental: number;
  weight_sentiment: number;
  min_confidence: string; // 'high' | 'medium' | 'low'
  total_weight?: number;
  preview_symbol?: string | null;
  preview_scores?: Record<string, unknown> | null;
}

export interface PendingAutoTrade {
  id: string;
  user_id: string;
  auto_trade_config_id: string;
  category: string;
  recommendation_date: string;
  symbols: string[];
  scores: {
    technical_score?: number;
    fundamental_score?: number;
    sentiment_score?: number;
    combined_score?: number;
    confidence?: string;
    direction?: string;
    position_size_multiplier?: number;
  } | null;
  recommended_strategy_type: string;
  suggested_params: Record<string, unknown> | null;
  status: PendingTradeStatus;
  created_strategy_id: string | null;
  expires_at: string;
  actioned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PendingAutoTradeAction {
  action: 'approve' | 'reject';
  reason?: string | null;
}

export interface PendingAutoTradeListResponse {
  pending_trades: PendingAutoTrade[];
  total: number;
  pending_count: number;
}

export interface AutoTradeConfigListResponse {
  configs: AutoTradeConfig[];
}

export interface StrategyTemplateListResponse {
  templates: StrategyTemplate[];
}
