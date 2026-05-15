const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export async function apiFetch<T = unknown>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_id");
    throw new Error("Oturum süresi doldu. Lütfen tekrar giriş yapın.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Bir hata oluştu");
  }

  return res.json();
}

// ── Auth ──────────────────────────────────────────────
export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: async (email: string, password: string) => {
    const data = await apiFetch<{
      access_token: string;
      user_id: string;
      email: string;
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("user_id", data.user_id);
    return data;
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_id");
    window.location.href = "/login";
  },

  me: () => apiFetch("/api/auth/me"),
};

// ── Personality ───────────────────────────────────────
export const personalityApi = {
  getQuestions: () => apiFetch<{ questions: unknown[]; total: number }>("/api/personality/questions"),

  submit: (answers: Record<string, string>) =>
    apiFetch("/api/personality/submit", {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  getProfile: (user_id: string) => apiFetch(`/api/personality/${user_id}`),

  getHistory: () => apiFetch("/api/personality/history"),
};

// ── Budget ────────────────────────────────────────────
export const budgetApi = {
  create: (user_id: string, income_data: unknown, expense_data: unknown, savings_data: unknown) =>
    apiFetch("/api/budget/create", {
      method: "POST",
      body: JSON.stringify({ user_id, income_data, expense_data, savings_data }),
    }),

  get: (user_id: string) => apiFetch(`/api/budget/${user_id}`),

  getAnalysis: (user_id: string) => apiFetch(`/api/budget/${user_id}/analysis`),

  checkAffordability: (user_id: string, amount: number) =>
    apiFetch("/api/budget/affordability", {
      method: "POST",
      body: JSON.stringify({ user_id, amount }),
    }),

  addExpense: (user_id: string, category: string, amount: number, description?: string) =>
    apiFetch("/api/budget/expense", {
      method: "POST",
      body: JSON.stringify({ user_id, category, amount, description: description || null }),
    }),

  listExpenses: (user_id: string, limit = 10) =>
    apiFetch(`/api/budget/${user_id}/expenses?limit=${limit}`),

  deleteExpense: (expense_id: string) =>
    apiFetch(`/api/budget/expense/${expense_id}`, { method: "DELETE" }),
};

// ── Chat ──────────────────────────────────────────────
export const chatApi = {
  send: (message: string) =>
    apiFetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  getHistory: (limit = 20) => apiFetch(`/api/chat/history?limit=${limit}`),

  getThread: (userMsgId: string) => apiFetch(`/api/chat/thread/${userMsgId}`),

  deleteHistory: () => apiFetch("/api/chat/history", { method: "DELETE" }),
};

// ── Watchlist ─────────────────────────────────────
export const watchlistApi = {
  list: () => apiFetch("/api/watchlist/"),

  add: (product: { name: string; price: number; url?: string; image_url?: string; seller?: string }) =>
    apiFetch("/api/watchlist/", {
      method: "POST",
      body: JSON.stringify(product),
    }),

  remove: (id: string) =>
    apiFetch(`/api/watchlist/${id}`, { method: "DELETE" }),

  check: () =>
    apiFetch("/api/watchlist/check", { method: "POST" }),

  history: (id: string) =>
    apiFetch(`/api/watchlist/${id}/history`),

  updateThreshold: (id: string, threshold: number) =>
    apiFetch(`/api/watchlist/${id}/threshold?threshold_pct=${threshold}`, {
      method: "PATCH",
    }),

  notifications: (limit = 20) =>
    apiFetch(`/api/watchlist/notifications?limit=${limit}`),

  markRead: (id: string) =>
    apiFetch(`/api/watchlist/notifications/${id}/read`, { method: "PATCH" }),

  markAllRead: () =>
    apiFetch("/api/watchlist/notifications/read-all", { method: "PATCH" }),
};
