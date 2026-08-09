import type { PropsWithChildren } from 'react'

import type { CurrentSessionResponse } from '../api/generated/company-system'
import { AuthContext } from './authContext'

export function AuthProvider({
  children,
  session,
}: PropsWithChildren<{ session: CurrentSessionResponse }>) {
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>
}
