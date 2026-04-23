<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('llm.config.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('llm.config.subtitleList') }}
        </p>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div class="p-6">
          <div class="flex flex-wrap items-center justify-end gap-3 mb-6">
            <BaseButton
              variant="outline"
              size="sm"
              :loading="loading"
              :title="t('common.refresh')"
              class="flex items-center gap-1 shadow-sm hover:shadow-md transition-shadow"
              @click="loadAll"
            >
              <svg
                v-if="!loading"
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span class="sr-only">{{ t('common.refresh') }}</span>
            </BaseButton>
            <BaseButton
              variant="primary"
              size="sm"
              :disabled="loading || modelsLoading"
              @click="openAddModal"
            >
              {{ t('llm.config.addConfig') }}
            </BaseButton>
          </div>

          <BaseLoading v-if="loading" />
          <template v-else>
            <div
              v-if="configList.length === 0"
              class="py-16 text-center rounded-lg border border-gray-200 bg-gray-50"
            >
              <svg
                class="mx-auto h-12 w-12 text-gray-400 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p class="text-sm font-medium text-gray-600">
                {{ t('llm.config.noConfigs') }}
              </p>
            </div>

            <div
              v-else
              class="overflow-x-auto relative rounded-lg border border-gray-200 bg-white shadow-sm"
            >
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
                  <tr>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.scopeLabel') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.user') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.provider') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.model') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.apiBase') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.apiKey') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.parameters') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.capabilities') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.default') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.active') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.config.actions') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                  <tr
                    v-for="row in configList"
                    :key="row.uuid || row.id"
                    class="hover:bg-gray-50 transition-colors duration-150"
                  >
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-900"
                    >
                      {{
                        row.scope === 'global'
                          ? t('llm.config.scopeGlobal')
                          : t('llm.config.scopeUser')
                      }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{
                        row.scope === 'user'
                          ? row.username || row.user_id || '–'
                          : '–'
                      }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-900"
                    >
                      <ProviderIcon :provider="row.provider" size="sm">
                        <span class="text-gray-900">{{
                          providerLabel(row.provider)
                        }}</span>
                      </ProviderIcon>
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-700"
                    >
                      {{ getEffectiveRowConfig(row).model || '–' }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-700"
                    >
                      {{ getEffectiveRowConfig(row).api_base || '–' }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-700"
                    >
                      {{ maskApiKey(row.config?.api_key || row.config?.key) }}
                    </td>
                    <td class="px-4 py-4 text-sm">
                      <div class="flex flex-col gap-1">
                        <span
                          class="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                        >
                          {{ t('llm.config.temperature') }}:
                          {{
                            formatDefaultValue(
                              getEffectiveRowConfig(row).temperature
                            )
                          }}
                        </span>
                        <span
                          class="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                        >
                          {{ t('llm.config.topP') }}:
                          {{
                            formatDefaultValue(getEffectiveRowConfig(row).top_p)
                          }}
                        </span>
                        <span
                          class="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                        >
                          {{ t('llm.config.maxOutputTokens') }}:
                          {{
                            formatDefaultValue(
                              getEffectiveRowConfig(row).max_tokens
                            )
                          }}
                        </span>
                      </div>
                    </td>
                    <td class="px-4 py-4 text-sm">
                      <span
                        v-if="getRowCapabilities(row).length"
                        class="flex flex-wrap gap-1"
                      >
                        <span
                          v-for="cap in getRowCapabilities(row)"
                          :key="cap"
                          class="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                        >
                          {{ capabilityLabel(cap) }}
                        </span>
                      </span>
                      <span v-else class="text-gray-400">–</span>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-sm">
                      <span
                        v-if="row.is_default"
                        class="inline-flex items-center text-primary-600"
                        :title="t('llm.config.testUseDefault')"
                      >
                        <svg
                          class="h-5 w-5"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                          aria-hidden="true"
                        >
                          <path
                            fill-rule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clip-rule="evenodd"
                          />
                        </svg>
                      </span>
                      <button
                        v-else-if="row.scope === 'global'"
                        type="button"
                        class="inline-flex items-center rounded p-1 text-gray-400 hover:bg-primary-50 hover:text-primary-600"
                        :title="t('llm.config.setAsDefault')"
                        @click="setAsDefault(row)"
                      >
                        <svg
                          class="h-5 w-5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                          />
                        </svg>
                      </button>
                      <span v-else class="text-gray-300">–</span>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-sm">
                      <span
                        v-if="row.is_active"
                        class="inline-flex items-center text-green-600"
                        :title="t('common.yes')"
                      >
                        <svg
                          class="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </span>
                      <span
                        v-else
                        class="inline-flex items-center text-gray-400"
                        :title="t('common.no')"
                      >
                        <svg
                          class="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M15 12H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </span>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-right">
                      <div class="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          :title="t('llm.config.testCall')"
                          class="inline-flex items-center justify-center rounded p-1.5 text-gray-500 hover:bg-sky-50 hover:text-sky-600"
                          @click="openTestModal(row)"
                        >
                          <svg
                            class="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M8 8h8"
                            />
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M12 8v8"
                            />
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                          </svg>
                        </button>
                        <button
                          type="button"
                          :title="
                            row.is_active
                              ? t('llm.config.disable')
                              : t('llm.config.enable')
                          "
                          :class="
                            row.is_active
                              ? 'inline-flex items-center justify-center rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600'
                              : 'inline-flex items-center justify-center rounded p-1.5 text-gray-500 hover:bg-green-50 hover:text-green-600'
                          "
                          @click="setActive(row, !row.is_active)"
                        >
                          <svg
                            v-if="row.is_active"
                            class="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M5.636 5.636a9 9 0 1012.728 0M12 3v9"
                            />
                          </svg>
                          <svg
                            v-else
                            class="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        </button>
                        <button
                          type="button"
                          :title="t('common.edit')"
                          class="inline-flex items-center justify-center rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                          @click="editConfig(row)"
                        >
                          <svg
                            class="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                            />
                          </svg>
                        </button>
                        <button
                          type="button"
                          :title="t('common.delete')"
                          class="inline-flex items-center justify-center rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600"
                          @click="deleteConfig(row)"
                        >
                          <svg
                            class="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
      </div>

      <BaseModal
        :show="showTestModal"
        :title="testModalTitle"
        @close="closeTestModal"
      >
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ t('llm.config.testPromptLabel') }}
            </label>
            <textarea
              v-model="testPrompt"
              rows="4"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              :placeholder="t('llm.config.testPromptPlaceholder')"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ t('llm.config.maxOutputTokens') }} (max_tokens)
            </label>
            <input
              v-model.number="testMaxTokens"
              type="number"
              min="1"
              max="4096"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div class="flex flex-col gap-1 pt-1">
            <div class="flex items-center gap-2 min-h-[1.5rem]">
              <input
                id="test-streaming"
                v-model="testStreaming"
                type="checkbox"
                class="h-4 w-4 shrink-0 rounded border-2 border-gray-400 text-primary-600 focus:ring-2 focus:ring-primary-500 cursor-pointer"
              />
              <label
                for="test-streaming"
                class="text-sm font-medium text-gray-700 cursor-pointer select-none"
              >
                {{
                  t('llm.config.streamingOutput') ===
                  'llm.config.streamingOutput'
                    ? '流式输出'
                    : t('llm.config.streamingOutput')
                }}
              </label>
            </div>
            <p class="text-xs text-gray-500">
              {{
                t('llm.config.streamingParamHint') ===
                'llm.config.streamingParamHint'
                  ? '请求参数 stream：控制是否以 SSE 流式返回'
                  : t('llm.config.streamingParamHint')
              }}
            </p>
          </div>
          <div class="flex justify-end gap-2">
            <BaseButton
              v-if="testCallLoading && testStreaming"
              type="button"
              variant="outline"
              class="border-red-300 text-red-700 hover:bg-red-50"
              :disabled="!testCallAbortController"
              @click="stopTestCallStream"
            >
              {{
                t('llm.config.streamStop') === 'llm.config.streamStop'
                  ? '停止'
                  : t('llm.config.streamStop')
              }}
            </BaseButton>
            <BaseButton type="button" variant="outline" @click="closeTestModal">
              {{ t('common.cancel') }}
            </BaseButton>
            <BaseButton
              type="button"
              variant="primary"
              :loading="testCallLoading"
              :disabled="!testPrompt.trim()"
              @click="sendTestCall"
            >
              {{ t('llm.config.testSend') }}
            </BaseButton>
          </div>
          <div
            v-if="testCallResult !== null || (testCallLoading && testStreaming)"
            class="rounded-lg border p-4"
            :class="
              testCallLoading && testStreaming
                ? 'border-gray-200 bg-gray-50'
                : testCallOk
                  ? 'border-green-200 bg-green-50'
                  : 'border-red-200 bg-red-50'
            "
          >
            <div
              v-if="testCallLoading && testStreaming"
              class="flex items-center gap-2 mb-2"
            >
              <svg
                class="animate-spin h-4 w-4 text-gray-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
            <p v-else class="text-sm font-medium text-gray-700 mb-2">
              {{
                testCallOk
                  ? t('llm.config.testResponse')
                  : t('llm.config.testError')
              }}
            </p>
            <div
              v-if="
                (testCallLoading && testStreaming && streamingThinking) ||
                (testCallResult && (testCallResult.thinking || '').trim())
              "
              class="mb-3 rounded-lg border border-amber-200 bg-amber-50/80"
            >
              <div
                class="flex items-center gap-2 px-3 py-2 border-b border-amber-200 bg-amber-100/60"
              >
                <span
                  class="text-xs font-semibold uppercase tracking-wide text-amber-800"
                >
                  {{
                    t('llm.config.thinkingBlock') === 'llm.config.thinkingBlock'
                      ? '思考过程'
                      : t('llm.config.thinkingBlock')
                  }}
                </span>
              </div>
              <p
                class="px-3 py-2 text-xs text-amber-900/90 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-48 overflow-y-auto"
              >
                {{
                  testCallLoading && testStreaming
                    ? streamingThinking
                    : testCallResult && testCallResult.thinking
                }}
              </p>
            </div>
            <div
              v-if="testCallOk || (testCallLoading && testStreaming)"
              class="test-call-markdown text-sm text-gray-800 overflow-x-auto"
            >
              <MarkdownRenderer
                :content="markdownContentForTest"
                :enable-highlight="true"
              />
            </div>
            <p v-else class="text-sm text-red-700">
              {{ testCallDetail }}
            </p>
            <div
              v-if="testCallOk && testCallUsage"
              class="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600"
            >
              <span class="font-medium">{{ t('llm.config.testUsage') }}:</span>
              {{ testCallUsage.prompt_tokens }} in /
              {{ testCallUsage.completion_tokens }} out /
              {{ testCallUsage.total_tokens }} total
              <span v-if="testCallUsage.cost != null">
                · {{ testCallUsage.cost_currency || 'USD' }}
                {{ testCallUsage.cost }}
              </span>
            </div>
            <div
              v-if="testCallResult && testCallResult.streaming !== undefined"
              class="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-600"
            >
              <span class="font-medium"
                >{{ t('llm.config.streamingReturn') || '返回方式' }}:</span
              >
              {{
                testCallResult.streaming
                  ? t('llm.config.streamingMode') || '流式'
                  : t('llm.config.nonStreamingMode') || '非流式'
              }}
              <span v-if="testCallResult.stopped" class="ml-2 text-amber-600">
                ({{
                  t('llm.config.streamStopped') === 'llm.config.streamStopped'
                    ? '已停止'
                    : t('llm.config.streamStopped')
                }})
              </span>
            </div>
          </div>
        </div>
      </BaseModal>

      <BaseModal
        :show="showConfigModal"
        :title="editingId ? t('common.edit') : t('llm.config.addConfig')"
        @close="closeConfigModal"
      >
        <form @submit.prevent="submitConfigForm" class="space-y-4">
          <div v-if="!editingId">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('llm.config.scopeLabel')
            }}</label>
            <select
              v-model="form.scope"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="global">{{ t('llm.config.scopeGlobal') }}</option>
              <option value="user">{{ t('llm.config.scopeUser') }}</option>
            </select>
          </div>
          <div v-if="!editingId && form.scope === 'user'">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('llm.config.user')
            }}</label>
            <select
              v-model="form.user_id"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              :required="userList.length > 0"
            >
              <option value="">{{ t('llm.config.user') }}…</option>
              <option v-for="u in userList" :key="u.id" :value="u.id">
                {{ u.username || u.id }}
              </option>
            </select>
            <p v-if="userList.length === 0" class="mt-1 text-sm text-amber-600">
              {{ t('llm.config.noUsersHint') }}
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('llm.config.provider')
            }}</label>
            <div
              class="flex items-center gap-2 rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm"
            >
              <ProviderIcon :provider="form.provider" size="sm" />
              <select
                v-model="form.provider"
                class="min-w-0 flex-1 border-0 bg-transparent p-0 focus:ring-0"
                @change="onProviderChange"
              >
                <option
                  v-for="p in providersFromModels"
                  :key="p.id"
                  :value="p.id"
                >
                  {{ p.label }}
                </option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('llm.config.model')
            }}</label>
            <div class="relative" ref="modelDropdownRef">
              <button
                type="button"
                class="w-full flex items-center justify-between gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-left text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @click="modelDropdownOpen = !modelDropdownOpen"
              >
                <span class="truncate text-gray-900">{{
                  modelSelectTriggerLabel
                }}</span>
                <svg
                  class="h-4 w-4 shrink-0 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
              <div
                v-show="modelDropdownOpen"
                class="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded-md border border-gray-200 bg-white py-1 shadow-lg"
              >
                <button
                  v-for="m in currentProviderModels"
                  :key="m.id"
                  type="button"
                  class="w-full px-3 py-2 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none"
                  :class="{ 'bg-primary-50': form.config.model === m.id }"
                  @click="selectModel(m.id)"
                >
                  <div class="font-medium text-gray-900">{{ m.label }}</div>
                  <div
                    v-if="(m.capabilities || []).length"
                    class="mt-1 flex flex-wrap gap-1"
                  >
                    <span
                      v-for="cap in m.capabilities || []"
                      :key="cap"
                      class="inline-flex rounded px-1.5 py-0.5 text-xs font-medium"
                      :class="capabilityTagClass(cap)"
                    >
                      {{ capabilityLabel(cap) }}
                    </span>
                  </div>
                  <div
                    v-if="refPriceLine(m.reference_pricing)"
                    class="mt-1 text-xs text-gray-500"
                  >
                    {{ refPriceLine(m.reference_pricing) }}
                  </div>
                </button>
                <div class="border-t border-gray-100" />
                <button
                  type="button"
                  class="w-full px-3 py-2 text-left font-medium text-gray-600 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none"
                  :class="{ 'bg-primary-50': isCustomModel }"
                  @click="selectModel('__custom__')"
                >
                  {{ t('llm.config.modelCustom') }}
                </button>
              </div>
            </div>
            <div v-if="isCustomModel" class="mt-2">
              <input
                v-model="form.config.model"
                type="text"
                class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                :placeholder="t('llm.config.modelPlaceholder')"
                @focus="modelDropdownOpen = false"
              />
            </div>
          </div>
          <div
            v-if="selectedModelInfo"
            class="rounded-lg border border-gray-200 bg-gray-50 p-3"
          >
            <p class="text-xs font-medium text-gray-600 mb-2">
              {{ t('llm.config.capabilities') }}
            </p>
            <div class="flex flex-wrap gap-1 mb-2">
              <span
                v-for="cap in selectedModelInfo.capabilities"
                :key="cap"
                class="inline-flex items-center rounded-md bg-primary-50 px-2 py-0.5 text-xs text-primary-800"
              >
                {{ capabilityLabel(cap) }}
              </span>
            </div>
            <div
              v-if="
                selectedModelInfo.max_input_tokens ||
                selectedModelInfo.max_output_tokens
              "
              class="flex flex-wrap gap-3 text-xs text-gray-600"
            >
              <span v-if="selectedModelInfo.max_input_tokens">
                {{ t('llm.config.maxInputTokens') }}:
                {{ selectedModelInfo.max_input_tokens.toLocaleString() }}
              </span>
              <span v-if="selectedModelInfo.max_output_tokens">
                {{ t('llm.config.maxOutputTokens') }}:
                {{ selectedModelInfo.max_output_tokens.toLocaleString() }}
              </span>
            </div>
            <div
              v-if="refPriceLine(selectedModelInfo.reference_pricing)"
              class="mt-2 text-xs text-gray-600"
            >
              <span class="font-medium text-gray-700">{{
                t('llm.config.referencePrice')
              }}</span>
              {{ refPriceLine(selectedModelInfo.reference_pricing) }}
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('llm.config.apiBase')
            }}</label>
            <input
              v-model="form.config.api_base"
              type="url"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              :placeholder="defaultApiBasePlaceholder"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('llm.config.apiKey')
            }}</label>
            <input
              v-model="form.config.api_key"
              type="password"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              :placeholder="t('llm.config.apiKeyPlaceholder')"
            />
          </div>

          <div class="rounded-xl border border-gray-200 bg-gray-50/80 p-4">
            <h3
              class="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-700"
            >
              <svg
                class="h-4 w-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                />
              </svg>
              {{ t('llm.config.advancedOptions') }}
            </h3>
            <div class="space-y-3">
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1"
                    >{{ t('llm.config.maxOutputTokens') }} (max_tokens)</label
                  >
                  <input
                    v-model.number="form.config.max_tokens"
                    type="number"
                    min="1"
                    class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    placeholder="optional"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1">{{
                    t('llm.config.temperature')
                  }}</label>
                  <input
                    v-model.number="form.config.temperature"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1">{{
                    t('llm.config.topP')
                  }}</label>
                  <input
                    v-model.number="form.config.top_p"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>
              <template v-if="form.provider === 'azure_openai'">
                <div
                  class="grid grid-cols-2 gap-3 border-t border-gray-200 pt-3"
                >
                  <div>
                    <label
                      class="block text-xs font-medium text-gray-600 mb-1"
                      >{{ t('llm.config.deployment') }}</label
                    >
                    <input
                      v-model="form.config.deployment"
                      type="text"
                      class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-gray-600 mb-1"
                      >{{ t('llm.config.apiVersion') }}</label
                    >
                    <input
                      v-model="form.config.api_version"
                      type="text"
                      class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                </div>
              </template>
            </div>
          </div>

          <div
            v-if="formMessage"
            :class="
              formMessageSuccess
                ? 'text-green-600 text-sm'
                : 'text-red-600 text-sm'
            "
          >
            {{ formMessage }}
          </div>
          <div
            v-if="formRawMessage && !formMessageSuccess"
            class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
          >
            <div class="mb-1 font-medium">{{ t('llm.config.rawError') }}</div>
            <div class="whitespace-pre-wrap break-words font-mono">
              {{ formRawMessage }}
            </div>
          </div>
          <div class="flex flex-wrap items-center justify-end gap-3">
            <BaseButton
              type="button"
              variant="outline"
              :loading="testLoading"
              @click="testConnection"
            >
              {{ t('llm.config.testConnection') }}
            </BaseButton>
            <BaseButton
              type="button"
              variant="outline"
              @click="closeConfigModal"
            >
              {{ t('common.cancel') }}
            </BaseButton>
            <BaseButton
              type="submit"
              variant="primary"
              :loading="formSaving"
              :disabled="submitDisabled"
            >
              {{ editingId ? t('common.save') : t('llm.config.addConfig') }}
            </BaseButton>
          </div>
        </form>
      </BaseModal>
    </div>
  </AdminLayout>
