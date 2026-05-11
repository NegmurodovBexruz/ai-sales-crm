"use client";

import { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { Conversation, Customer } from "@/lib/types";
import { Badge, Card, EmptyState, ErrorMessage, LoadingState } from "@/components/ui";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.customers()
      .then((data) => {
        setCustomers(data);
        setSelected(data[0] ?? null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Mijozlarni yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setConversationLoading(true);
    api.conversations(selected.id)
      .then(setConversations)
      .catch((err) => setError(err instanceof Error ? err.message : "Suhbatni yuklab bo‘lmadi"))
      .finally(() => setConversationLoading(false));
  }, [selected]);

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Mijozlar</h1>
        <p className="text-sm text-slate-500">Mijozni tanlab, suhbat tarixini ko‘ring.</p>
      </div>
      <ErrorMessage message={error} />
      {loading ? <LoadingState /> : customers.length === 0 ? <EmptyState label="Hali mijoz yo‘q." /> : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <Card className="overflow-x-auto p-0">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b bg-slate-50 text-slate-500">
                <tr>
                  <th className="p-3">To‘liq ism</th>
                  <th className="p-3">Username</th>
                  <th className="p-3">Telefon</th>
                  <th className="p-3">Til</th>
                  <th className="p-3">Yaratilgan</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((customer) => (
                  <tr
                    key={customer.id}
                    onClick={() => setSelected(customer)}
                    className={`cursor-pointer border-b last:border-0 ${selected?.id === customer.id ? "bg-slate-100" : "hover:bg-slate-50"}`}
                  >
                    <td className="p-3 font-medium text-slate-950">{customer.full_name || "-"}</td>
                    <td className="p-3 text-slate-700">{customer.username ? `@${customer.username}` : "-"}</td>
                    <td className="p-3 text-slate-700">{customer.phone || "-"}</td>
                    <td className="p-3"><Badge>{customer.language}</Badge></td>
                    <td className="p-3 text-slate-500">{formatDate(customer.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <Card>
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-slate-950">{selected?.full_name || "Suhbat"}</h2>
              <p className="text-sm text-slate-500">{selected?.phone || selected?.username || "Mijoz tarixi"}</p>
            </div>
            {conversationLoading ? <LoadingState label="Suhbat yuklanmoqda..." /> : conversations.length === 0 ? <EmptyState label="Suhbat xabarlari yo‘q." /> : (
              <div className="max-h-[620px] space-y-3 overflow-y-auto pr-1">
                {conversations.map((message) => (
                  <div key={message.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <Badge tone={message.sender_type === "customer" ? "yellow" : message.sender_type === "ai" ? "green" : "slate"}>{message.sender_type}</Badge>
                      <span className="text-xs text-slate-500">{formatDate(message.created_at)}</span>
                    </div>
                    <p className="whitespace-pre-wrap text-sm text-slate-800">{message.message_text}</p>
                    {message.intent && <div className="mt-2 text-xs text-slate-500">Intent: {message.intent}</div>}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </section>
  );
}
