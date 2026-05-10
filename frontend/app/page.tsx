"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api.me()
      .then((user) => {
        router.replace(user.global_role === "super_admin" ? "/super-admin" : "/dashboard");
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  return null;
}
