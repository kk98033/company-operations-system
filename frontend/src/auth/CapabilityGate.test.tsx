import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { syntheticCurrentSession } from '../test/sessionFixture'
import { AuthProvider } from './AuthProvider'
import { CapabilityGate } from './CapabilityGate'
import { hasCapability } from './capabilities'

describe('CapabilityGate', () => {
  it('只顯示 Session 明確授權的操作，不接受角色名稱或萬用字元', () => {
    const session = {
      ...syntheticCurrentSession,
      capabilities: ['settings.manage'],
    }
    render(
      <AuthProvider session={session}>
        <CapabilityGate capability="settings.manage">
          <button type="button">權限設定</button>
        </CapabilityGate>
        <CapabilityGate capability="settings.write" fallback={<span>不可使用</span>}>
          <button type="button">隱藏操作</button>
        </CapabilityGate>
      </AuthProvider>,
    )

    expect(screen.getByRole('button', { name: '權限設定' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '隱藏操作' })).not.toBeInTheDocument()
    expect(screen.getByText('不可使用')).toBeInTheDocument()
    expect(hasCapability(session.capabilities, 'admin')).toBe(false)
    expect(hasCapability(session.capabilities, 'settings.*')).toBe(false)
  })
})
