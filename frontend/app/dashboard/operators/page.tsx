"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { Business, TelegramOperator } from "@/lib/types";
import { Badge, Button, Card, DangerButton, EmptyState, ErrorMessage, Input, Label, LoadingState, SecondaryButton } from "@/components/ui";

type OperatorForm = {
  name: string;
  telegram_chat_id: string;
  username: string;
  is_active: boolean;
};

const emptyForm: OperatorForm = {
  name: "",
  telegram_chat_id: "",
  username: "",
  is_active: true
};

export default function OperatorsPage() {
  const [operators, setOperators] = useState<TelegramOperator[]>([]);
  const [business, setBusiness] = useState<Business | null>(null);
  const [form, setForm] = useState<OperatorForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadData() {
    const [operatorList, businessState] = await Promise.all([api.operators(), api.businessMe()]);
    setOperators(operatorList);
    setBusiness(businessState.business);
  }

  useEffect(() => {
    loadData()
      .catch((err) => setError(err instanceof Error ? err.message : "Operatorlarni yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, []);

  function startEdit(operator: TelegramOperator) {
    setEditingId(operator.id);
    setForm({
      name: operator.name,
      telegram_chat_id: operator.telegram_chat_id,
      username: operator.username ?? "",
      is_active: operator.is_active
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    const payload = {
      name: form.name,
      telegram_chat_id: form.telegram_chat_id,
      username: form.username || null,
      is_active: form.is_active
    };
    try {
      if (editingId) {
        await api.updateOperator(editingId, payload);
        setMessage("Operator yangilandi.");
      } else {
        await api.createOperator(payload);
        setMessage("Operator qo‘shildi.");
      }
      resetForm();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operatorni saqlab bo‘lmadi");
    } finally {
      setSaving(false);
    }
  }

  async function run(action: () => Promise<unknown>, success: string) {
    setError(null);
    setMessage(null);
    try {
      await action();
      await loadData();
      setMessage(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operator amali bajarilmadi");
    }
  }

  async function copyCode(value?: string | null) {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setMessage("Operator code nusxalandi.");
  }

  const activeCount = operators.filter((operator) => operator.is_active).length;

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Operatorlar</h1>
        <p className="text-sm text-slate-500">AI yo‘naltirish va buyurtma xabarlari uchun Telegram operatorlarni boshqaring.</p>
      </div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
      {!loading && activeCount === 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Aktiv operator yo‘q. AI operatorga yo‘naltira olmaydi.
        </div>
      )}
      {!loading && business && (
        <Card>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-medium text-slate-700">Operator paneli code</div>
              <div className="mt-1 font-mono text-lg font-semibold text-slate-950">{business.operator_code || "-"}</div>
              <p className="mt-1 text-sm text-slate-500">
                Operator paneliga kirishi uchun operatorga Operator code va uning Telegram chat ID kerak bo‘ladi.
              </p>
            </div>
            <Button type="button" disabled={!business.operator_code} onClick={() => copyCode(business.operator_code)}>
              Code nusxalash
            </Button>
          </div>
        </Card>
      )}
      <Card>
        <form onSubmit={onSubmit} className="grid gap-4 lg:grid-cols-4">
          <div>
            <Label>Operator nomi</Label>
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </div>
          <div>
            <Label>Telegram chat ID</Label>
            <Input value={form.telegram_chat_id} onChange={(event) => setForm({ ...form, telegram_chat_id: event.target.value })} required />
          </div>
          <div>
            <Label>Telegram username</Label>
            <Input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} placeholder="ali_operator" />
          </div>
          <label className="flex items-center gap-2 pt-7 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
              className="h-4 w-4"
            />
            Aktiv
          </label>
          <div className="lg:col-span-4">
            <p className="text-sm text-slate-500">
              Operator Telegram ID ni olish uchun operator @userinfobot botiga yozib, o‘z ID raqamini yuborishi kerak.
            </p>
          </div>
          <div className="flex gap-2 lg:col-span-4">
            <Button disabled={saving}>{saving ? "Saqlanmoqda..." : editingId ? "Operatorni saqlash" : "Operator qo‘shish"}</Button>
            {editingId && <SecondaryButton type="button" onClick={resetForm}>Tahrirlashni bekor qilish</SecondaryButton>}
          </div>
        </form>
      </Card>
      {loading ? <LoadingState /> : operators.length === 0 ? (
        <EmptyState label="Hali operator qo‘shilmagan. AI operatorga yo‘naltirishi uchun kamida bitta Telegram operator qo‘shing." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b bg-slate-50 text-slate-500">
              <tr>
                <th className="p-3">Nomi</th>
                <th className="p-3">Telegram chat ID</th>
                <th className="p-3">Username</th>
                <th className="p-3">Holati</th>
                <th className="p-3">Yaratilgan</th>
                <th className="p-3">Amallar</th>
              </tr>
            </thead>
            <tbody>
              {operators.map((operator) => (
                <tr key={operator.id} className="border-b last:border-0">
                  <td className="p-3 font-medium text-slate-950">{operator.name}</td>
                  <td className="p-3 text-slate-700">{operator.telegram_chat_id}</td>
                  <td className="p-3 text-slate-700">{operator.username ? `@${operator.username}` : "-"}</td>
                  <td className="p-3">
                    <Badge tone={operator.is_active ? "green" : "red"}>{operator.is_active ? "Aktiv" : "Noaktiv"}</Badge>
                  </td>
                  <td className="p-3 text-slate-500">{formatDate(operator.created_at)}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      <SecondaryButton onClick={() => startEdit(operator)}>Tahrirlash</SecondaryButton>
                      <SecondaryButton onClick={() => run(() => api.updateOperator(operator.id, { is_active: !operator.is_active }), operator.is_active ? "Operator noaktiv qilindi." : "Operator aktiv qilindi.")}>
                        {operator.is_active ? "Noaktiv qilish" : "Aktiv qilish"}
                      </SecondaryButton>
                      <DangerButton onClick={() => run(() => api.deleteOperator(operator.id), "Operator o‘chirildi yoki noaktiv qilindi.")}>O‘chirish</DangerButton>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
