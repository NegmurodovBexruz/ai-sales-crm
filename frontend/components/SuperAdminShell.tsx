"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { isAuthenticated, logout } from "@/lib/auth";
import type { User } from "@/lib/types";
import { SecondaryButton } from "@/components/ui";

const links = [
  { href: "/super-admin", label: "Statistika" },
  { href: "/super-admin/businesses", label: "Bizneslar" },
  { href: "/super-admin/users", label: "Foydalanuvchilar" },
  { href: "/super-admin/orders", label: "Buyurtmalar" },
  { href: "/super-admin/members", label: "A’zolar" },
  { href: "/super-admin/operators", label: "Operatorlar" }
];

export function SuperAdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api.me()
      .then((currentUser) => {
        if (currentUser.global_role !== "super_admin") {
          router.replace("/dashboard");
          return;
        }
        setUser(currentUser);
        setCheckingAuth(false);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  if (checkingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
        Super admin yuklanmoqda...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white p-4 md:block">
        <div className="mb-6">
          <div className="text-lg font-semibold text-slate-950">AI Sales CRM</div>
          <div className="text-sm text-slate-500">Super admin</div>
        </div>
        <nav className="space-y-1">
          {links.map((link) => {
            const active = pathname === link.href || (link.href !== "/super-admin" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`block rounded-md px-3 py-2 text-sm font-medium ${
                  active ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="md:pl-64">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white">
          <div className="flex min-h-16 items-center justify-between gap-3 px-4 md:px-6">
            <div>
              <div className="text-sm text-slate-500">Kirish emaili</div>
              <div className="text-sm font-medium text-slate-900">{user?.email ?? "..."}</div>
            </div>
            <div className="flex items-center gap-2">
              <nav className="flex max-w-[55vw] gap-1 overflow-x-auto md:hidden">
                {links.map((link) => (
                  <Link key={link.href} href={link.href} className="rounded-md px-2 py-1 text-xs text-slate-700 hover:bg-slate-100">
                    {link.label}
                  </Link>
                ))}
              </nav>
              <SecondaryButton onClick={logout}>Chiqish</SecondaryButton>
            </div>
          </div>
        </header>
        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
