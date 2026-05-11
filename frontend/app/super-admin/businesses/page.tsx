"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { SuperAdminBusinessSummary } from "@/lib/types";
import { Card, ErrorMessage, LoadingState } from "@/components/ui";
import { AdminTable, PageHeader, SearchBar, StatusText, ViewLink } from "@/app/super-admin/_components";

export default function SuperAdminBusinessesPage() {
  const [businesses, setBusinesses] = useState<SuperAdminBusinessSummary[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBusinesses();
  }, []);

  async function loadBusinesses(query?: string) {
    setError(null);
    try {
      setBusinesses(await api.superAdminBusinesses({ search: query || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bizneslarni yuklab bo‘lmadi");
    } finally {
      setLoading(false);
    }
  }

  function onSearch(event: FormEvent) {
    event.preventDefault();
    loadBusinesses(search);
  }

  if (loading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Bizneslar" description="Platformadagi barcha bizneslarni qidiring va ko‘ring." />
      <ErrorMessage message={error} />
      <Card>
        <SearchBar value={search} onChange={setSearch} onSubmit={onSearch} placeholder="Nomi, telefon yoki public ID bo‘yicha qidirish" />
        <AdminTable
          headers={["Biznes ID", "Nomi", "Telefon", "Ownerlar", "Adminlar", "Mahsulotlar", "Buyurtmalar", "Mijozlar", "Operatorlar", "Yaratilgan", "Holati", "Amallar"]}
          rows={businesses.map((business) => [
            business.public_business_id,
            business.name,
            business.phone || "-",
            business.owners_count,
            business.admins_count,
            business.products_count,
            business.orders_count,
            business.customers_count,
            business.active_operators_count,
            formatDate(business.created_at),
            <StatusText key="status" active={business.is_active} />,
            <ViewLink key="view" href={`/super-admin/businesses/${business.id}`} />
          ])}
        />
      </Card>
    </div>
  );
}
