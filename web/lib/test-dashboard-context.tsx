"use client"

import { createContext, useContext, type ReactNode } from "react"

const TestDashboardModeContext = createContext(false)

export function TestDashboardProvider({ children }: { children: ReactNode }) {
  return (
    <TestDashboardModeContext.Provider value={true}>
      {children}
    </TestDashboardModeContext.Provider>
  )
}

export function useTestDashboardMode() {
  return useContext(TestDashboardModeContext)
}
