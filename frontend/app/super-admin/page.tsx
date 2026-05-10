"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SuperAdminStats } from "@/lib/types";
import { Card, ErrorMessage, LoadingState } from "@/components/ui";
import { PageHeader } from "@/app/super-admin/_components";

export default function SuperAdminOverviewPage() {
  const [stats, setStats] = useState<SuperAdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.superAdminStats()
      .then(setStats)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const cards = stats ? [
    ["Total businesses", stats.total_businesses],
    ["Active businesses", stats.active_businesses],
    ["Total users", stats.total_users],
    ["Total orders", stats.total_orders],
    ["Total customers", stats.total_customers],
    ["Total products", stats.total_products],
    ["Total operators", stats.total_operators],
    ["Orders today", stats.orders_today],
    ["New users today", stats.new_users_today],
    ["New businesses today", stats.new_businesses_today]
  ] : [];

  return (
    <div>
      <PageHeader title="Overview" description="Platform-wide totals and today's activity." />
      <ErrorMessage message={error} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {cards.map(([label, value]) => (
          <Card key={label}>
            <div className="text-sm text-slate-500">{label}</div>
            <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}
