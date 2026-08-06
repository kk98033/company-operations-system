import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiRequestError, getApiErrorMessage } from './errorMessage'
import { getApiReadiness } from './health'

afterEach(() => vi.unstubAllGlobals())

describe('產生的 OpenAPI health client', () => {
  it('成功時回傳產生型別約束的 readiness 資料', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json({
      checks: [{ name: 'database', status: 'ok' }],
      status: 'ready',
    }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getApiReadiness()).resolves.toEqual({
      checks: [{ name: 'database', status: 'ok' }],
      status: 'ready',
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/health/ready',
      expect.objectContaining({ credentials: 'same-origin', method: 'GET' }),
    )
  })

  it('503 envelope 會轉成 TanStack Query 可辨識的安全錯誤', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(Response.json({
      error: {
        code: 'SERVICE_NOT_READY',
        details: { checks: [{ name: 'database', status: 'error' }] },
        message: '必要相依服務尚未就緒',
      },
    }, { status: 503 })))

    await expect(getApiReadiness()).rejects.toEqual(
      expect.objectContaining<ApiRequestError>({
        code: 'SERVICE_NOT_READY',
        details: { checks: [{ name: 'database', status: 'error' }] },
        message: '必要相依服務尚未就緒',
        name: 'ApiRequestError',
        status: 503,
      }),
    )
  })

  it('網路、非 JSON 與未知錯誤不會洩漏底層例外', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockRejectedValue(
      new TypeError('Failed to fetch database secret'),
    ))
    await expect(getApiReadiness()).rejects.toEqual(expect.objectContaining({
      code: 'NETWORK_ERROR',
      message: '無法連線至系統服務，請確認網路後再試。',
      status: null,
    }))

    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(
      new Response('database secret', { status: 500 }),
    ))
    await expect(getApiReadiness()).rejects.toEqual(expect.objectContaining({
      code: 'UNEXPECTED_RESPONSE',
      message: '系統暫時無法完成操作，請稍後再試。',
      status: null,
    }))

    expect(getApiErrorMessage(new Error('database secret')))
      .toBe('系統暫時無法完成操作，請稍後再試。')
  })
})