</template>

<script setup>
/**
 * LLM Configuration: Provider -> Model selection with capability tags.
 * API Base URL below model selection; defaults to official URL for the provider.
 */
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { llmAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import ProviderIcon from '@/components/llm/ProviderIcon.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import MarkdownRenderer from '@/components/ui/MarkdownRenderer.vue'

const PROVIDER_LABELS = {
  openai: 'OpenAI',
  openai_compatible: 'OpenAI Compatible',
  azure_openai: 'Azure OpenAI',
  azure: 'Azure OpenAI',
  gemini: 'Google Gemini',
  google: 'Google Gemini',
  anthropic: 'Anthropic',
  claude: 'Anthropic',
  mistral: 'Mistral',
  dashscope: 'Dashscope (Qwen)',
  qwen: 'Dashscope (Qwen)',
  deepseek: 'DeepSeek',
  xai: 'xAI (Grok)',
  grok: 'xAI (Grok)',
  minimax: 'MiniMax',
  moonshot: 'Moonshot (Kimi)',
  zai: 'Z.AI (GLM)',
  zhipu: 'Z.AI (GLM)',
  volcengine: 'Volcengine (Doubao)',
  openrouter: 'OpenRouter',
  ollama: 'Ollama',
  bedrock: 'AWS Bedrock'
}

function normalizeProviderKey(provider) {
  return String(provider || '')
    .trim()
    .toLowerCase()
}

function providerLabel(provider) {
  const key = normalizeProviderKey(provider)
  return PROVIDER_LABELS[key] || provider || '–'
}

function maskApiKey(value) {
  if (!value || typeof value !== 'string') return '–'
  const key = value.trim()
  if (!key) return '–'
  if (key.includes('***')) return key
  if (key.length <= 8) return '***'
  return `${key.slice(0, 4)}***${key.slice(-4)}`
}

const { t } = useI18n()

const loading = ref(true)
const modelsLoading = ref(true)
const configList = ref([])
const userList = ref([])
const modelsData = ref({ providers: [], capability_labels: {} })
const providerSchemaData = ref({ providers: {} })

const showConfigModal = ref(false)
const showTestModal = ref(false)
const testConfigRow = ref(null)
const testPrompt = ref('')
const testMaxTokens = ref(2048)
const testCallLoading = ref(false)
const testCallResult = ref(null)
const testStreaming = ref(true)
const streamingContent = ref('')
const streamingThinking = ref('')
const testCallAbortController = ref(null)
const editingId = ref(null)
const formSaving = ref(false)
const testLoading = ref(false)
const formMessage = ref('')
const formRawMessage = ref('')
const formMessageSuccess = ref(false)
const connectionTestedSuccess = ref(false)
const modelDropdownOpen = ref(false)
const modelDropdownRef = ref(null)

const form = reactive({
  scope: 'global',
  user_id: null,
  provider: 'openai',
  config: {
    api_key: '',
    api_base: '',
    model: '',
    deployment: '',
    api_version: '2024-02-15-preview',
    max_tokens: null,
    temperature: null,
    top_p: null
  },
  is_active: true
})

const providersFromModels = computed(() => {
  return (modelsData.value?.providers || []).map((p) => ({
    id: p.id,
    label: providerLabel(p.id) || p.label
  }))
})

const currentProviderModels = computed(() => {
  const list = (modelsData.value?.providers || []).find(
    (p) => (p.id || '').toLowerCase() === (form.provider || '').toLowerCase()
  )
  return list?.models || []
})

const currentProviderSchema = computed(() => {
  const providerKey = (form.provider || '').toLowerCase()
  return providerSchemaData.value?.providers?.[providerKey] || {}
})

const defaultApiBaseForProvider = computed(() => {
  return currentProviderSchema.value?.default_api_base || ''
})

const defaultApiBasePlaceholder = computed(() => {
  return defaultApiBaseForProvider.value || t('llm.config.apiBasePlaceholder')
})

const isCurrentModelInList = computed(() => {
  const id = (form.config.model || '').trim()
  if (!id) return false
  return currentProviderModels.value.some((m) => (m.id || '').trim() === id)
})

const isCustomModel = computed(() => {
  const list = currentProviderModels.value
  if (list.length === 0) return true
  return !isCurrentModelInList.value
})

const modelSelectTriggerLabel = computed(() => {
  if (isCustomModel.value) {
    return form.config.model
      ? `${t('llm.config.modelCustom')} ${form.config.model}`
      : t('llm.config.modelCustom')
  }
  const m = currentProviderModels.value.find(
    (x) => (x.id || '').trim() === (form.config.model || '').trim()
  )
  return m ? m.label : t('llm.config.modelSelect')
})

const submitDisabled = computed(() => {
  if (
    !editingId.value &&
    form.scope === 'user' &&
    userList.value.length === 0
  ) {
    return true
  }
  if (!editingId.value && !connectionTestedSuccess.value) {
    return true
  }
  return false
})

const testModalTitle = computed(() => {
  const row = testConfigRow.value
  if (!row) return t('llm.config.testCall')
  const prov = providerLabel(row.provider)
  const model = getEffectiveRowConfig(row).model || '–'
  return `${t('llm.config.testCall')} · ${prov} / ${model}`
})

const testCallOk = computed(() => testCallResult.value?.ok === true)
const testCallContent = computed(() => testCallResult.value?.content ?? '')
const testCallDetail = computed(() => testCallResult.value?.detail ?? '')
const testCallUsage = computed(() => testCallResult.value?.usage ?? null)

function unwrapMarkdownIfCodeBlock(raw) {
  if (typeof raw !== 'string' || !raw.trim()) return raw
  const trimmed = raw.trim()
  const openMatch = trimmed.match(/^```(?:markdown|md)?\s*\n?/i)
  const closeMatch = trimmed.match(/\n?```\s*$/)
  if (
    openMatch &&
    closeMatch &&
    trimmed.length > openMatch[0].length + closeMatch[0].length
  ) {
    return trimmed
      .slice(openMatch[0].length, trimmed.length - closeMatch[0].length)
      .trim()
  }
  return raw
}

const markdownContentForTest = computed(() => {
  const src =
    testCallLoading.value && testStreaming.value
      ? streamingContent.value
      : testCallContent.value
  return unwrapMarkdownIfCodeBlock(src || '')
})

const selectedModelInfo = computed(() => {
  const modelId = (form.config.model || '').trim()
  if (!modelId) return null
  const m = currentProviderModels.value.find(
    (x) => (x.id || '').trim() === modelId
  )
  if (!m) return null
  return {
    capabilities: m.capabilities || [],
    max_input_tokens: m.max_input_tokens,
    max_output_tokens: m.max_output_tokens,
    reference_pricing: m.reference_pricing || null
  }
})

function capabilityLabel(capKey) {
  const labels = modelsData.value?.capability_labels || {}
  return labels[capKey] || capKey
}

const CAP_TAG_CLASSES = {
  'text-to-text': 'bg-sky-100 text-sky-800',
  code: 'bg-emerald-100 text-emerald-800',
  vision: 'bg-violet-100 text-violet-800',
  multimodal: 'bg-indigo-100 text-indigo-800',
  'text-to-image': 'bg-amber-100 text-amber-800',
  'long-context': 'bg-orange-100 text-orange-800',
  'low-cost': 'bg-slate-100 text-slate-600',
  embedding: 'bg-teal-100 text-teal-800',
  reasoning: 'bg-rose-100 text-rose-800'
}

function capabilityTagClass(capKey) {
  return CAP_TAG_CLASSES[capKey] || 'bg-gray-100 text-gray-700'
}

function formatRefPrice(num) {
  if (num == null || typeof num !== 'number') return '–'
  return num % 1 === 0 ? String(num) : num.toFixed(2)
}

function refPriceLine(rp) {
  if (!rp || (rp.input_usd_per_1m == null && rp.output_usd_per_1m == null))
    return ''
  const inStr =
    rp.input_usd_per_1m != null
      ? `$${formatRefPrice(rp.input_usd_per_1m)}/1M in`
      : ''
  const outStr =
    rp.output_usd_per_1m != null
      ? `$${formatRefPrice(rp.output_usd_per_1m)}/1M out`
      : ''
  return [inStr, outStr].filter(Boolean).join(' · ')
}

function formatDefaultValue(value) {
  if (value === 0) return '0'
  if (value === null || value === undefined || value === '') return '–'
  return String(value)
}

function isMaskedSecretValue(value) {
  return typeof value === 'string' && value.includes('***')
}

function buildProviderDefaultConfig(provider) {
  const schema =
    providerSchemaData.value?.providers?.[(provider || '').toLowerCase()] || {}
  return {
    api_key: '',
    api_base: schema.default_api_base || '',
    model: schema.default_model || '',
    deployment: '',
    api_version: '2024-02-15-preview',
    max_tokens: schema.default_max_tokens ?? null,
    temperature: schema.default_temperature ?? null,
    top_p: schema.default_top_p ?? null
  }
}

function getEffectiveRowConfig(row) {
  const schema =
    providerSchemaData.value?.providers?.[
      (row?.provider || '').toLowerCase()
    ] || {}
  const config = row?.config || {}
  return {
    api_base: config.api_base || schema.default_api_base || '',
    model: config.model || schema.default_model || '',
    max_tokens: config.max_tokens ?? schema.default_max_tokens ?? null,
    temperature: config.temperature ?? schema.default_temperature ?? null,
    top_p: config.top_p ?? schema.default_top_p ?? null
  }
}

function buildConfigPayloadFrom(config) {
  const payload = {
    api_base: config?.api_base || undefined,
    model: config?.model || undefined,
    deployment: config?.deployment || undefined,
    api_version: config?.api_version || undefined,
    max_tokens: config?.max_tokens ?? undefined,
    temperature: config?.temperature ?? undefined,
    top_p: config?.top_p ?? undefined
  }
  const apiKey = (config?.api_key || config?.key || '').trim()
  if (apiKey && !isMaskedSecretValue(apiKey)) {
    payload.api_key = apiKey
  }
  return payload
}

function buildConfigPayload() {
  return buildConfigPayloadFrom(form.config)
}

function selectModel(modelId) {
  if (modelId === '__custom__') {
    form.config.model = ''
  } else {
    form.config.model = modelId
  }
  modelDropdownOpen.value = false
}

function closeModelDropdown(e) {
  const el = modelDropdownRef.value
  if (el && e.target && !el.contains(e.target)) {
    modelDropdownOpen.value = false
  }
}

watch(modelDropdownOpen, (open) => {
  if (open) {
    nextTick(() => document.addEventListener('click', closeModelDropdown))
  } else {
    document.removeEventListener('click', closeModelDropdown)
  }
})

function getRowCapabilities(row) {
  const provider = (row.provider || '').toLowerCase()
  const modelId = (getEffectiveRowConfig(row).model || '').trim()
  if (!modelId) return []
  const prov = (modelsData.value?.providers || []).find(
    (p) => (p.id || '').toLowerCase() === provider
  )
  const model = prov?.models?.find((m) => (m.id || '').trim() === modelId)
  return model?.capabilities || []
}

function onProviderChange() {
  form.config = buildProviderDefaultConfig(form.provider)
  connectionTestedSuccess.value = false
}

function resetForm() {
  form.scope = 'global'
  form.user_id = null
  form.provider = 'openai'
  form.config = buildProviderDefaultConfig(form.provider)
  form.is_active = true
  formMessage.value = ''
  formRawMessage.value = ''
  formMessageSuccess.value = false
  connectionTestedSuccess.value = false
}

async function loadModels() {
  modelsLoading.value = true
  try {
    const [models, schema] = await Promise.all([
      llmAdminApi.getLLMConfigModels(),
      llmAdminApi.getLLMConfigProviders()
    ])
    modelsData.value = {
      providers: models?.providers || [],
      capability_labels: models?.capability_labels || {}
    }
    providerSchemaData.value = {
      providers: schema?.providers || {}
    }
  } catch (e) {
    if (e?.response?.status !== 404) console.error(e)
    modelsData.value = { providers: [], capability_labels: {} }
    providerSchemaData.value = { providers: {} }
  } finally {
    modelsLoading.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    const data = await llmAdminApi.getLLMConfigAll()
    configList.value = Array.isArray(data) ? data : []
  } catch (e) {
    if (e?.response?.status !== 404) console.error(e)
    configList.value = []
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  try {
    const data = await llmAdminApi.getUsers()
    userList.value = Array.isArray(data) ? data : []
  } catch {
    userList.value = []
  }
}

function openAddModal() {
  if (modelsLoading.value) {
    return
  }
  editingId.value = null
  resetForm()
  form.config = buildProviderDefaultConfig(form.provider)
  loadUsers()
  showConfigModal.value = true
}

async function editConfig(row) {
  editingId.value = row.uuid || row.id
  try {
    const data = await llmAdminApi.getLLMConfigDetail(row.uuid || row.id)
    form.provider = (data?.provider || 'openai').toLowerCase()
    const c = data?.config || {}
    form.config = {
      api_key: isMaskedSecretValue(c.api_key || c.key) ? '' : (c.api_key ?? ''),
      api_base: c.api_base ?? '',
      model: c.model ?? '',
      deployment: c.deployment ?? '',
      api_version: c.api_version ?? '2024-02-15-preview',
      max_tokens: c.max_tokens ?? null,
      temperature: c.temperature ?? null,
      top_p: c.top_p ?? null
    }
    form.is_active = data?.is_active !== false
  } catch (e) {
    formMessage.value =
      e?.response?.data?.detail || e?.message || 'Failed to load'
    formMessageSuccess.value = false
  }
  showConfigModal.value = true
}

function closeConfigModal() {
  showConfigModal.value = false
  editingId.value = null
  resetForm()
}

function openTestModal(row) {
  testConfigRow.value = row
  testPrompt.value = ''
  testMaxTokens.value = 2048
  testCallResult.value = null
  streamingContent.value = ''
  showTestModal.value = true
}

function closeTestModal() {
  showTestModal.value = false
  testConfigRow.value = null
  testPrompt.value = ''
  testMaxTokens.value = 2048
  testCallResult.value = null
  streamingContent.value = ''
}

async function sendTestCall() {
  const row = testConfigRow.value
  if (!(row?.uuid || row?.id) || !testPrompt.value.trim()) return
  const boundedMaxTokens = Math.min(
    4096,
    Math.max(1, Number(testMaxTokens.value) || 2048)
  )
  testCallLoading.value = true
  testCallResult.value = null
  streamingContent.value = ''
  streamingThinking.value = ''
  testCallAbortController.value = null
  const body = {
    prompt: testPrompt.value.trim(),
    max_tokens: boundedMaxTokens,
    config_uuid: row.uuid || row.id
  }
  try {
    if (testStreaming.value) {
      const controller = new AbortController()
      testCallAbortController.value = controller
      await llmAdminApi.postLLMConfigTestCallStream(
        body,
        {
          onChunk(content) {
            streamingContent.value += content
          },
          onReasoning(content) {
            streamingThinking.value += content
          },
          onDone(usage) {
            testCallResult.value = {
              ok: true,
              content: streamingContent.value,
              usage,
              streaming: true,
              thinking: streamingThinking.value
            }
            testCallLoading.value = false
            testCallAbortController.value = null
          },
          onError(detail) {
            if (detail === 'aborted') {
              testCallResult.value = {
                ok: true,
                content: streamingContent.value,
                streaming: true,
                stopped: true,
                thinking: streamingThinking.value
              }
            } else {
              testCallResult.value = {
                ok: false,
                detail: detail || t('llm.config.testFailed'),
                streaming: true
              }
            }
            testCallLoading.value = false
            testCallAbortController.value = null
          }
        },
        controller.signal
      )
      if (testCallResult.value === null) {
        testCallLoading.value = false
        testCallAbortController.value = null
      }
    } else {
      const res = await llmAdminApi.postLLMConfigTestCall(body)
      testCallResult.value =
        res && typeof res === 'object' && !Array.isArray(res)
          ? { ...res, streaming: false }
          : res
    }
  } catch (e) {
    if (e?.name === 'AbortError') {
      testCallResult.value = {
        ok: true,
        content: streamingContent.value,
        streaming: true,
        stopped: true,
        thinking: streamingThinking.value
      }
    } else {
      testCallResult.value = {
        ok: false,
        detail:
          e?.response?.data?.detail ||
          e?.detail ||
          e?.message ||
          t('llm.config.testFailed'),
        streaming: testStreaming.value
      }
    }
  } finally {
    testCallLoading.value = false
    testCallAbortController.value = null
  }
}

function stopTestCallStream() {
  if (testCallAbortController.value) {
    testCallAbortController.value.abort()
  }
}

async function testConnection() {
  testLoading.value = true
  formMessage.value = ''
  formRawMessage.value = ''
  try {
    const payload = {
      provider: form.provider,
      config: buildConfigPayload()
    }
    const res = await llmAdminApi.postLLMConfigTest(payload)
    if (res?.ok) {
      formMessage.value = t('llm.config.testSuccess')
      formMessageSuccess.value = true
      connectionTestedSuccess.value = true
    } else {
      formMessage.value = res?.detail || t('llm.config.testFailed')
      formRawMessage.value = res?.raw_detail || ''
      formMessageSuccess.value = false
    }
  } catch (e) {
    formMessage.value =
      e?.response?.data?.detail || e?.message || t('llm.config.testFailed')
    formRawMessage.value = e?.response?.data?.raw_detail || e?.detail || ''
    formMessageSuccess.value = false
  } finally {
    testLoading.value = false
  }
}

async function submitConfigForm() {
  if (!editingId.value && form.scope === 'user' && !form.user_id) {
    formMessage.value = t('llm.config.user') + '?'
    formMessageSuccess.value = false
    return
  }
  formSaving.value = true
  formMessage.value = ''
  formRawMessage.value = ''
  try {
    const body = {
      provider: form.provider,
      config: buildConfigPayload(),
      is_active: form.is_active
    }
    if (editingId.value) {
      await llmAdminApi.putLLMConfigDetail(editingId.value, body)
    } else {
      if (form.scope === 'user' && form.user_id) {
        body.scope = 'user'
        body.user_id = form.user_id
      }
      await llmAdminApi.postLLMConfig(body)
    }
    formMessage.value = t('llm.config.saveSuccess')
    formMessageSuccess.value = true
    closeConfigModal()
    await loadAll()
  } catch (e) {
    formMessage.value =
      e?.response?.data?.detail || e?.message || t('llm.config.saveError')
    formMessageSuccess.value = false
  } finally {
    formSaving.value = false
  }
}

async function setActive(row, value) {
  if (!(row?.uuid || row?.id)) return
  try {
    await llmAdminApi.putLLMConfigDetail(row.uuid || row.id, {
      is_active: value
    })
    await loadAll()
  } catch (e) {
    console.error(e)
  }
}

async function setAsDefault(row) {
  if (!(row?.uuid || row?.id) || row.scope !== 'global') return
  try {
    const data = await llmAdminApi.getLLMConfigDetail(row.uuid || row.id)
    const body = {
      provider: (data?.provider || row.provider || 'openai').toLowerCase(),
      config: buildConfigPayloadFrom(data?.config || {}),
      is_active: data?.is_active !== false,
      is_default: true
    }
    await llmAdminApi.putLLMConfigDetail(row.uuid || row.id, body)
    await loadAll()
  } catch (e) {
    console.error(e)
  }
}

async function deleteConfig(row) {
  if (!(row?.uuid || row?.id) || !confirm(t('llm.config.confirmDeleteConfig')))
    return
  try {
    await llmAdminApi.deleteLLMConfigDetail(row.uuid || row.id)
    await loadAll()
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadModels()
  loadAll()
})
</script>

<style scoped>
.test-call-markdown {
  max-height: 28rem;
  overflow-y: auto;
}
.test-call-markdown :deep(.markdown-content) {
  @apply text-gray-800;
}
.test-call-markdown :deep(.markdown-content pre) {
  @apply text-xs;
}
</style>
