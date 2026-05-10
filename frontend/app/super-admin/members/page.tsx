"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { SuperAdminMemberSummary } from "@/lib/types";
import { Button, Card, ErrorMessage, Input, LoadingState } from "@/components/ui";
import { AdminTable, PageHeader } from "@/app/super-admin/_components";

export default function SuperAdminMembersPage() {
  const [members, setMembers] = useState<SuperAdminMemberSummary[]>([]);
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMembers();
  }, []);

  async function loadMembers() {
    setError(null);
    try {
      setMembers(await api.superAdminMembers({ role: role || undefined, status: status || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members");
    } finally {
      setLoading(false);
    }
  }

  function onFilter(event: FormEvent) {
    event.preventDefault();
    loadMembers();
  }

  if (loading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Members" description="All business memberships and statuses." />
      <ErrorMessage message={error} />
      <Card>
        <form onSubmit={onFilter} className="mb-4 grid gap-2 md:grid-cols-[1fr_1fr_auto]">
          <Input value={role} onChange={(event) => setRole(event.target.value)} placeholder="Role" />
          <Input value={status} onChange={(event) => setStatus(event.target.value)} placeholder="Status" />
          <Button>Filter</Button>
        </form>
        <AdminTable
          headers={["Business", "User email", "Role", "Status", "Created"]}
          rows={members.map((member) => [
            `${member.business_name} (#${member.business_id})`,
            member.user_email,
            member.role,
            member.status,
            formatDate(member.created_at)
          ])}
        />
      </Card>
    </div>
  );
}
