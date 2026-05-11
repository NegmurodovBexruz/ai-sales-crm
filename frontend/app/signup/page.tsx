"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button, Card, ErrorMessage, Input, Label } from "@/components/ui";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Parol kamida 8 ta belgidan iborat bo‘lishi kerak.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Parollar mos emas.");
      return;
    }

    setLoading(true);
    try {
      await api.register({ email, password, full_name: fullName });
      router.replace("/login?created=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Akkaunt yaratib bo‘lmadi");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-950">Ro‘yxatdan o‘tish</h1>
          <p className="mt-1 text-sm text-slate-500">AI Sales CRM uchun owner akkaunt yarating.</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <ErrorMessage message={error} />
          <div>
            <Label>To‘liq ism</Label>
            <Input value={fullName} onChange={(event) => setFullName(event.target.value)} required />
          </div>
          <div>
            <Label>Email</Label>
            <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          <div>
            <Label>Parol</Label>
            <Input type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required />
          </div>
          <div>
            <Label>Parolni tasdiqlash</Label>
            <Input type="password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Akkaunt yaratilmoqda..." : "Akkaunt yaratish"}
          </Button>
        </form>
        <div className="mt-4 text-center text-sm text-slate-600">
          Akkauntingiz bormi?{" "}
          <Link href="/login" className="font-medium text-slate-950 hover:underline">
            Kirish
          </Link>
        </div>
      </Card>
    </main>
  );
}
