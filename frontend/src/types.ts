export interface User {
  id: number;
  email: string;
  name: string;
  avatar_url?: string | null;
}

export interface Profile {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

export interface Holding {
  id: number;
  profile_id: number;
  asset_class: string;
  name: string;
  identifier: string;
  latest_price: number | null;
  current_value: number | null;
  meta: Record<string, unknown>;
}

export interface Transaction {
  id: number;
  holding_id: number;
  txn_date: string;
  txn_type: string;
  quantity: number;
  price: number;
  amount: number;
  charges: number;
  dividend: number;
  notes: string;
  source: string;
}

export interface HoldingMetric {
  holding_id: number;
  name: string;
  identifier: string;
  asset_class: string;
  units: number;
  latest_price: number | null;
  invested: number;
  current_value: number;
  dividends: number;
  gain: number;
  absolute_return_pct: number | null;
  xirr_pct: number | null;
  txn_count: number;
  meta: Record<string, unknown>;
}

export interface Aggregate {
  invested: number;
  current_value: number;
  gain: number;
  absolute_return_pct: number | null;
  xirr_pct?: number | null;
  count: number;
}

export interface Analytics {
  as_of: string;
  portfolio: Aggregate;
  by_asset_class: Record<string, Aggregate>;
  holdings: HoldingMetric[];
}

export interface Insight {
  level: "positive" | "info" | "warning" | "critical";
  title: string;
  detail: string;
  holding?: string | null;
}

export interface ImportSummary {
  filename: string;
  totals: {
    parsed: number;
    new_transactions: number;
    duplicates: number;
    holdings_created: number;
  };
  by_asset_class: Record<
    string,
    { parsed: number; new_transactions: number; duplicates: number; holdings_created: number }
  >;
  errors: string[];
}

export const ASSET_CLASSES = [
  "MF",
  "Stocks",
  "FD",
  "Bonds",
  "NPS",
  "PF",
  "Crypto",
  "Policies",
  "Gratuity",
];
