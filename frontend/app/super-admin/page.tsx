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
      .catch((err) => setError(err instanceof Error ? err.message : "Statistikani yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const cards = stats ? [
    ["Jami bizneslar", stats.total_businesses],
    ["Aktiv bizneslar", stats.active_businesses],
    ["Jami foydalanuvchilar", stats.total_users],
    ["Jami buyurtmalar", stats.total_orders],
    ["Jami mijozlar", stats.total_customers],
    ["Jami mahsulotlar", stats.total_products],
    ["Jami operatorlar", stats.total_operators],
    ["Bugungi buyurtmalar", stats.orders_today],
    ["Bugungi yangi foydalanuvchilar", stats.new_users_today],
    ["Bugungi yangi bizneslar", stats.new_businesses_today]
  ] : [];

  return (
    <div>
      <PageHeader title="Statistika" description="Platforma bo‘yicha umumiy ko‘rsatkichlar va bugungi faollik." />
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
