import Link from "next/link";
import { Card } from "@/components/ui";

export default function ForgotPasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md text-center">
        <h1 className="text-2xl font-semibold text-slate-950">Forgot password</h1>
        <p className="mt-3 text-sm text-slate-600">
          Password recovery is not available yet. Please contact the administrator.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-flex h-9 items-center justify-center rounded-md border border-slate-300 bg-slate-900 px-3 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          Back to login
        </Link>
      </Card>
    </main>
  );
}
