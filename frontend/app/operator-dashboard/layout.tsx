import { OperatorDashboardShell } from "@/components/OperatorDashboardShell";

export default function OperatorDashboardLayout({ children }: { children: React.ReactNode }) {
  return <OperatorDashboardShell>{children}</OperatorDashboardShell>;
}
