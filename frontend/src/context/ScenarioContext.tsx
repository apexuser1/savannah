import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode
} from 'react'
import type { AppliedScenario } from '../types'

interface ScenarioContextValue {
  appliedScenario?: AppliedScenario
  applyScenario: (scenario: AppliedScenario) => void
  clearScenario: () => void
}

const ScenarioContext = createContext<ScenarioContextValue | undefined>(undefined)

export const ScenarioProvider = ({ children }: { children: ReactNode }) => {
  const [appliedScenario, setAppliedScenario] = useState<AppliedScenario | undefined>(undefined)

  const applyScenario = useCallback((scenario: AppliedScenario) => {
    setAppliedScenario(scenario)
  }, [])

  const clearScenario = useCallback(() => {
    setAppliedScenario(undefined)
  }, [])

  const value = useMemo(
    () => ({
      appliedScenario,
      applyScenario,
      clearScenario
    }),
    [appliedScenario, applyScenario, clearScenario]
  )

  return <ScenarioContext.Provider value={value}>{children}</ScenarioContext.Provider>
}

export const useScenario = () => {
  const context = useContext(ScenarioContext)
  if (!context) {
    throw new Error('useScenario must be used within ScenarioProvider')
  }
  return context
}
