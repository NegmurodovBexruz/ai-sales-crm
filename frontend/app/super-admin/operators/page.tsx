"use client";

import { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { SuperAdminOperatorSummary } from "@/lib/types";
import { Card, ErrorMessage, LoadingState } from "@/components/ui";
import { AdminTable, PageHeader, StatusText } from "@/app/super-admin/_components";

export default function SuperAdminOperatorsPage() {
  const [operators, setOperators] = useState<SuperAdminOperatorSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.superAdminOperators()
      .then(setOperators)
      .catch((err) => setError(err instanceof Error ? err.message : "Operatorlarni yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Operatorlar" description="Platformadagi barcha Telegram operatorlar." />
      <ErrorMessage message={error} />
      <Card>
        <AdminTable
          headers={["Biznes", "Operator nomi", "Telegram chat ID", "Username", "Holati", "Yaratilgan"]}
          rows={operators.map((operator) => [
            `${operator.business_name} (#${operator.business_id})`,
            operator.name,
            operator.telegram_chat_id,
            operator.username || "-",
            <StatusText key="status" active={operator.is_active} />,
            formatDate(operator.created_at)
          ])}
        />
      </Card>
    </div>
  );
}
