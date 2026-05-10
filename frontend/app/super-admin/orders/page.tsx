"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatDate, formatMoney } from "@/lib/api";
import type { SuperAdminOrderSummary } from "@/lib/types";
import { Button, Card, ErrorMessage, Input, LoadingState } from "@/components/ui";
import { AdminTable, PageHeader } from "@/app/super-admin/_components";

export default function SuperAdminOrdersPage() {
  const [orders, setOrders] = useState<SuperAdminOrderSummary[]>([]);
  const [businessId, setBusinessId] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadOrders();
  }, []);

  async function loadOrders() {
    setError(null);
    try {
      setOrders(await api.superAdminOrders({
        business_id: businessId ? Number(businessId) : undefined,
        status: status || undefined
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load orders");
    } finally {
      setLoading(false);
    }
  }

  function onFilter(event: FormEvent) {
    event.preventDefault();
    loadOrders();
  }

  if (loading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Orders" description="All orders across all businesses." />
      <ErrorMessage message={error} />
      <Card>
        <form onSubmit={onFilter} className="mb-4 grid gap-2 md:grid-cols-[1fr_1fr_auto]">
          <Input value={businessId} onChange={(event) => setBusinessId(event.target.value)} placeholder="Business ID" />
          <Input value={status} onChange={(event) => setStatus(event.target.value)} placeholder="Status" />
          <Button>Filter</Button>
        </form>
        <AdminTable
          headers={["Order ID", "Business", "Customer", "Phone", "Product", "Quantity", "Total price", "Status", "Created"]}
          rows={orders.map((order) => [
            `#${order.id}`,
            `${order.business_name} (#${order.business_id})`,
            order.customer_name,
            order.phone,
            order.product || "-",
            order.quantity,
            formatMoney(order.total_price),
            order.status,
            formatDate(order.created_at)
          ])}
        />
      </Card>
    </div>
  );
}
