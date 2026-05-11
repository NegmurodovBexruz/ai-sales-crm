"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, formatDate } from "@/lib/api";
import type { SuperAdminUserDetail } from "@/lib/types";
import { Button, Card, ErrorMessage, Input, Label, LoadingState } from "@/components/ui";
import { AdminTable, PageHeader, StatusText, ViewLink } from "@/app/super-admin/_components";

export default function SuperAdminUserDetailPage() {
  const params = useParams<{ id: string }>();
  const userId = Number(params.id);
  const [user, setUser] = useState<SuperAdminUserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUser();
  }, [userId]);

  async function loadUser() {
    setError(null);
    try {
      setUser(await api.superAdminUser(userId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Foydalanuvchini yuklab bo‘lmadi");
    } finally {
      setLoading(false);
    }
  }

  async function saveUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) return;
    const form = new FormData(event.currentTarget);
    const globalRole = String(form.get("global_role") || "user") as "user" | "super_admin";
    if (globalRole === "super_admin" && user.global_role !== "super_admin") {
      const confirmed = window.confirm("Bu foydalanuvchiga global Super admin huquqini beradi. Davom etasizmi?");
      if (!confirmed) return;
    }
    setSaving(true);
    setError(null);
    try {
      setUser(await api.updateSuperAdminUser(userId, {
        full_name: String(form.get("full_name") || "") || null,
        global_role: globalRole,
        is_active: form.get("is_active") === "true"
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Foydalanuvchini yangilab bo‘lmadi");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState />;
  if (!user) return <ErrorMessage message={error || "Foydalanuvchi topilmadi"} />;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <PageHeader title={user.email} description="Foydalanuvchi ma’lumotlari va global kirish huquqi." />
        <Link href="/super-admin/users" className="text-sm font-medium text-slate-600 hover:text-slate-950">Ortga</Link>
      </div>
      <ErrorMessage message={error} />

      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-slate-950">Foydalanuvchi ma’lumotlari</h2>
          <form onSubmit={saveUser} className="space-y-3">
            <div><Label>Email</Label><Input value={user.email} readOnly /></div>
            <div><Label>To‘liq ism</Label><Input name="full_name" defaultValue={user.full_name || ""} /></div>
            <div>
              <Label>Global rol</Label>
              <select name="global_role" defaultValue={user.global_role} className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm">
                <option value="user">Foydalanuvchi</option>
                <option value="super_admin">Super admin</option>
              </select>
            </div>
            <div>
              <Label>Holati</Label>
              <select name="is_active" defaultValue={String(user.is_active)} className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm">
                <option value="true">Aktiv</option>
                <option value="false">Noaktiv</option>
              </select>
            </div>
            <Button disabled={saving}>{saving ? "Saqlanmoqda..." : "Foydalanuvchini saqlash"}</Button>
          </form>
          <div className="mt-4 grid gap-2 text-sm">
            <div>Rol: {user.role}</div>
            <div>Holati: <StatusText active={user.is_active} /></div>
            <div>Yaratilgan: {formatDate(user.created_at)}</div>
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 text-lg font-semibold text-slate-950">A’zoliklar</h2>
          <AdminTable headers={["Biznes", "Rol", "Holat", "Yaratilgan", "Amal"]} rows={user.business_memberships.map((membership) => [
            `${membership.business_name} (#${membership.business_id})`,
            membership.role,
            membership.status,
            formatDate(membership.created_at),
            <ViewLink key="view" href={`/super-admin/businesses/${membership.business_id}`} />
          ])} />
        </Card>
      </div>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Egaligidagi bizneslar</h2>
        <AdminTable headers={["Biznes ID", "Nomi", "Ownerlar", "Adminlar", "Buyurtmalar", "Mijozlar", "Holati", "Amal"]} rows={user.owned_businesses.map((business) => [
          business.public_business_id,
          business.name,
          business.owners_count,
          business.admins_count,
          business.orders_count,
          business.customers_count,
          <StatusText key="status" active={business.is_active} />,
          <ViewLink key="view" href={`/super-admin/businesses/${business.id}`} />
        ])} />
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-slate-950">Admin a’zoliklari</h2>
        <AdminTable headers={["Biznes", "Holat", "Yaratilgan", "Amal"]} rows={user.admin_memberships.map((membership) => [
          `${membership.business_name} (#${membership.business_id})`,
          membership.status,
          formatDate(membership.created_at),
          <ViewLink key="view" href={`/super-admin/businesses/${membership.business_id}`} />
        ])} />
      </Card>
    </div>
  );
}
