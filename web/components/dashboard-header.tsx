"use client"

import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { formatLastUpdated } from "@/lib/format"

function ThemeToggle() {
  const { setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const isDark = resolvedTheme === "dark"

  if (!mounted) {
    return (
      <Button variant="outline" size="icon" disabled aria-label="Toggle theme">
        <Sun className="h-4 w-4 opacity-0" aria-hidden />
      </Button>
    )
  }

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  )
}

interface DashboardHeaderProps {
  lastUpdatedAt: number | null
  errorMessage: string | null
}

export function DashboardHeader({
  lastUpdatedAt,
  errorMessage,
}: DashboardHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Smart Queue Dashboard</h1>
        {lastUpdatedAt && (
          <p className="text-sm text-muted-foreground">
            Last updated: {formatLastUpdated(lastUpdatedAt)}
          </p>
        )}
        {errorMessage && (
          <p className="text-sm text-destructive">{errorMessage}</p>
        )}
      </div>
      <ThemeToggle />
    </div>
  )
}
