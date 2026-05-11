"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { Business, TelegramStatus } from "@/lib/types";
import { Button, Card, EmptyState, ErrorMessage, Input, Label, LoadingState, Textarea } from "@/components/ui";

type BusinessForm = {
  name: string;
  description: string;
  phone: string;
  delivery_policy: string;
  return_policy: string;
  working_hours: string;
  ai_tone: string;
};

export default function SettingsPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [isOwner, setIsOwner] = useState(false);
  const [canManageTelegram, setCanManageTelegram] = useState(false);
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramStatus, setTelegramStatus] = useState<TelegramStatus | null>(null);
  const [form, setForm] = useState<BusinessForm>({
    name: "",
    description: "",
    phone: "",
    delivery_policy: "",
    return_policy: "",
    working_hours: "",
    ai_tone: ""
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [savingTelegram, setSavingTelegram] = useState(false);
  const [settingWebhook, setSettingWebhook] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function applyBusiness(nextBusiness: Business | null) {
    setBusiness(nextBusiness);
    if (!nextBusiness) return;
    setForm({
      name: nextBusiness.name ?? "",
      description: nextBusiness.description ?? "",
      phone: nextBusiness.phone ?? "",
      delivery_policy: nextBusiness.delivery_policy ?? "",
      return_policy: nextBusiness.return_policy ?? "",
      working_hours: nextBusiness.working_hours ?? "",
      ai_tone: nextBusiness.ai_tone ?? ""
    });
  }

  useEffect(() => {
    api.businessMe()
      .then(async (data) => {
        const owner = data.membership?.role === "owner";
        const telegramManager = data.membership?.role === "owner" || data.membership?.role === "admin";
        setIsOwner(owner);
        setCanManageTelegram(telegramManager);
        applyBusiness(data.business);
        if (data.business && telegramManager) {
          setTelegramStatus(await api.telegramStatus(data.business.id));
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load business"))
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!business) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateBusiness(business.id, form);
      applyBusiness(updated);
      setMessage("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  async function onFileChange(file?: File) {
    if (!business || !file) return;
    if (!file.name.toLowerCase().endsWith(".docx")) {
      setError("Please upload a .docx file.");
      return;
    }
    setUploading(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.uploadKnowledgeDocx(business.id, file);
      applyBusiness(updated);
      setMessage("Knowledge document uploaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload document");
    } finally {
      setUploading(false);
    }
  }

  async function copyCode(value?: string | null) {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setMessage("Copied.");
  }

  async function saveTelegramToken() {
    if (!business) return;
    setSavingTelegram(true);
    setError(null);
    setMessage(null);
    try {
      const status = await api.saveTelegramToken(business.id, telegramToken);
      setTelegramStatus(status);
      setTelegramToken("");
      setMessage("Telegram token saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save Telegram token");
    } finally {
      setSavingTelegram(false);
    }
  }

  async function setWebhook() {
    if (!business) return;
    setSettingWebhook(true);
    setError(null);
    setMessage(null);
    try {
      const status = await api.setTelegramWebhook(business.id);
      setTelegramStatus(status);
      setMessage("Telegram webhook set.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set Telegram webhook");
    } finally {
      setSettingWebhook(false);
    }
  }

  function AccessCodeRow({ label, value }: { label: string; value?: string | null }) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
        <div>
          <div className="text-xs uppercase text-slate-500">{label}</div>
          <div className="font-mono text-sm font-medium text-slate-950">{value || "-"}</div>
        </div>
        <Button type="button" disabled={!value} onClick={() => copyCode(value)}>Copy</Button>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Settings</h1>
        <p className="text-sm text-slate-500">Manage business profile and AI knowledge.</p>
      </div>
      <ErrorMessage message={error} />
      {message && <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
      {loading ? <LoadingState /> : !business ? <EmptyState label="No business found for this account." /> : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <Card>
            <form onSubmit={onSubmit} className="grid gap-4 lg:grid-cols-2">
              {!isOwner && (
                <div className="lg:col-span-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  Only the business owner can edit profile settings.
                </div>
              )}
              <div>
                <Label>Name</Label>
                <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required disabled={!isOwner} />
              </div>
              <div>
                <Label>Phone</Label>
                <Input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} disabled={!isOwner} />
              </div>
              <div>
                <Label>Working hours</Label>
                <Input value={form.working_hours} onChange={(event) => setForm({ ...form, working_hours: event.target.value })} disabled={!isOwner} />
              </div>
              <div>
                <Label>AI tone</Label>
                <Input value={form.ai_tone} onChange={(event) => setForm({ ...form, ai_tone: event.target.value })} placeholder="friendly, formal, short" disabled={!isOwner} />
              </div>
              <div className="lg:col-span-2">
                <Label>Description</Label>
                <Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} disabled={!isOwner} />
              </div>
              <div className="lg:col-span-2">
                <Label>Delivery policy</Label>
                <Textarea value={form.delivery_policy} onChange={(event) => setForm({ ...form, delivery_policy: event.target.value })} disabled={!isOwner} />
              </div>
              <div className="lg:col-span-2">
                <Label>Return policy</Label>
                <Textarea value={form.return_policy} onChange={(event) => setForm({ ...form, return_policy: event.target.value })} disabled={!isOwner} />
              </div>
              <div className="lg:col-span-2">
                <Button disabled={saving || !isOwner}>{saving ? "Saving..." : "Save settings"}</Button>
              </div>
            </form>
          </Card>
          <div className="space-y-4">
            {canManageTelegram && (
              <Card>
                <h2 className="text-lg font-semibold text-slate-950">Telegram Bot</h2>
                <div className="mt-4 space-y-3 text-sm">
                  <p className="text-slate-500">Create a bot using BotFather and paste the token here.</p>
                  <div>
                    <Label>Telegram bot token</Label>
                    <Input
                      type="password"
                      value={telegramToken}
                      onChange={(event) => setTelegramToken(event.target.value)}
                      placeholder={telegramStatus?.has_token ? "Token connected" : "123456:ABC..."}
                    />
                  </div>
                  <p className="text-slate-500">After saving token, click Set Webhook.</p>
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" disabled={savingTelegram || !telegramToken.trim()} onClick={saveTelegramToken}>
                      {savingTelegram ? "Saving..." : "Save token"}
                    </Button>
                    <Button type="button" disabled={settingWebhook || !telegramStatus?.has_token} onClick={setWebhook}>
                      {settingWebhook ? "Setting..." : "Set Webhook"}
                    </Button>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-slate-500">Webhook status</div>
                    <div className="mt-1 font-medium text-slate-950">{telegramStatus?.webhook_set ? "Webhook set" : "Webhook not set"}</div>
                    <div className="mt-2 text-slate-500">Token</div>
                    <div className="font-medium text-slate-950">{telegramStatus?.has_token ? "Token connected" : "No token connected"}</div>
                    <div className="mt-2 text-slate-500">Webhook URL</div>
                    <div className="break-all font-mono text-xs text-slate-700">{telegramStatus?.webhook_url || "BACKEND_URL is not configured"}</div>
                  </div>
                </div>
              </Card>
            )}
          <Card>
            <h2 className="text-lg font-semibold text-slate-950">Business access</h2>
            <div className="mt-4 space-y-3">
              <AccessCodeRow label="Public business ID" value={business.public_business_id} />
              <AccessCodeRow label="Admin join code" value={business.admin_join_code} />
              <AccessCodeRow label="Operator code" value={business.operator_code} />
            </div>
          </Card>
          <Card>
            <h2 className="text-lg font-semibold text-slate-950">Knowledge document</h2>
            <div className="mt-4 space-y-3 text-sm">
              <div>
                <div className="text-slate-500">File</div>
                <div className="font-medium text-slate-950">{business.knowledge_file_name || "No file uploaded"}</div>
              </div>
              <div>
                <div className="text-slate-500">Uploaded</div>
                <div className="font-medium text-slate-950">{formatDate(business.knowledge_uploaded_at)}</div>
              </div>
              <div>
                <Label>Upload .docx</Label>
                <Input type="file" accept=".docx" disabled={uploading || !isOwner} onChange={(event) => onFileChange(event.target.files?.[0])} />
              </div>
              <div>
                <div className="mb-1 text-slate-500">Preview</div>
                <div className="max-h-80 overflow-y-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-3 text-slate-700">
                  {business.business_knowledge_text || "No extracted knowledge text yet."}
                </div>
              </div>
              {uploading && <div className="text-slate-500">Uploading...</div>}
            </div>
          </Card>
          </div>
        </div>
      )}
    </section>
  );
}
