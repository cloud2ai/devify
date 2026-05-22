import { beforeAll, describe, expect, it, vi } from 'vitest'

let i18n

describe('i18n messages', () => {
  beforeAll(async () => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {}
    })
    vi.stubGlobal('navigator', {
      language: 'en',
      userLanguage: 'en'
    })

    i18n = (await import('./index')).default
  })

  it('keeps shared common keys after merging admin locales', () => {
    const enMessages = i18n.global.getLocaleMessage('en')
    const zhCNMessages = i18n.global.getLocaleMessage('zh-CN')

    expect(enMessages.common.appName).toBe('AImyChats')
    expect(enMessages.common.settings).toBe('Settings')
    expect(enMessages.billing.creditsInfo.attachmentLimit).toBe('Attachment Limit')
    expect(zhCNMessages.common.appName).toBe('AImyChats')
    expect(zhCNMessages.common.settings).toBe('设置')
    expect(zhCNMessages.billing.creditsInfo.attachmentLimit).toBe('附件数量')
  })
})
