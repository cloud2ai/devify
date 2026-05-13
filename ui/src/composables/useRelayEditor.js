import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { relayApi } from '@/api/relay'
import { extractErrorMessage } from '@/utils/api'
import { useToast } from '@/composables/useToast'

export function useRelayEditor({ reloadAll, activeTab }) {
  const { t } = useI18n()
  const { showError, showSuccess } = useToast()

  const saving = ref(false)
  const testing = ref(false)
  const showFeishuAppSecret = ref(false)
  const editorVisible = ref(false)
  const editorMode = ref('create')
  const expandedSubscriptionId = ref('')
  const editorError = ref('')
  const editorSuccess = ref('')
  const testSubscriptionId = ref('')
  const editorTestSignature = ref('')

  const defaultStrategies = () => ({
    auto_merge_strategy: 'new',
    manual_merge_strategy: 'linked',
    retry_issue_strategy: 'update'
  })

  const defaultFeishuConfig = () => ({
    app_token_type: 'bitable',
    app_token: '',
    table_name: '',
    app_id: '',
    app_secret: '',
    attachment_field_name: '附件',
    summary_prefix: ''
  })

  const defaultJiraConfig = () => ({
    url: '',
    username: '',
    api_token: '',
    project_key: '',
    issue_type_default: 'Task',
    priority_default: 'Medium',
    summary_prefix: '[AI]',
    add_timestamp: false,
    convert_to_jira_wiki: true,
    assignee_use_llm: true,
    assignee_default: '',
    assignee_allow_values_text: '',
    assignee_prompt: '',
    components_use_llm: false,
    components_fetch_from_api: false,
    components_default_text: '',
    components_prompt: '',
    epic_link_use_llm: true,
    epic_link_fetch_from_api: true,
    epic_link_default: '',
    epic_link_jql_filter: '',
    epic_link_prompt: '',
    description_field: 'description'
  })

  const emptyEditorForm = () => ({
    id: null,
    target_type: 'feishu_bitable',
    name: '',
    enabled: true,
    language: 'Chinese',
    strategies: defaultStrategies(),
    feishuConfig: defaultFeishuConfig(),
    jiraConfig: defaultJiraConfig(),
    fieldMappingRows: [{ source: '', target: '' }]
  })

  const editorForm = reactive(emptyEditorForm())

  function setEditorForm(nextForm) {
    Object.assign(editorForm, emptyEditorForm(), nextForm)
  }

  function normalizeFieldMappingRows(fieldMappings) {
    const entries =
      fieldMappings && typeof fieldMappings === 'object'
        ? Object.entries(fieldMappings)
        : []
    if (entries.length === 0) return [{ source: '', target: '' }]
    return entries.map(([source, target]) => ({
      source: String(source || ''),
      target: String(target || '')
    }))
  }

  function formatMultilineList(value) {
    if (!Array.isArray(value)) return ''
    return value.map((item) => String(item || '')).join('\n')
  }

  function parseMultilineList(text) {
    return String(text || '')
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean)
  }

  function buildFieldMappingsFromRows(rows) {
    return (rows || []).reduce((acc, row) => {
      const source = String(row?.source || '').trim()
      const target = String(row?.target || '').trim()
      if (source && target) acc[source] = target
      return acc
    }, {})
  }

  function buildEditorTestSignature() {
    return JSON.stringify({
      target_type: editorForm.target_type || 'feishu_bitable',
      language: editorForm.language || 'Chinese',
      strategies: {
        auto_merge_strategy: editorForm.strategies.auto_merge_strategy || 'new',
        manual_merge_strategy:
          editorForm.strategies.manual_merge_strategy || 'linked',
        retry_issue_strategy:
          editorForm.strategies.retry_issue_strategy || 'update'
      },
      feishuConfig:
        editorForm.target_type === 'feishu_bitable'
          ? {
              app_token_type:
                editorForm.feishuConfig.app_token_type || 'bitable',
              app_token: editorForm.feishuConfig.app_token || '',
              table_name: editorForm.feishuConfig.table_name || '',
              app_id: editorForm.feishuConfig.app_id || '',
              app_secret: editorForm.feishuConfig.app_secret || '',
              attachment_field_name:
                editorForm.feishuConfig.attachment_field_name || '附件',
              summary_prefix: editorForm.feishuConfig.summary_prefix || '',
              field_mappings: buildFieldMappingsFromRows(
                editorForm.fieldMappingRows
              )
            }
          : {},
      jiraConfig:
        editorForm.target_type === 'jira'
          ? {
              url: editorForm.jiraConfig.url || '',
              username: editorForm.jiraConfig.username || '',
              api_token: editorForm.jiraConfig.api_token || '',
              project_key: editorForm.jiraConfig.project_key || '',
              issue_type_default:
                editorForm.jiraConfig.issue_type_default || 'Task',
              priority_default:
                editorForm.jiraConfig.priority_default || 'Medium',
              summary_prefix: editorForm.jiraConfig.summary_prefix || '[AI]',
              add_timestamp: Boolean(editorForm.jiraConfig.add_timestamp),
              convert_to_jira_wiki: Boolean(
                editorForm.jiraConfig.convert_to_jira_wiki
              ),
              assignee_use_llm: Boolean(editorForm.jiraConfig.assignee_use_llm),
              assignee_default: editorForm.jiraConfig.assignee_default || '',
              assignee_allow_values_text:
                editorForm.jiraConfig.assignee_allow_values_text || '',
              assignee_prompt: editorForm.jiraConfig.assignee_prompt || '',
              components_use_llm: Boolean(
                editorForm.jiraConfig.components_use_llm
              ),
              components_fetch_from_api: Boolean(
                editorForm.jiraConfig.components_fetch_from_api
              ),
              components_default_text:
                editorForm.jiraConfig.components_default_text || '',
              components_prompt: editorForm.jiraConfig.components_prompt || '',
              epic_link_use_llm: Boolean(
                editorForm.jiraConfig.epic_link_use_llm
              ),
              epic_link_fetch_from_api: Boolean(
                editorForm.jiraConfig.epic_link_fetch_from_api
              ),
              epic_link_default: editorForm.jiraConfig.epic_link_default || '',
              epic_link_jql_filter:
                editorForm.jiraConfig.epic_link_jql_filter || '',
              epic_link_prompt: editorForm.jiraConfig.epic_link_prompt || '',
              description_field:
                editorForm.jiraConfig.description_field || 'description'
            }
          : {}
    })
  }

  const editorCurrentSignature = computed(() => buildEditorTestSignature())
  const editorTestPassed = computed(
    () =>
      Boolean(editorTestSignature.value) &&
      editorTestSignature.value === editorCurrentSignature.value
  )
  const editorCanSave = computed(
    () => editorTestPassed.value && !saving.value && !testing.value
  )

  function addFieldMappingRow() {
    editorForm.fieldMappingRows.push({ source: '', target: '' })
  }

  function removeFieldMappingRow(index) {
    if (editorForm.fieldMappingRows.length === 1) {
      editorForm.fieldMappingRows[0] = { source: '', target: '' }
      return
    }
    editorForm.fieldMappingRows.splice(index, 1)
  }

  function resetEditor() {
    setEditorForm()
    editorError.value = ''
    editorSuccess.value = ''
    editorTestSignature.value = ''
    showFeishuAppSecret.value = false
    editorMode.value = 'create'
  }

  function openCreatePanel() {
    resetEditor()
    testSubscriptionId.value = ''
    expandedSubscriptionId.value = ''
    editorVisible.value = true
    activeTab.value = 'channels'
  }

  function cancelEditor() {
    editorVisible.value = false
    expandedSubscriptionId.value = ''
    resetEditor()
  }

  function editSubscription(sub) {
    editorError.value = ''
    editorSuccess.value = ''
    editorTestSignature.value = ''
    showFeishuAppSecret.value = false
    const config = sub.config || {}
    const feishuConfig = config.feishu_bitable || {}
    const jiraConfig = config.jira || {}
    const fieldsConfig = config.fields || {}
    setEditorForm({
      id: sub.id,
      target_type: sub.target_type || 'feishu_bitable',
      name: sub.name || '',
      enabled: Boolean(sub.enabled),
      language: config.language || 'Chinese',
      strategies: {
        auto_merge_strategy:
          sub.strategies?.auto_merge_strategy ||
          config.auto_merge_strategy ||
          'new',
        manual_merge_strategy:
          sub.strategies?.manual_merge_strategy ||
          config.manual_merge_strategy ||
          'linked',
        retry_issue_strategy:
          sub.strategies?.retry_issue_strategy ||
          config.retry_issue_strategy ||
          'update'
      },
      feishuConfig: {
        app_token_type: feishuConfig.app_token_type || 'bitable',
        app_token: feishuConfig.app_token || '',
        table_name: feishuConfig.table_name || '',
        app_id: feishuConfig.app_id || '',
        app_secret: feishuConfig.app_secret || '',
        attachment_field_name: feishuConfig.attachment_field_name || '附件',
        summary_prefix: feishuConfig.summary_prefix || ''
      },
      jiraConfig: {
        url: jiraConfig.url || '',
        username: jiraConfig.username || '',
        api_token: jiraConfig.api_token || '',
        project_key:
          fieldsConfig.project_key_config?.default ||
          jiraConfig.project_key ||
          '',
        issue_type_default:
          fieldsConfig.issue_type_config?.default ||
          jiraConfig.issue_type_default ||
          'Task',
        priority_default:
          fieldsConfig.priority_config?.default ||
          jiraConfig.priority_default ||
          'Medium',
        summary_prefix:
          fieldsConfig.summary_config?.prefix ||
          jiraConfig.summary_prefix ||
          '[AI]',
        add_timestamp:
          Boolean(fieldsConfig.summary_config?.add_timestamp) ||
          Boolean(jiraConfig.add_timestamp),
        description_field:
          fieldsConfig.description_config?.jira_field ||
          jiraConfig.description_field ||
          'description',
        convert_to_jira_wiki:
          Boolean(fieldsConfig.description_config?.convert_to_jira_wiki) ||
          Boolean(jiraConfig.convert_to_jira_wiki),
        assignee_use_llm:
          Boolean(fieldsConfig.assignee_config?.use_llm) ||
          Boolean(jiraConfig.assignee_use_llm),
        assignee_default:
          fieldsConfig.assignee_config?.default ||
          jiraConfig.assignee_default ||
          '',
        assignee_allow_values_text: formatMultilineList(
          fieldsConfig.assignee_config?.allow_values ||
            jiraConfig.assignee_allow_values ||
            []
        ),
        assignee_prompt:
          fieldsConfig.assignee_config?.prompt ||
          jiraConfig.assignee_prompt ||
          '',
        components_use_llm:
          Boolean(fieldsConfig.components_config?.use_llm) ||
          Boolean(jiraConfig.components_use_llm),
        components_fetch_from_api:
          fieldsConfig.components_config?.fetch_from_api !== undefined
            ? Boolean(fieldsConfig.components_config.fetch_from_api)
            : Boolean(jiraConfig.components_fetch_from_api),
        components_default_text: formatMultilineList(
          fieldsConfig.components_config?.default ||
            jiraConfig.components_default ||
            []
        ),
        components_prompt:
          fieldsConfig.components_config?.prompt ||
          jiraConfig.components_prompt ||
          '',
        epic_link_use_llm:
          Boolean(fieldsConfig.epic_link_config?.use_llm) ||
          Boolean(jiraConfig.epic_link_use_llm),
        epic_link_fetch_from_api:
          fieldsConfig.epic_link_config?.fetch_from_api !== undefined
            ? Boolean(fieldsConfig.epic_link_config.fetch_from_api)
            : Boolean(jiraConfig.epic_link_fetch_from_api),
        epic_link_default:
          fieldsConfig.epic_link_config?.default ||
          jiraConfig.epic_link_default ||
          '',
        epic_link_jql_filter:
          fieldsConfig.epic_link_config?.jql_filter ||
          jiraConfig.epic_link_jql_filter ||
          '',
        epic_link_prompt:
          fieldsConfig.epic_link_config?.prompt ||
          jiraConfig.epic_link_prompt ||
          ''
      },
      fieldMappingRows: normalizeFieldMappingRows(
        sub.field_mappings ||
          feishuConfig.field_mappings ||
          config.field_mappings ||
          {}
      )
    })
    editorMode.value = 'edit'
    editorVisible.value = false
    expandedSubscriptionId.value = String(sub.id)
    testSubscriptionId.value = String(sub.id)
    activeTab.value = 'channels'
  }

  function buildTestPayload() {
    return {
      artifact_snapshot: {
        summary_title: 'devify test summary',
        summary_content: 'devify test description',
        llm_content: 'devify test description',
        language: editorForm.language || 'Chinese'
      }
    }
  }

  async function persistEditor() {
    const isUpdate = Boolean(editorForm.id)
    const fieldMappings = buildFieldMappingsFromRows(
      editorForm.fieldMappingRows
    )
    const componentsDefault = parseMultilineList(
      editorForm.jiraConfig.components_default_text
    )
    const componentsConfig = {
      use_llm: Boolean(editorForm.jiraConfig.components_use_llm),
      fetch_from_api: Boolean(editorForm.jiraConfig.components_fetch_from_api),
      jira_field: 'components',
      default: componentsDefault,
      prompt: editorForm.jiraConfig.components_prompt || ''
    }
    const strategies = {
      auto_merge_strategy: editorForm.strategies.auto_merge_strategy || 'new',
      manual_merge_strategy:
        editorForm.strategies.manual_merge_strategy || 'linked',
      retry_issue_strategy:
        editorForm.strategies.retry_issue_strategy || 'update'
    }
    const baseConfig = {
      issue_engine: editorForm.target_type,
      enable: editorForm.enabled,
      language: editorForm.language || 'Chinese',
      ...strategies
    }
    const config =
      editorForm.target_type === 'jira'
        ? {
            ...baseConfig,
            jira: {
              url: editorForm.jiraConfig.url || '',
              username: editorForm.jiraConfig.username || '',
              api_token: editorForm.jiraConfig.api_token || '',
              project_key: editorForm.jiraConfig.project_key || '',
              issue_type_default:
                editorForm.jiraConfig.issue_type_default || 'Task',
              priority_default:
                editorForm.jiraConfig.priority_default || 'Medium',
              summary_prefix: editorForm.jiraConfig.summary_prefix || '[AI]',
              add_timestamp: Boolean(editorForm.jiraConfig.add_timestamp),
              convert_to_jira_wiki: Boolean(
                editorForm.jiraConfig.convert_to_jira_wiki
              ),
              assignee_use_llm: Boolean(editorForm.jiraConfig.assignee_use_llm),
              assignee_default: editorForm.jiraConfig.assignee_default || '',
              assignee_allow_values: parseMultilineList(
                editorForm.jiraConfig.assignee_allow_values_text
              ),
              assignee_prompt: editorForm.jiraConfig.assignee_prompt || '',
              components_use_llm: Boolean(
                editorForm.jiraConfig.components_use_llm
              ),
              components_fetch_from_api: Boolean(
                editorForm.jiraConfig.components_fetch_from_api
              ),
              components_default: parseMultilineList(
                editorForm.jiraConfig.components_default_text
              ),
              components_prompt: editorForm.jiraConfig.components_prompt || '',
              epic_link_use_llm: Boolean(
                editorForm.jiraConfig.epic_link_use_llm
              ),
              epic_link_fetch_from_api: Boolean(
                editorForm.jiraConfig.epic_link_fetch_from_api
              ),
              epic_link_default: editorForm.jiraConfig.epic_link_default || '',
              epic_link_jql_filter:
                editorForm.jiraConfig.epic_link_jql_filter || '',
              epic_link_prompt: editorForm.jiraConfig.epic_link_prompt || '',
              description_field:
                editorForm.jiraConfig.description_field || 'description'
            },
            fields: {
              project_key_config: {
                jira_field: 'project',
                default: editorForm.jiraConfig.project_key || ''
              },
              issue_type_config: {
                jira_field: 'issuetype',
                default: editorForm.jiraConfig.issue_type_default || 'Task'
              },
              priority_config: {
                jira_field: 'priority',
                default: editorForm.jiraConfig.priority_default || 'Medium'
              },
              summary_config: {
                prefix: editorForm.jiraConfig.summary_prefix || '[AI]',
                add_timestamp: Boolean(editorForm.jiraConfig.add_timestamp)
              },
              description_config: {
                jira_field:
                  editorForm.jiraConfig.description_field || 'description',
                convert_to_jira_wiki: Boolean(
                  editorForm.jiraConfig.convert_to_jira_wiki
                )
              },
              assignee_config: {
                use_llm: Boolean(editorForm.jiraConfig.assignee_use_llm),
                jira_field: 'assignee',
                default: editorForm.jiraConfig.assignee_default || '',
                allow_values: parseMultilineList(
                  editorForm.jiraConfig.assignee_allow_values_text
                ),
                prompt: editorForm.jiraConfig.assignee_prompt || ''
              },
              epic_link_config: {
                use_llm: Boolean(editorForm.jiraConfig.epic_link_use_llm),
                fetch_from_api: Boolean(
                  editorForm.jiraConfig.epic_link_fetch_from_api
                ),
                jira_field: 'customfield_10014',
                default: editorForm.jiraConfig.epic_link_default || '',
                jql_filter: editorForm.jiraConfig.epic_link_jql_filter || '',
                prompt: editorForm.jiraConfig.epic_link_prompt || ''
              },
              ...(componentsConfig.use_llm ||
              componentsConfig.fetch_from_api ||
              componentsConfig.default.length > 0 ||
              componentsConfig.prompt
                ? { components_config: componentsConfig }
                : {})
            },
            feishu_bitable: {}
          }
        : {
            ...baseConfig,
            jira: {
              url: editorForm.jiraConfig.url || '',
              username: editorForm.jiraConfig.username || '',
              api_token: editorForm.jiraConfig.api_token || ''
            },
            feishu_bitable: {
              app_token_type:
                editorForm.feishuConfig.app_token_type || 'bitable',
              app_token: editorForm.feishuConfig.app_token || '',
              table_name: editorForm.feishuConfig.table_name || '',
              app_id: editorForm.feishuConfig.app_id || '',
              app_secret: editorForm.feishuConfig.app_secret || '',
              attachment_field_name:
                editorForm.feishuConfig.attachment_field_name || '附件',
              summary_prefix: editorForm.feishuConfig.summary_prefix || '',
              field_mappings: fieldMappings
            },
            fields: {}
          }
    const payload = {
      target_type: editorForm.target_type,
      name: editorForm.name,
      enabled: editorForm.enabled,
      config,
      strategies,
      field_mappings: fieldMappings
    }
    const result = isUpdate
      ? await relayApi.updateSubscription(editorForm.id, payload)
      : await relayApi.createSubscription(payload)
    return result
  }

  async function saveEditor() {
    editorError.value = ''
    editorSuccess.value = ''
    if (!editorCanSave.value) return
    saving.value = true
    try {
      const isUpdate = Boolean(editorForm.id)
      const result = await persistEditor()
      // Update form state immediately after a successful save so the panel
      // closes correctly even if the subsequent reload fails.
      testSubscriptionId.value = String(
        result.id || testSubscriptionId.value || ''
      )
      editorForm.id = result.id || editorForm.id
      editorMode.value = 'edit'
      editorSuccess.value = isUpdate
        ? t('relay.updateSuccess')
        : t('relay.saveSuccess')
      showSuccess(editorSuccess.value)
      activeTab.value = 'channels'
      editorVisible.value = false
      if (isUpdate) expandedSubscriptionId.value = ''
      await reloadAll()
    } catch (error) {
      editorError.value = extractErrorMessage(error, t('common.error'))
      showError(editorError.value)
    } finally {
      saving.value = false
    }
  }

  async function deleteSubscription(id) {
    if (!confirm(t('relay.confirmDelete'))) return
    try {
      await relayApi.deleteSubscription(id)
      await reloadAll()
      if (String(testSubscriptionId.value) === String(id))
        testSubscriptionId.value = ''
      showSuccess(t('relay.deleteSuccess'))
    } catch (error) {
      showError(extractErrorMessage(error, t('common.error')))
    }
  }

  async function runTest(subscriptionId) {
    const targetSubscriptionId =
      subscriptionId || testSubscriptionId.value || editorForm.id
    if (!targetSubscriptionId) return null
    testing.value = true
    try {
      const data = await relayApi.testSubscription({
        subscription_id: targetSubscriptionId,
        ...buildTestPayload()
      })
      editorTestSignature.value = editorCurrentSignature.value
      showSuccess(t('relay.testSuccess'))
      return data
    } catch (error) {
      const message = extractErrorMessage(error, t('common.error'))
      showError(message)
      throw error
    } finally {
      testing.value = false
    }
  }

  async function runEditorTest() {
    try {
      if (!editorForm.id) {
        const result = await persistEditor()
        await reloadAll()
        editorForm.id = result.id || editorForm.id
        testSubscriptionId.value = String(
          result.id || testSubscriptionId.value || ''
        )
      }
      await runTest(editorForm.id || testSubscriptionId.value)
      editorMode.value = 'edit'
      activeTab.value = 'channels'
    } catch (error) {
      // runTest and persistEditor already surface the error message
    }
  }

  async function toggleSubscriptionEnabled(sub) {
    try {
      await relayApi.updateSubscription(sub.id, { enabled: !sub.enabled })
      await reloadAll()
      showSuccess(
        sub.enabled ? t('relay.disableSuccess') : t('relay.enableSuccess')
      )
    } catch (error) {
      showError(extractErrorMessage(error, t('common.error')))
    }
  }

  return {
    saving,
    testing,
    showFeishuAppSecret,
    editorVisible,
    editorMode,
    expandedSubscriptionId,
    editorError,
    editorSuccess,
    testSubscriptionId,
    editorTestSignature,
    editorForm,
    editorCurrentSignature,
    editorTestPassed,
    editorCanSave,
    setEditorForm,
    normalizeFieldMappingRows,
    formatMultilineList,
    parseMultilineList,
    buildFieldMappingsFromRows,
    addFieldMappingRow,
    removeFieldMappingRow,
    resetEditor,
    openCreatePanel,
    cancelEditor,
    editSubscription,
    buildTestPayload,
    persistEditor,
    saveEditor,
    deleteSubscription,
    runTest,
    runEditorTest,
    toggleSubscriptionEnabled
  }
}
