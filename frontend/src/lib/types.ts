export type User = {
  id: number;
  email: string;
  full_name?: string | null;
  role?: string;
  global_role: "user" | "super_admin";
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type Business = {
  id: number;
  owner_id: number;
  public_business_id: string;
  admin_join_code?: string | null;
  operator_code?: string | null;
  name: string;
  description?: string | null;
  phone?: string | null;
  delivery_policy?: string | null;
  return_policy?: string | null;
  working_hours?: string | null;
  ai_tone?: string | null;
  business_knowledge_text?: string | null;
  knowledge_file_name?: string | null;
  knowledge_uploaded_at?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type BusinessMember = {
  id: number;
  business_id: number;
  user_id: number;
  role: "owner" | "admin";
  status: "pending" | "active" | "rejected" | "removed";
  invited_by_user_id?: number | null;
  approved_by_user_id?: number | null;
  created_at: string;
  updated_at: string;
  user?: {
    id: number;
    email: string;
    full_name?: string | null;
  } | null;
};

export type BusinessMe = {
  business: Business | null;
  membership: BusinessMember | null;
  pending_requests: BusinessMember[];
};

export type MemberList = {
  business_public_id: string;
  members: BusinessMember[];
  pending_requests: BusinessMember[];
};

export type Product = {
  id: number;
  business_id: number;
  name: string;
  description?: string | null;
  category?: string | null;
  price: string | number;
  discount_price?: string | number | null;
  stock_count: number;
  image_url?: string | null;
  tags?: string | null;
  availability_status: string;
  created_at: string;
  updated_at: string;
};

export type OperatorProduct = Omit<Product, "business_id" | "created_at" | "updated_at">;

export type OperatorInfo = {
  id: number;
  name: string;
  telegram_chat_id: string;
  business_id: number;
  business_name: string;
};

export type OperatorMe = {
  operator: OperatorInfo;
  business: {
    id: number;
    name: string;
  };
};

export type Order = {
  id: number;
  business_id: number;
  customer_id: number;
  product_id?: number | null;
  quantity?: number | null;
  total_price: string | number;
  customer_name: string;
  phone: string;
  address: string;
  comment?: string | null;
  status: string;
  items?: OrderItem[];
  created_at: string;
  updated_at: string;
};

export type OrderItem = {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: string | number;
  discount_price?: string | number | null;
  final_unit_price: string | number;
  total_price: string | number;
};

export type Customer = {
  id: number;
  business_id: number;
  telegram_user_id: string;
  full_name?: string | null;
  username?: string | null;
  phone?: string | null;
  language: "uz_latin" | "uz_cyrillic" | "ru";
  created_at: string;
  updated_at: string;
};

export type Conversation = {
  id: number;
  business_id: number;
  customer_id: number;
  message_text: string;
  sender_type: "customer" | "ai" | "admin" | "system";
  intent?: string | null;
  created_at: string;
};

export type TelegramOperator = {
  id: number;
  business_id: number;
  name: string;
  telegram_chat_id: string;
  username?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SuperAdminStats = {
  total_businesses: number;
  active_businesses: number;
  total_users: number;
  total_orders: number;
  total_customers: number;
  total_products: number;
  total_operators: number;
  new_businesses_today: number;
  new_users_today: number;
  orders_today: number;
};

export type SuperAdminUserMembership = {
  id: number;
  business_id: number;
  business_name: string;
  role: string;
  status: string;
  created_at: string;
};

export type SuperAdminBusinessSummary = {
  id: number;
  public_business_id: string;
  name: string;
  phone?: string | null;
  description?: string | null;
  delivery_policy?: string | null;
  return_policy?: string | null;
  working_hours?: string | null;
  ai_tone?: string | null;
  created_at: string;
  owners_count: number;
  admins_count: number;
  products_count: number;
  orders_count: number;
  customers_count: number;
  active_operators_count: number;
  is_active: boolean;
  status: string;
};

export type SuperAdminUserSummary = {
  id: number;
  email: string;
  full_name?: string | null;
  global_role: "user" | "super_admin";
  is_active: boolean;
  created_at: string;
  businesses: SuperAdminUserMembership[];
};

export type SuperAdminMemberSummary = {
  id: number;
  business_id: number;
  business_name: string;
  user_id: number;
  user_email: string;
  role: string;
  status: string;
  created_at: string;
};

export type SuperAdminOperatorSummary = {
  id: number;
  business_id: number;
  business_name: string;
  name: string;
  telegram_chat_id: string;
  username?: string | null;
  is_active: boolean;
  created_at: string;
};

export type SuperAdminOrderSummary = {
  id: number;
  business_id: number;
  business_name: string;
  customer_name: string;
  phone: string;
  product?: string | null;
  quantity: number;
  total_price: string | number;
  status: string;
  created_at: string;
};

export type SuperAdminCustomerSummary = {
  id: number;
  business_id: number;
  telegram_user_id: string;
  full_name?: string | null;
  username?: string | null;
  phone?: string | null;
  language: string;
  created_at: string;
};

export type SuperAdminProductSummary = {
  id: number;
  business_id: number;
  name: string;
  category?: string | null;
  price: string | number;
  discount_price?: string | number | null;
  stock_count: number;
  availability_status: string;
  created_at: string;
};

export type SuperAdminBusinessDetail = {
  business: SuperAdminBusinessSummary;
  members: SuperAdminMemberSummary[];
  products: SuperAdminProductSummary[];
  operators: SuperAdminOperatorSummary[];
  recent_orders: SuperAdminOrderSummary[];
  recent_customers: SuperAdminCustomerSummary[];
  business_knowledge: {
    knowledge_file_name?: string | null;
    knowledge_uploaded_at?: string | null;
    business_knowledge_text_preview?: string | null;
  };
};

export type SuperAdminUserDetail = {
  id: number;
  email: string;
  full_name?: string | null;
  role: string;
  global_role: "user" | "super_admin";
  is_active: boolean;
  created_at: string;
  updated_at: string;
  business_memberships: SuperAdminUserMembership[];
  owned_businesses: SuperAdminBusinessSummary[];
  admin_memberships: SuperAdminUserMembership[];
};
