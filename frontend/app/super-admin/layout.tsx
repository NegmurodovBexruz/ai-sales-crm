import { SuperAdminShell } from "@/components/SuperAdminShell";

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  return <SuperAdminShell>{children}</SuperAdminShell>;
}
