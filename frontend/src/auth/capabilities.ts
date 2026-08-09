import { useAuthenticatedSession } from './authContext'

export function hasCapability(capabilities: readonly string[], capability: string) {
  return capabilities.includes(capability)
}

export function useHasCapability(capability: string) {
  const session = useAuthenticatedSession()
  return hasCapability(session.capabilities, capability)
}
