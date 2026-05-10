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
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load members"))
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
      setError(err instanceof Error ? err.message : "Member action failed");
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Members</h1>
        <p className="text-sm text-slate-500">Approve admin requests and manage active business admins.</p>
      </div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
      {loading ? <LoadingState /> : !business || !members ? <EmptyState label="No business found." /> : (
        <>
          <Card>
            <div className="text-sm text-slate-500">Public business ID</div>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <code className="rounded-md bg-slate-100 px-3 py-2 text-lg font-semibold text-slate-950">{business.public_business_id}</code>
              <SecondaryButton onClick={() => navigator.clipboard.writeText(business.public_business_id)}>Copy</SecondaryButton>
            </div>
          </Card>
          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-950">Pending requests</h2>
            {members.pending_requests.length === 0 ? <EmptyState label="No pending admin requests." /> : (
              <div className="space-y-3">
                {members.pending_requests.map((member) => (
                  <div key={member.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3">
                    <div>
                      <div className="font-medium text-slate-950">{member.user?.full_name || member.user?.email || `User #${member.user_id}`}</div>
                      <div className="text-sm text-slate-500">{member.user?.email} · {formatDate(member.created_at)}</div>
                    </div>
                    <div className="flex gap-2">
                      <SecondaryButton onClick={() => run(() => api.approveMember(member.id), "Member approved.")}>Approve</SecondaryButton>
                      <DangerButton onClick={() => run(() => api.rejectMember(member.id), "Member rejected.")}>Reject</DangerButton>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-950">Active members</h2>
            <div className="space-y-3">
              {members.members.map((member) => (
                <div key={member.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3">
                  <div>
                    <div className="font-medium text-slate-950">{member.user?.full_name || member.user?.email || `User #${member.user_id}`}</div>
                    <div className="text-sm text-slate-500">{member.user?.email} · joined {formatDate(member.created_at)}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={member.role === "owner" ? "green" : "slate"}>{member.role}</Badge>
                    {member.role === "admin" && <DangerButton onClick={() => run(() => api.removeMember(member.id), "Member removed.")}>Remove</DangerButton>}
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
