import { DashboardShell } from "@/components/dashboard-shell"
import { TestDashboardProvider } from "@/lib/test-dashboard-context"

export default function TestPage() {
  return (
    <TestDashboardProvider>
      <DashboardShell />
    </TestDashboardProvider>
  )
}
