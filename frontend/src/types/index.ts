/* Shared types for the CriptoLab frontend — mirrors FastAPI response shapes. */

export type Config = {
  mode: string;
  kill_switch: boolean;
};

export type PriceResponse = { symbol: string; interval: string; price: number; ts: number };

export type CandleResponse = {
  symbol: string;
  interval: string;
  open_time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  close_time: number;
  quote_asset_volume: number;
  number_of_trades: number;
  taker_buy_base_asset_volume: number;
  taker_buy_quote_asset_volume: number;
};

export type Ranking = {
  symbol: string;
  score: number;
  confluence: number;
  recommendation: string;
  reason: string;
  trend_1h?: string | null;
  trend_4h?: string | null;
  trend_1d?: string | null;
  price?: number | null;
  return_pct_1d?: number | null;
};

export type PortfolioPosition = {
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  entry_time: string;
  updated_at: string;
};

export type PortfolioTrade = {
  id: number;
  symbol: string;
  interval: string;
  action: string;
  quantity: number;
  price: number;
  commission: number;
  pnl: number;
  pnl_pct: number;
  reason: string;
  created_at: string;
};

export type DecisionEntry = {
  decision_id: string;
  decision_type: string;
  timestamp: string;
  symbol: string | null;
  strategy_name: string | null;
  timeframe: string | null;
  mode: string;
  approved: boolean;
  reason: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  policy_version: string | null;
  strategy_version: string | null;
};

export type AlertEntry = {
  timestamp: string;
  level: string;
  category: string;
  title: string;
  message: string;
  data?: Record<string, unknown> | null;
};

export type Strategy = {
  id: string;
  label: string;
};
