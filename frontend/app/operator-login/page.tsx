"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { setOperatorToken } from "@/lib/auth";
import { Button, Card, ErrorMessage, Input, Label } from "@/components/ui";

export default function OperatorLoginPage() {
  const router = useRouter();
  const [operatorCode, setOperatorCode] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await api.operatorLogin(operatorCode.trim(), telegramChatId.trim());
      setOperatorToken(response.access_token);
      router.replace("/operator-dashboard/products");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operator login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-md">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-950">Operator login</h1>
          <p className="text-sm text-slate-500">Use your operator code and Telegram chat ID.</p>
        </div>
        <ErrorMessage message={error} />
        <form onSubmit={onSubmit} className="mt-4 space-y-4">
          <div>
            <Label>Operator code</Label>
            <Input value={operatorCode} onChange={(event) => setOperatorCode(event.target.value)} placeholder="OP-4MZ81Q" required />
          </div>
          <div>
            <Label>Telegram chat ID</Label>
            <Input value={telegramChatId} onChange={(event) => setTelegramChatId(event.target.value)} placeholder="123456789" required />
          </div>
          <Button className="w-full" disabled={loading}>{loading ? "Logging in..." : "Login"}</Button>
        </form>
        <div className="mt-4 text-center text-sm text-slate-500">
          <Link href="/login" className="font-medium text-slate-900 hover:underline">Admin login</Link>
        </div>
      </Card>
    </main>
  );
}
