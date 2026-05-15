export interface User {
  id: string;
  email: string;
  full_name?: string;
}

export interface Personality {
  id: string;
  user_id: string;
  spending_type: "dengeli" | "savruk" | "tutumlu";
  risk_score: number;
  impulsive_score: number;
  saving_score: number;
  research_score: number;
  strengths: string[];
  weaknesses: string[];
  recommendations: string;
  created_at: string;
}

export interface SavingsTip {
  key: string;
  params?: Record<string, number | string>;
}

export type ExpenseCategory =
  | "groceries"
  | "transport"
  | "health"
  | "education"
  | "entertainment"
  | "clothing"
  | "bills"
  | "other";

export interface Expense {
  id: string;
  user_id: string;
  category: ExpenseCategory | string;
  amount: number;
  description?: string | null;
  created_at: string;
}

export interface Budget {
  success: boolean;
  status: "healthy" | "warning" | "critical";
  financial_metrics: {
    total_income: number;
    fixed_expenses: number;
    available_budget: number;
    savings_goal: number;
    spendable_after_savings: number;
    /** Bu ay (UTC) yapılan harcamaların toplamı */
    current_month_spending?: number;
    /** spendable_after_savings - current_month_spending */
    remaining_spendable?: number;
    expense_ratio: number;
  };
  // Backend yapılandırılmış dönüyor; eski sürüm için string'i de kabul ediyoruz.
  savings_tips: Array<string | SavingsTip>;
}

export interface Product {
  name: string;
  price: number;
  seller: string;
  rating: number;
  description: string;
  url: string;
  image_url: string;
  recommendation_reason: string;
  serpapi_product_id?: string;
  review_analysis?: {
    review_count: number;
    reviews: Review[];
    analysis: Record<string, unknown>;
  };
}

export interface Review {
  rating: number;
  comment: string;
  user_profile: string;
  sentiment?: string;
}

export interface Recommendation {
  spending_type: string;
  budget_status: string;
  top_pick: {
    product_name: string;
    reason: string;
    value_score: number;
  } | null;
  summary: string;
  financial_advice: string;
  top_products: Product[];
}

export interface ChatResponse {
  message: string;
  is_product_request: boolean;
  reply?: string;
  steps_completed: string[];
  personality: Personality;
  budget_status: string;
  products: Product[];
  recommendation: Recommendation;
  error: string | null;
  affordability_message: string | null;
  user_msg_id?: string | null;
}

export interface ChatHistory {
  id: string;
  user_id: string;
  message: string;
  role: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}
