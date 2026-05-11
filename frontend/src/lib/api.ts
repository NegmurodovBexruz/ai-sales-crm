import { clearOperatorToken, clearToken, getOperatorToken, getToken } from "@/lib/auth";
import type {
  Business,
  BusinessMe,
  BusinessMember,
  Conversation,
  Customer,
  MemberList,
  Order,
  OperatorInfo,
  OperatorMe,
  OperatorProduct,
  Product,
  SuperAdminBusinessDetail,
  SuperAdminBusinessSummary,
  SuperAdminMemberSummary,
  SuperAdminOperatorSummary,
  SuperAdminOrderSummary,
  SuperAdminStats,
  SuperAdminUserDetail,
  SuperAdminUserSummary,
  TelegramStatus,
  TelegramOperator,
  User
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type RequestOptions = RequestInit & { skipAuth?: boolean };
type OperatorRequestOptions = RequestInit & { skipAuth?: boolean };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!options.skipAuth && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Sessiya tugadi. Iltimos, qayta kiring.");
  }

  if (!response.ok) {
    let message: unknown = "So‘rov bajarilmadi";
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(", ") : String(message));
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function operatorRequest<T>(path: string, options: OperatorRequestOptions = {}): Promise<T> {
  const token = getOperatorToken();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!options.skipAuth && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    clearOperatorToken();
    if (typeof window !== "undefined") window.location.href = "/operator-login";
    throw new Error("Operator sessiyasi tugadi. Iltimos, qayta kiring.");
  }

  if (!response.ok) {
    let message: unknown = "So‘rov bajarilmadi";
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(", ") : String(message));
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (payload: { email: string; password: string; full_name: string }) =>
    request<User>("/api/auth/register", {
      method: "POST",
      skipAuth: true,
      body: JSON.stringify(payload)
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login-json", {
      method: "POST",
      skipAuth: true,
      body: JSON.stringify({ email, password })
    }),
  operatorLogin: (operatorCode: string, telegramChatId: string) =>
    operatorRequest<{ access_token: string; token_type: string; operator: OperatorInfo }>("/api/operator-auth/login", {
      method: "POST",
      skipAuth: true,
      body: JSON.stringify({ operator_code: operatorCode, telegram_chat_id: telegramChatId })
    }),
  operatorMe: () => operatorRequest<OperatorMe>("/api/operator-auth/me"),
  operatorProducts: () => operatorRequest<OperatorProduct[]>("/api/operator/products"),
  me: () => request<User>("/api/auth/me"),
  businessMe: () => request<BusinessMe>("/api/businesses/me"),
  updateBusiness: (businessId: number, payload: Partial<Business>) =>
    request<Business>(`/api/businesses/${businessId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  uploadKnowledgeDocx: (businessId: number, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<Business>(`/api/businesses/${businessId}/knowledge-docx`, {
      method: "POST",
      body: formData
    });
  },
  telegramStatus: (businessId: number) =>
    request<TelegramStatus>(`/api/businesses/${businessId}/telegram/status`),
  saveTelegramToken: (businessId: number, telegramBotToken: string) =>
    request<TelegramStatus>(`/api/businesses/${businessId}/telegram-token`, {
      method: "PATCH",
      body: JSON.stringify({ telegram_bot_token: telegramBotToken })
    }),
  setTelegramWebhook: (businessId: number) =>
    request<TelegramStatus>(`/api/businesses/${businessId}/telegram/set-webhook`, {
      method: "POST"
    }),
  products: () => request<Product[]>("/api/products"),
  createProduct: (payload: Omit<Product, "id" | "availability_status" | "created_at" | "updated_at">) =>
    request<Product>("/api/products", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateProduct: (productId: number, payload: Partial<Product>) =>
    request<Product>(`/api/products/${productId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  deleteProduct: (productId: number) =>
    request<void>(`/api/products/${productId}`, {
      method: "DELETE"
    }),
  increaseStock: (productId: number, amount = 1) =>
    request<Product>(`/api/products/${productId}/stock/increase`, {
      method: "PATCH",
      body: JSON.stringify({ amount })
    }),
  decreaseStock: (productId: number, amount = 1) =>
    request<Product>(`/api/products/${productId}/stock/decrease`, {
      method: "PATCH",
      body: JSON.stringify({ amount })
    }),
  orders: () => request<Order[]>("/api/orders"),
  markOrderDone: (orderId: number) =>
    request<{ order: Order; product_stock_count: number; message: string }>(`/api/orders/${orderId}/done`, {
      method: "PATCH"
    }),
  updateOrderStatus: (orderId: number, status: string) =>
    request<Order>(`/api/orders/${orderId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    }),
  customers: () => request<Customer[]>("/api/customers"),
  conversations: (customerId: number) =>
    request<Conversation[]>(`/api/conversations/customer/${customerId}`),
  createBusiness: (payload: Pick<Business, "name"> & Partial<Business>) =>
    request<Business>("/api/businesses", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  joinBusiness: (adminJoinCode: string) =>
    request<{ message: string; membership: BusinessMember }>("/api/business-members/join-request", {
      method: "POST",
      body: JSON.stringify({ admin_join_code: adminJoinCode })
    }),
  joinBusinessWithAdminCode: (adminJoinCode: string) =>
    request<{ message: string; membership: BusinessMember }>("/api/business-members/join-request", {
      method: "POST",
      body: JSON.stringify({ admin_join_code: adminJoinCode })
    }),
  members: (businessId?: number) =>
    request<MemberList>(`/api/business-members${businessId ? `?business_id=${businessId}` : ""}`),
  approveMember: (memberId: number) =>
    request<{ message: string }>(`/api/business-members/${memberId}/approve`, { method: "PATCH" }),
  rejectMember: (memberId: number) =>
    request<{ message: string }>(`/api/business-members/${memberId}/reject`, { method: "PATCH" }),
  removeMember: (memberId: number) =>
    request<{ message: string }>(`/api/business-members/${memberId}/remove`, { method: "PATCH" }),
  operators: () => request<TelegramOperator[]>("/api/operators"),
  createOperator: (payload: Omit<TelegramOperator, "id" | "business_id" | "created_at" | "updated_at">) =>
    request<TelegramOperator>("/api/operators", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateOperator: (operatorId: number, payload: Partial<TelegramOperator>) =>
    request<TelegramOperator>(`/api/operators/${operatorId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  deleteOperator: (operatorId: number) =>
    request<TelegramOperator>(`/api/operators/${operatorId}`, {
      method: "DELETE"
    }),
  superAdminStats: () => request<SuperAdminStats>("/api/super-admin/stats"),
  superAdminBusinesses: (params?: { search?: string; limit?: number; offset?: number }) =>
    request<SuperAdminBusinessSummary[]>(`/api/super-admin/businesses${queryString(params)}`),
  superAdminBusiness: (businessId: number) =>
    request<SuperAdminBusinessDetail>(`/api/super-admin/businesses/${businessId}`),
  updateSuperAdminBusiness: (businessId: number, payload: Partial<Business>) =>
    request<SuperAdminBusinessSummary>(`/api/super-admin/businesses/${businessId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  superAdminUsers: (params?: { search?: string; global_role?: string; limit?: number; offset?: number }) =>
    request<SuperAdminUserSummary[]>(`/api/super-admin/users${queryString(params)}`),
  superAdminUser: (userId: number) => request<SuperAdminUserDetail>(`/api/super-admin/users/${userId}`),
  updateSuperAdminUser: (userId: number, payload: Partial<User>) =>
    request<SuperAdminUserDetail>(`/api/super-admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  superAdminMembers: (params?: { business_id?: number; user_id?: number; role?: string; status?: string }) =>
    request<SuperAdminMemberSummary[]>(`/api/super-admin/business-members${queryString(params)}`),
  superAdminOperators: () => request<SuperAdminOperatorSummary[]>("/api/super-admin/operators"),
  superAdminOrders: (params?: { business_id?: number; status?: string; limit?: number; offset?: number }) =>
    request<SuperAdminOrderSummary[]>(`/api/super-admin/orders${queryString(params)}`)
};

function queryString(params?: Record<string, string | number | undefined>) {
  if (!params) return "";
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function formatMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 2 }).format(Number(value));
}

export function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("uz-UZ", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

