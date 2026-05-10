"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { Button, Card, ErrorMessage, Input, Label } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("created") === "1") {
      setSuccess("Account created. Please log in.");
    }
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const token = await api.login(email, password);
      setToken(token.access_token);
      const currentUser = await api.me();
      if (currentUser.global_role === "super_admin") {
        router.replace("/super-admin");
        return;
      }
      const businessMe = await api.businessMe();
      if (businessMe.business && businessMe.membership?.status === "active") {
        router.replace("/dashboard");
        return;
      }
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-950">Login</h1>
          <p className="mt-1 text-sm text-slate-500">AI Sales CRM dashboardga kirish.</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <ErrorMessage message={error} />
          {success && <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{success}</div>}
          <div>
            <Label>Email</Label>
            <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          <div>
            <Label>Password</Label>
            <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </div>
          <div className="flex items-center justify-between gap-3">
            <Link href="/signup" className="text-sm font-medium text-slate-600 hover:text-slate-950">
              Sign up
            </Link>
            <Link href="/forgot-password" className="text-sm font-medium text-slate-600 hover:text-slate-950">
              Forgot password?
            </Link>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
