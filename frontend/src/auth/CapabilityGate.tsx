import type { PropsWithChildren, ReactNode } from 'react'

import { useHasCapability } from './capabilities'

export function CapabilityGate({
  capability,
  children,
  fallback = null,
}: PropsWithChildren<{ capability: string; fallback?: ReactNode }>) {
  return useHasCapability(capability) ? children : fallback
}
