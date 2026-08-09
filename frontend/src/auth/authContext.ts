import { createContext, useContext } from 'react'

import type { CurrentSessionResponse } from '../api/generated/company-system'

export const AuthContext = createContext<CurrentSessionResponse | null>(null)

export function useAuthenticatedSession(): CurrentSessionResponse {
  const session = useContext(AuthContext)
  if (session === null) throw new Error('Authenticated Session context is missing')
  return session
}
