"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated, logout } from "@/lib/auth";
import type { BusinessMe } from "@/lib/types";
import { Button, Card, ErrorMessage, Input, Label, LoadingState, SecondaryButton, Textarea } from "@/components/ui";

export default function OnboardingPage() {
  const router = useRouter();
  const [state, setState] = useState<BusinessMe | null>(null);
  const [mode, setMode] = useState<"create" | "join" | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [phone, setPhone] = useState("");
  const [adminJoinCode, setAdminJoinCode] = useState("");
  const [notice, setNotice] = useState<{ title: string; message: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    Promise.all([api.me(), api.businessMe()])
      .then(([currentUser, businessMe]) => {
        if (currentUser.global_role === "super_admin") {
          router.replace("/super-admin");
          return;
        }
        setState(businessMe);
        if (businessMe.business && businessMe.membership?.status === "active") {
          router.replace("/dashboard");
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Akkaunt holatini yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, [router]);

  async function createBusiness(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.createBusiness({ name, description: description || null, phone: phone || null });
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Biznes yaratib bo‘lmadi");
    } finally {
      setSaving(false);
    }
  }

  async function joinBusiness(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const response = await api.joinBusiness(adminJoinCode.trim().toUpperCase());
      const alreadyPending = response.message?.toLowerCase().includes("already");
      setNotice({
        title: alreadyPending ? "So‘rov yuborilgan" : "So‘rov yuborildi",
        message: alreadyPending
          ? "So‘rov allaqachon yuborilgan. Owner tasdiqlashini kuting."
          : "Owner tasdiqlasa sizni biznes panelga avtomatik o‘tkazamiz."
      });
      const businessMe = await api.businessMe();
      setState(businessMe);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Qo‘shilish so‘rovini yuborib bo‘lmadi");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <main className="min-h-screen bg-slate-50 p-4"><LoadingState /></main>;

  const pending = state?.pending_requests?.[0];

  function goInitial() {
    setMode(null);
    setAdminJoinCode("");
    setError(null);
    setNotice(null);
  }

  if (notice) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-md text-center">
          <h1 className="text-2xl font-semibold text-slate-950">{notice.title}</h1>
          <p className="mt-3 text-sm text-slate-600">{notice.message}</p>
          <Button className="mt-6" onClick={goInitial}>OK</Button>
        </Card>
      </main>
    );
  }

  if (pending && mode === null) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-md text-center">
          <h1 className="text-2xl font-semibold text-slate-950">So‘rov yuborilgan</h1>
          <p className="mt-3 text-sm text-slate-600">
            Owner tasdiqlasa sizni biznes panelga avtomatik o‘tkazamiz.
          </p>
          <div className="mt-6 flex justify-center gap-2">
            <Button onClick={goInitial}>OK</Button>
            <SecondaryButton onClick={logout}>Chiqish</SecondaryButton>
          </div>
        </Card>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-2xl">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-950">Biznesga kirishni sozlash</h1>
            <p className="mt-1 text-sm text-slate-500">Yangi biznes yarating yoki mavjud biznesga admin sifatida qo‘shiling.</p>
          </div>
          <SecondaryButton onClick={logout}>Chiqish</SecondaryButton>
        </div>
        <ErrorMessage message={error} />
        {mode === null && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => setMode("create")}
              className="rounded-lg border border-slate-200 bg-white p-6 text-left shadow-sm transition hover:border-slate-400 hover:bg-slate-50"
            >
              <div className="text-lg font-semibold text-slate-950">Biznes yaratish</div>
              <div className="mt-2 text-sm text-slate-500">Owner sifatida yangi biznes ish joyini boshlang.</div>
            </button>
            <button
              type="button"
              onClick={() => setMode("join")}
              className="rounded-lg border border-slate-200 bg-white p-6 text-left shadow-sm transition hover:border-slate-400 hover:bg-slate-50"
            >
              <div className="text-lg font-semibold text-slate-950">Admin sifatida qo‘shilish</div>
              <div className="mt-2 text-sm text-slate-500">Owner bergan admin join code orqali so‘rov yuboring.</div>
            </button>
          </div>
        )}
        {mode === "create" && (
          <form onSubmit={createBusiness} className="mt-6 space-y-4">
            <div>
              <Label>Biznes nomi</Label>
              <Input value={name} onChange={(event) => setName(event.target.value)} required />
            </div>
            <div>
              <Label>Telefon</Label>
              <Input value={phone} onChange={(event) => setPhone(event.target.value)} />
            </div>
            <div>
              <Label>Tavsif</Label>
              <Textarea value={description} onChange={(event) => setDescription(event.target.value)} />
            </div>
            <div className="flex gap-2">
              <Button disabled={saving}>{saving ? "Yaratilmoqda..." : "Biznes yaratish"}</Button>
              <SecondaryButton type="button" onClick={goInitial}>Ortga</SecondaryButton>
            </div>
          </form>
        )}
        {mode === "join" && (
          <form onSubmit={joinBusiness} className="mt-6 space-y-4">
            <div>
              <Label>Admin join code</Label>
              <Input value={adminJoinCode} onChange={(event) => setAdminJoinCode(event.target.value)} placeholder="ADM-8KQ2M9" required />
              <p className="mt-1 text-sm text-slate-500">Admin join code ni biznes owneridan oling.</p>
            </div>
            <div className="flex gap-2">
              <Button disabled={saving}>{saving ? "Yuborilmoqda..." : "So‘rov yuborish"}</Button>
              <SecondaryButton type="button" onClick={goInitial}>Ortga</SecondaryButton>
            </div>
          </form>
        )}
      </Card>
    </main>
  );
}
