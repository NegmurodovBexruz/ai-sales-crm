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
      setError(err instanceof Error ? err.message : "Failed to load businesses");
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
      <PageHeader title="Businesses" description="Search and inspect all platform businesses." />
      <ErrorMessage message={error} />
      <Card>
        <SearchBar value={search} onChange={setSearch} onSubmit={onSearch} placeholder="Search name, phone, public ID" />
        <AdminTable
          headers={["Business ID", "Name", "Phone", "Owners", "Admins", "Products", "Orders", "Customers", "Operators", "Created", "Status", "Actions"]}
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
