import { describe, it, expect } from 'vitest'
import i18n from './index'

describe('i18n messages', () => {
  it('keeps shared common keys after merging admin locales', () => {
    const enMessages = i18n.global.getLocaleMessage('en')
    const zhCNMessages = i18n.global.getLocaleMessage('zh-CN')

    expect(enMessages.common.appName).toBe('AImyChats')
    expect(enMessages.common.settings).toBe('Settings')
    expect(zhCNMessages.common.appName).toBe('AImyChats')
    expect(zhCNMessages.common.settings).toBe('设置')
  })
})
