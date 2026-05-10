"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, formatDate, formatMoney } from "@/lib/api";
import type { SuperAdminBusinessDetail } from "@/lib/types";
import { Button, Card, ErrorMessage, Input, Label, LoadingState, Textarea } from "@/components/ui";
import { AdminTable, PageHeader, StatusText } from "@/app/super-admin/_components";

export default function SuperAdminBusinessDetailPage() {
  const params = useParams<{ id: string }>();
  const businessId = Number(params.id);
  const [detail, setDetail] = useState<SuperAdminBusinessDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDetail();
  }, [businessId]);

  async function loadDetail() {
    setError(null);
    try {
      setDetail(await api.superAdminBusiness(businessId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load business");
    } finally {
      setLoading(false);
    }
  }

  async function saveBusiness(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(null);
    try {
      await api.updateSuperAdminBusiness(businessId, {
        name: String(form.get("name") || ""),
        phone: String(form.get("phone") || "") || null,
        description: String(form.get("description") || "") || null,
        delivery_policy: String(form.get("delivery_policy") || "") || null,
        return_policy: String(form.get("return_policy") || "") || null,
        working_hours: String(form.get("working_hours") || "") || null,
        ai_tone: String(form.get("ai_tone") || "") || null,
        is_active: form.get("is_active") === "true"
      });
      await loadDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update business");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState />;
  if (!detail) return <ErrorMessage message={error || "Business not found"} />;

  const business = detail.business;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <PageHeader title={business.name} description={`Business ${business.public_business_id}`} />
        <Link href="/super-admin/businesses" className="text-sm font-medium text-slate-600 hover:text-slate-950">Back</Link>
      </div>
      <ErrorMessage message={error} />

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-slate-950">Business info</h2>
          <form onSubmit={saveBusiness} className="space-y-3">
            <div><Label>Name</Label><Input name="name" defaultValue={business.name} required /></div>
            <div><Label>Phone</Label><Input name="phone" defaultValue={business.phone || ""} /></div>
            <div><Label>Description</Label><Textarea name="description" defaultValue={business.description || ""} /></div>
            <div><Label>Delivery policy</Label><Textarea name="delivery_policy" defaultValue={business.delivery_policy || ""} /></div>
            <div><Label>Return policy</Label><Textarea name="return_policy" defaultValue={business.return_policy || ""} /></div>
            <div><Label>Working hours</Label><Input name="working_hours" defaultValue={business.working_hours || ""} /></div>
            <div><Label>AI tone</Label><Input name="ai_tone" defaultValue={business.ai_tone || ""} /></div>
            <div>
              <Label>Status</Label>
              <select name="is_active" defaultValue={String(business.is_active)} className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm">
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </div>
            <Button disabled={saving}>{saving ? "Saving..." : "Save business"}</Button>
          </form>
        </Card>

        <Card>
          <h2 className="mb-4 text-lg font-semibold text-slate-950">Knowledge file info</h2>
          <div className="grid gap-3 text-sm">
            <Meta label="Status" value={<StatusText active={business.is_active} />} />
            <Meta label="Created" value={formatDate(business.created_at)} />
            <Meta label="Knowledge file" value={detail.business_knowledge.knowledge_file_name || "-"} />
            <Meta label="Knowledge uploaded" value={formatDate(detail.business_knowledge.knowledge_uploaded_at)} />
            <div>
              <div className="text-xs font-medium uppercase text-slate-500">Knowledge preview</div>
              <p className="mt-1 max-h-64 overflow-auto rounded-md bg-slate-50 p-3 text-slate-700">
                {detail.business_knowledge.business_knowledge_text_preview || "-"}
              </p>
            </div>
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Members</h2>
        <AdminTable headers={["Business", "User email", "Role", "Status", "Created"]} rows={detail.members.map((member) => [
          `${member.business_name} (#${member.business_id})`,
          member.user_email,
          member.role,
          member.status,
          formatDate(member.created_at)
        ])} />
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Products</h2>
        <AdminTable headers={["ID", "Name", "Category", "Price", "Stock", "Status", "Created"]} rows={detail.products.map((product) => [
          product.id,
          product.name,
          product.category || "-",
          formatMoney(product.discount_price || product.price),
          product.stock_count,
          product.availability_status,
          formatDate(product.created_at)
        ])} />
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Operators</h2>
        <AdminTable headers={["Name", "Telegram chat ID", "Username", "Status", "Created"]} rows={detail.operators.map((operator) => [
          operator.name,
          operator.telegram_chat_id,
          operator.username || "-",
          <StatusText key="status" active={operator.is_active} />,
          formatDate(operator.created_at)
        ])} />
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Recent orders</h2>
        <AdminTable headers={["Order", "Customer", "Phone", "Product", "Qty", "Total", "Status", "Created"]} rows={detail.recent_orders.map((order) => [
          `#${order.id}`,
          order.customer_name,
          order.phone,
          order.product || "-",
          order.quantity,
          formatMoney(order.total_price),
          order.status,
          formatDate(order.created_at)
        ])} />
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Recent customers</h2>
        <AdminTable headers={["ID", "Name", "Username", "Phone", "Language", "Created"]} rows={detail.recent_customers.map((customer) => [
          customer.id,
          customer.full_name || "-",
          customer.username || "-",
          customer.phone || "-",
          customer.language,
          formatDate(customer.created_at)
        ])} />
      </Card>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-800">{value}</div>
    </div>
  );
}
