import { screen } from '@testing-library/react'
import { render } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

import { ErrorBoundary } from './ErrorBoundary'

function BrokenPage(): never {
  throw new Error('test render failure')
}

describe('ErrorBoundary', () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

  afterEach(() => {
    consoleError.mockClear()
  })

  it('在子元件 render 失敗時顯示可理解的錯誤頁', () => {
    render(
      <ErrorBoundary>
        <BrokenPage />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('頁面無法顯示')
    expect(screen.getByRole('button', { name: '重新載入' })).toBeInTheDocument()
    expect(consoleError).toHaveBeenCalled()
  })
})
