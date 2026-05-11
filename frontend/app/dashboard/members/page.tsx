"use client";

import { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { Business, MemberList } from "@/lib/types";
import { Badge, Card, DangerButton, EmptyState, ErrorMessage, LoadingState, SecondaryButton } from "@/components/ui";

export default function MembersPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [members, setMembers] = useState<MemberList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadData() {
    const businessMe = await api.businessMe();
    setBusiness(businessMe.business);
    if (businessMe.business) {
      setMembers(await api.members(businessMe.business.id));
    }
  }

  useEffect(() => {
    loadData()
      .catch((err) => setError(err instanceof Error ? err.message : "A’zolarni yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, []);

  async function run(action: () => Promise<unknown>, success: string) {
    setError(null);
    setMessage(null);
    try {
      await action();
      await loadData();
      setMessage(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "A’zo amali bajarilmadi");
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">A’zolar</h1>
        <p className="text-sm text-slate-500">Admin so‘rovlarini tasdiqlang va aktiv adminlarni boshqaring.</p>
      </div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
      {loading ? <LoadingState /> : !business || !members ? <EmptyState label="Biznes topilmadi." /> : (
        <>
          <Card>
            <div className="text-sm text-slate-500">Admin join code</div>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <code className="rounded-md bg-slate-100 px-3 py-2 text-lg font-semibold text-slate-950">{business.admin_join_code || "-"}</code>
              <SecondaryButton disabled={!business.admin_join_code} onClick={() => business.admin_join_code && navigator.clipboard.writeText(business.admin_join_code)}>Nusxalash</SecondaryButton>
            </div>
          </Card>
          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-950">Kutilayotgan so‘rovlar</h2>
            {members.pending_requests.length === 0 ? <EmptyState label="Kutilayotgan admin so‘rovlari yo‘q." /> : (
              <div className="space-y-3">
                {members.pending_requests.map((member) => (
                  <div key={member.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3">
                    <div>
                      <div className="font-medium text-slate-950">{member.user?.full_name || member.user?.email || `User #${member.user_id}`}</div>
                      <div className="text-sm text-slate-500">{member.user?.email} · {formatDate(member.created_at)}</div>
                    </div>
                    <div className="flex gap-2">
                      <SecondaryButton onClick={() => run(() => api.approveMember(member.id), "A’zo tasdiqlandi.")}>Tasdiqlash</SecondaryButton>
                      <DangerButton onClick={() => run(() => api.rejectMember(member.id), "A’zo rad etildi.")}>Rad etish</DangerButton>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-950">Aktiv a’zolar</h2>
            <div className="space-y-3">
              {members.members.map((member) => (
                <div key={member.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3">
                  <div>
                    <div className="font-medium text-slate-950">{member.user?.full_name || member.user?.email || `User #${member.user_id}`}</div>
                    <div className="text-sm text-slate-500">{member.user?.email} · joined {formatDate(member.created_at)}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={member.role === "owner" ? "green" : "slate"}>{member.role}</Badge>
                    {member.role === "admin" && <DangerButton onClick={() => run(() => api.removeMember(member.id), "A’zo olib tashlandi.")}>Olib tashlash</DangerButton>}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </section>
  );
}
