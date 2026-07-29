import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

const { createSubscription, updateSubscription } = vi.hoisted(() => ({
  createSubscription: vi.fn(),
  updateSubscription: vi.fn()
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key })
}))

vi.mock('@/api/relay', () => ({
  relayApi: {
    createSubscription,
    updateSubscription
  }
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showError: vi.fn(),
    showSuccess: vi.fn()
  })
}))

import { useRelayEditor } from './useRelayEditor'

describe('useRelayEditor GitHub Issue target', () => {
  beforeEach(() => {
    createSubscription.mockReset()
    updateSubscription.mockReset()
  })

  function createEditor() {
    return useRelayEditor({
      reloadAll: vi.fn(),
      activeTab: ref('channels')
    })
  }

  it('builds a GitHub test payload with repo credentials and mappings', () => {
    const { editorForm, buildTestPayload } = createEditor()
    editorForm.target_type = 'github_issue'
    editorForm.language = 'English'
    editorForm.githubConfig.repo = 'cloud2ai/devify'
    editorForm.githubConfig.token = 'github-token'
    editorForm.githubConfig.labels_text = 'relay\nneeds-review'
    editorForm.githubConfig.assignees_text = 'octocat\nhubot'

    const payload = buildTestPayload()

    expect(payload.subscription.config).toMatchObject({
      issue_engine: 'github_issue',
      language: 'English',
      github: {
        repo: 'cloud2ai/devify',
        token: 'github-token',
        labels: ['relay', 'needs-review'],
        assignees: ['octocat', 'hubot']
      }
    })
    expect(payload.artifact_snapshot).toMatchObject({
      summary_title: 'devify 测试摘要',
      summary_content: 'devify 测试描述',
      language: 'Chinese'
    })
  })

  it('restores GitHub config when editing a subscription', () => {
    const { editorForm, editSubscription } = createEditor()

    editSubscription({
      id: 22,
      target_type: 'github_issue',
      name: 'Devify GitHub',
      enabled: true,
      strategies: {},
      field_mappings: {},
      config: {
        language: 'English',
        github: {
          repo: 'cloud2ai/devify',
          token: 'github-token',
          labels: ['relay', 'bug'],
          assignees: ['octocat']
        }
      }
    })

    expect(editorForm.githubConfig).toEqual({
      repo: 'cloud2ai/devify',
      token: 'github-token',
      labels_text: 'relay\nbug',
      assignees_text: 'octocat'
    })
  })

  it('persists GitHub config using string arrays', async () => {
    createSubscription.mockResolvedValue({ id: 22 })
    const { editorForm, persistEditor } = createEditor()
    editorForm.target_type = 'github_issue'
    editorForm.name = 'Devify GitHub'
    editorForm.githubConfig.repo = 'cloud2ai/devify'
    editorForm.githubConfig.token = 'github-token'
    editorForm.githubConfig.labels_text = 'relay\nfeature'
    editorForm.githubConfig.assignees_text = 'octocat'

    await persistEditor()

    expect(createSubscription).toHaveBeenCalledWith(
      expect.objectContaining({
        target_type: 'github_issue',
        config: expect.objectContaining({
          issue_engine: 'github_issue',
          github: {
            repo: 'cloud2ai/devify',
            token: 'github-token',
            labels: ['relay', 'feature'],
            assignees: ['octocat']
          }
        })
      })
    )
  })
})
