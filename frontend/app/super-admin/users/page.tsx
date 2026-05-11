"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { SuperAdminUserSummary } from "@/lib/types";
import { Button, Card, ErrorMessage, Input, LoadingState } from "@/components/ui";
import { AdminTable, PageHeader, StatusText, ViewLink } from "@/app/super-admin/_components";

export default function SuperAdminUsersPage() {
  const [users, setUsers] = useState<SuperAdminUserSummary[]>([]);
  const [search, setSearch] = useState("");
  const [globalRole, setGlobalRole] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    setError(null);
    try {
      setUsers(await api.superAdminUsers({ search: search || undefined, global_role: globalRole || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Foydalanuvchilarni yuklab bo‘lmadi");
    } finally {
      setLoading(false);
    }
  }

  function onSearch(event: FormEvent) {
    event.preventDefault();
    loadUsers();
  }

  if (loading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Foydalanuvchilar" description="Global kirish huquqlari va rollarni boshqaring." />
      <ErrorMessage message={error} />
      <Card>
        <form onSubmit={onSearch} className="mb-4 grid gap-2 md:grid-cols-[1fr_180px_auto]">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Email yoki ism bo‘yicha qidirish" />
          <select value={globalRole} onChange={(event) => setGlobalRole(event.target.value)} className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm">
            <option value="">Barcha rollar</option>
            <option value="user">Foydalanuvchi</option>
            <option value="super_admin">Super admin</option>
          </select>
          <Button>Qidirish</Button>
        </form>
        <AdminTable
          headers={["ID", "Email", "To‘liq ism", "Global rol", "Bizneslar", "Yaratilgan", "Holati", "Amallar"]}
          rows={users.map((user) => [
            user.id,
            user.email,
            user.full_name || "-",
            user.global_role,
            user.businesses.length,
            formatDate(user.created_at),
            <StatusText key="status" active={user.is_active} />,
            <ViewLink key="view" href={`/super-admin/users/${user.id}`} />
          ])}
        />
      </Card>
    </div>
  );
}
