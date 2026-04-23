<template>
  <div class="min-h-screen bg-gray-50">
    <ShareHeader />
    <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <div class="mx-auto max-w-4xl space-y-6">
        <BaseCard
          v-if="loading"
          class="bg-gradient-to-b from-white via-white to-primary-50/40 border border-primary-100 shadow-sm"
        >
          <div class="flex flex-col items-center gap-4 py-8 text-center">
            <div class="relative">
              <div
                class="h-12 w-12 rounded-full bg-primary-50 flex items-center justify-center text-primary-600 shadow-inner"
              >
                <svg
                  class="w-6 h-6 animate-spin"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 12a8 8 0 018-8"
                  />
                </svg>
              </div>
            </div>
            <div class="space-y-1">
              <p class="text-base font-semibold text-gray-900">
                {{ t('share.viewLoading') }}
              </p>
              <p class="text-sm text-gray-500">
                {{ t('share.viewLoadingDescription') }}
              </p>
            </div>
          </div>
        </BaseCard>

        <BaseCard v-else-if="error" class="max-w-md mx-auto">
          <div class="space-y-6 py-6 text-center">
            <div
              class="mx-auto w-16 h-16 bg-red-50 rounded-full flex items-center justify-center shadow-inner"
            >
              <svg
                class="w-7 h-7 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <div class="space-y-2 px-4">
              <h2 class="text-lg font-semibold text-gray-900">
                {{ t('share.linkExpired') }}
              </h2>
              <p class="text-sm text-gray-500 leading-relaxed">
                {{ error || t('share.viewExpired') }}
              </p>
            </div>

            <div class="flex justify-center">
              <BaseButton variant="primary" size="md" @click="goHome">
                {{ t('share.backToHome') }}
              </BaseButton>
            </div>
          </div>
        </BaseCard>

        <BaseCard
          v-else-if="requiresPassword && !threadline"
          class="max-w-sm mx-auto"
        >
          <div class="space-y-5 py-4">
            <!-- Icon and Title -->
            <div class="text-center space-y-2">
              <div
                class="mx-auto w-12 h-12 bg-primary-50 rounded-full flex items-center justify-center"
              >
                <svg
                  class="w-6 h-6 text-primary-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
              </div>
              <div class="space-y-1">
                <h2 class="text-lg font-semibold text-gray-900">
                  {{ t('share.requiresPassword') }}
                </h2>
                <p class="text-xs text-gray-500">
                  {{ t('share.passwordPrompt') }}
                </p>
              </div>
            </div>

            <!-- Password Input -->
            <div class="space-y-3">
              <input
                v-model="passwordInput"
                type="password"
                maxlength="6"
                minlength="6"
                inputmode="numeric"
                pattern="[0-9]*"
                autocomplete="off"
                class="w-full rounded-xl border px-4 py-3 text-center text-lg font-medium tracking-[0.15em] bg-white text-gray-900 shadow-sm transition-all focus:border-primary-500 focus:ring-2 focus:ring-primary-100 focus:outline-none placeholder:text-gray-400 placeholder:font-normal"
                :class="
                  passwordError
                    ? 'border-red-300 ring-1 ring-red-100'
                    : 'border-gray-200 hover:border-gray-300'
                "
                :placeholder="t('share.passwordPlaceholder')"
                @keyup.enter="submitPassword"
                @input="passwordError = ''"
                ref="passwordInputRef"
              />
              <p
                v-if="passwordError"
                class="text-xs text-red-600 text-center flex items-center justify-center gap-1"
              >
                <svg
                  class="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {{ passwordError }}
              </p>
            </div>

            <!-- Submit Button -->
            <BaseButton
              variant="primary"
              :loading="verifying"
              block
              size="md"
              @click="submitPassword"
              :disabled="passwordInput.trim().length !== 6"
              class="font-medium"
            >
              {{ t('share.submitPassword') }}
            </BaseButton>
          </div>
        </BaseCard>

        <!-- Threadline Content - Reusing Detail Page Structure -->
        <div v-else-if="threadline" class="space-y-6">
          <!-- Core Topic (Summary Title) -->
          <BaseCard>
            <div class="space-y-2">
              <h1 class="text-xl font-semibold text-gray-900">
                {{
                  threadline.summary_title ||
                  threadline.subject ||
                  t('common.noSubject')
                }}
              </h1>
              <div
                class="flex items-center gap-2 text-sm text-gray-500"
                v-if="threadline.received_at || threadline.created_at"
              >
                <svg
                  class="w-4 h-4 text-gray-400 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>{{
                  formatShareDate(
                    threadline.received_at || threadline.created_at
                  )
                }}</span>
              </div>
            </div>
          </BaseCard>

          <BaseCard v-if="hasMetadataInfo" :header-muted="true">
            <template #header>
              <div class="flex items-center gap-2 text-gray-800">
                <svg
                  class="w-5 h-5 -mt-px flex-none"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <h3 class="text-base font-semibold leading-5">
                  {{ t('metadata.sectionTitle') }}
                </h3>
              </div>
            </template>
            <div class="space-y-3 text-xs sm:text-sm text-gray-700">
              <div
                class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-1.5"
              >
                <div class="flex items-center gap-1 text-gray-500">
                  <svg
                    class="w-3.5 h-3.5 text-gray-400 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                  <span>{{ t('metadata.category.title') }}</span>
                </div>
                <div class="flex items-center gap-2 min-w-0">
                  <span
                    v-if="metadataCategory"
                    class="inline-flex items-center gap-1 px-2 h-6 rounded-md text-xs font-medium select-none bg-blue-100 text-blue-800"
                  >
                    {{ metadataCategory }}
                  </span>
                  <span v-else class="text-gray-400">
                    {{ t('todos.notSet') }}
                  </span>
                </div>
              </div>

              <div
                class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-1.5"
              >
                <div class="flex items-center gap-1 text-gray-500">
                  <svg
                    class="w-3.5 h-3.5 text-gray-400 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                    />
                  </svg>
                  <span>{{ t('metadata.participants.title') }}</span>
                </div>
                <div class="flex items-center gap-2 min-w-0">
                  <div
                    v-if="metadataParticipants.length > 0"
                    class="flex flex-wrap gap-2"
                  >
                    <span
                      v-for="(participant, index) in metadataParticipants"
                      :key="`participant-${index}`"
                      class="inline-flex items-center gap-1 px-2 h-6 rounded-md text-xs font-medium select-none bg-green-100 text-green-800"
                    >
                      {{ participant }}
                    </span>
                  </div>
                  <span v-else class="text-gray-400">
                    {{ t('todos.notSet') }}
                  </span>
                </div>
              </div>

              <div
                class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-1.5"
              >
                <div class="flex items-center gap-1 text-gray-500">
                  <svg
                    class="w-3.5 h-3.5 text-gray-400 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M7 7h.01M3 7a4 4 0 014-4h5l7 7a2 2 0 010 2.828l-5.172 5.172a2 2 0 01-2.828 0L3 12V7z"
                    />
                  </svg>
                  <span>{{ t('metadata.keywords.title') }}</span>
                </div>
                <div class="flex items-center gap-2 min-w-0">
                  <div
                    v-if="metadataTags.length > 0"
                    class="flex flex-wrap gap-2"
                  >
                    <span
                      v-for="(tag, index) in metadataTags"
                      :key="`tag-${index}`"
                      class="inline-flex items-center gap-1 px-2 h-6 rounded-md text-xs font-medium select-none bg-rose-100 text-rose-800"
                    >
                      {{ tag }}
                    </span>
                  </div>
                  <span v-else class="text-gray-400">
                    {{ t('todos.notSet') }}
                  </span>
                </div>
              </div>
            </div>
          </BaseCard>

          <!-- Details Section (New Format) -->
          <BaseCard
            v-if="hasNewFormat && summaryData.details"
            :header-muted="true"
          >
            <template #header>
              <div class="flex items-center justify-between w-full">
                <div class="flex items-center gap-2 text-gray-800">
                  <svg
                    class="w-5 h-5 -mt-px flex-none"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <h3 class="text-base font-semibold leading-5">
                    {{ t('todos.newFormat.details') }}
                  </h3>
                </div>
                <button
                  @click="copyContent(summaryData.details, 'details')"
                  class="flex-shrink-0 inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-50 hover:bg-gray-100 border border-gray-200 hover:border-gray-300 px-2.5 py-1.5 rounded-lg transition-all shadow-sm"
                  :title="t('common.copy')"
                >
                  <svg
                    v-if="!copiedStates.details"
                    class="h-3.5 w-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  <svg
                    v-else
                    class="h-3.5 w-3.5 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span class="hidden sm:inline">
                    {{
                      copiedStates.details
                        ? t('common.copied')
                        : t('common.copy')
                    }}
                  </span>
                </button>
              </div>
            </template>
            <MarkdownRenderer :content="summaryData.details" />
          </BaseCard>

          <!-- TODOs Section -->
          <BaseCard v-if="threadlineTodos.length > 0" :header-muted="true">
            <template #header>
              <div class="flex items-center gap-2 text-gray-800">
                <svg
                  class="w-5 h-5 -mt-px flex-none"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                  />
                </svg>
                <h3 class="text-base font-semibold leading-5">
                  {{ t('todos.newFormat.todos') }}
                </h3>
              </div>
            </template>
            <TransitionGroup name="todo-list" tag="div" class="space-y-2">
              <TodoItem
                v-for="todo in threadlineTodos"
                :key="todo.id"
                :todo="todo"
                :loading="false"
                :email-message-id="threadline?.id"
                :read-only="true"
                @toggle="() => {}"
                @save="() => {}"
                @delete="() => {}"
                @editing-change="() => {}"
              />
            </TransitionGroup>
          </BaseCard>

          <!-- Key Process Section -->
          <BaseCard
            v-if="
              hasNewFormat &&
              summaryData.key_process &&
              summaryData.key_process.length > 0
            "
            :header-muted="true"
          >
            <template #header>
              <div class="flex items-center justify-between w-full">
                <div class="flex items-center gap-2 text-gray-800">
                  <svg
                    class="w-5 h-5 -mt-px flex-none"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                    />
                  </svg>
                  <h3 class="text-base font-semibold leading-5">
                    {{ t('todos.newFormat.keyProcess') }}
                  </h3>
                </div>
                <button
                  @click="copyKeyProcess"
                  class="flex-shrink-0 inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-50 hover:bg-gray-100 border border-gray-200 hover:border-gray-300 px-2.5 py-1.5 rounded-lg transition-all shadow-sm"
                  :title="t('common.copy')"
                >
                  <svg
                    v-if="!copiedStates.keyProcess"
                    class="h-3.5 w-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  <svg
                    v-else
                    class="h-3.5 w-3.5 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span class="hidden sm:inline">
                    {{
                      copiedStates.keyProcess
                        ? t('common.copied')
                        : t('common.copy')
                    }}
                  </span>
                </button>
              </div>
            </template>
            <ul class="space-y-2">
              <li
                v-for="(item, index) in summaryData.key_process"
                :key="index"
                class="flex items-start gap-2 text-sm text-gray-700"
              >
                <span class="text-primary-600 mt-0.5">•</span>
                <span>{{ item }}</span>
              </li>
            </ul>
          </BaseCard>

          <!-- Conversation Records (LLM Content) -->
          <BaseCard
            v-if="
              threadline.llm_content ||
              (!hasNewFormat && threadline.summary_content)
            "
            :header-muted="true"
          >
            <template #header>
              <div class="flex items-center justify-between w-full">
                <div class="flex items-center gap-2 text-gray-800">
                  <svg
                    class="w-5 h-5 -mt-px flex-none"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"
                    />
                  </svg>
                  <h3 class="text-base font-semibold leading-5">
                    {{ t('chats.processedContent') }}
                  </h3>
                </div>
                <button
                  @click="
                    copyContent(
                      threadline.llm_content || threadline.summary_content,
                      threadline.llm_content ? 'llm' : 'summary'
                    )
                  "
                  class="flex-shrink-0 inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-50 hover:bg-gray-100 border border-gray-200 hover:border-gray-300 px-2.5 py-1.5 rounded-lg transition-all shadow-sm"
                  :title="t('common.copy')"
                >
                  <svg
                    v-if="!copiedStates.llm && !copiedStates.summary"
                    class="h-3.5 w-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  <svg
                    v-else
                    class="h-3.5 w-3.5 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span class="hidden sm:inline">
                    {{
                      copiedStates.llm || copiedStates.summary
                        ? t('common.copied')
                        : t('common.copy')
                    }}
                  </span>
                </button>
              </div>
            </template>
            <div v-if="threadline.llm_content">
              <MarkdownRenderer :content="threadline.llm_content" />
            </div>
            <div v-else-if="threadline.summary_content">
              <MarkdownRenderer :content="threadline.summary_content" />
            </div>
          </BaseCard>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { chatApi } from '@/api/chat'
import { useToast } from '@/composables/useToast'
import ShareHeader from '@/components/layout/ShareHeader.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import MarkdownRenderer from '@/components/ui/MarkdownRenderer.vue'
import TodoItem from '@/components/TodoItem.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { showSuccess, showError } = useToast()

const loading = ref(true)
const error = ref('')
const requiresPassword = ref(false)
const verifying = ref(false)
const threadline = ref(null)
const passwordInput = ref('')
const passwordError = ref('')
const passwordInputRef = ref(null)

// Copy states
const copiedStates = ref({
  details: false,
  keyProcess: false,
  llm: false,
  summary: false
})

const MAX_RETRIES = 5
const RETRY_DELAY = 2000

const token = computed(() => route.params.token)

// Check if threadline has new format
const hasNewFormat = computed(() => {
  if (!threadline.value) return false
  return !!(
    threadline.value.summary_data &&
    (threadline.value.summary_data.details ||
      threadline.value.summary_data.key_process)
  )
})

// Extract summary data
const summaryData = computed(() => {
  if (!threadline.value || !threadline.value.summary_data) {
    return {}
  }
  const data = threadline.value.summary_data
  if (typeof data === 'string') {
    try {
      return JSON.parse(data)
    } catch (err) {
      console.error('Failed to parse summary data:', err)
      return {}
    }
  }
  return data
})

// Extract todos
const threadlineTodos = computed(() => {
  if (!threadline.value || !threadline.value.todos) {
    return []
  }
  return threadline.value.todos
})

const metadataInfo = computed(() => threadline.value?.metadata || null)

const normalizeMetadataArray = (value) => {
  if (!value) {
    return []
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => (typeof item === 'string' ? item.trim() : ''))
      .filter((item) => item && item.length > 0)
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
  }
  return []
}

const metadataCategory = computed(() => {
  const value = metadataInfo.value?.category
  if (typeof value === 'string') {
    return value.trim()
  }
  return ''
})

const metadataParticipants = computed(() =>
  normalizeMetadataArray(metadataInfo.value?.participants)
)
const metadataTags = computed(() =>
  normalizeMetadataArray(metadataInfo.value?.keywords)
)
const hasMetadataInfo = computed(
  () =>
    !!metadataInfo.value &&
    (metadataCategory.value ||
      metadataParticipants.value.length > 0 ||
      metadataTags.value.length > 0)
)

const formatShareDate = (dateString) => {
  if (!dateString) {
    return t('common.noData')
  }
  try {
    return new Date(dateString).toLocaleString()
  } catch (err) {
    console.error('Failed to format date:', err)
    return dateString
  }
}

const normalizeSummaryData = (data) => {
  if (!data) {
    return {}
  }
  if (typeof data === 'string') {
    try {
      return JSON.parse(data)
    } catch (err) {
      console.error('Failed to parse summary data:', err)
      return {}
    }
  }
  return data
}

const prepareThreadline = (data) => {
  if (!data) {
    return null
  }
  return {
    ...data,
    summary_data: normalizeSummaryData(data.summary_data),
    todos: data.todos || []
  }
}

const loadShare = async (retryCount = 0) => {
  loading.value = true
  error.value = ''
  threadline.value = null
  requiresPassword.value = false

  try {
    const response = await chatApi.getPublicShare(token.value)
    const data = response.data.data || response.data
    requiresPassword.value = data.requires_password
    if (!data.requires_password) {
      threadline.value = prepareThreadline(data.threadline)
    }
    loading.value = false
  } catch (err) {
    const status = err.response?.status
    const isGone = status === 410
    const isNotFound = status === 404

    // Don't retry for permanent errors (410 Gone, 404 Not Found)
    if (isGone || isNotFound) {
      const errorMessage = err.response?.data?.message || ''
      // Translate common backend error messages
      if (errorMessage.includes('expired or is inactive')) {
        error.value = t('share.linkExpiredOrInactive')
      } else if (
        errorMessage &&
        errorMessage.length > 10 &&
        !errorMessage.toLowerCase().includes('failed')
      ) {
        // Only use backend message if it's meaningful and not just "failed"
        error.value = errorMessage
      } else {
        error.value = t('share.viewExpired')
      }
      loading.value = false
      return
    }

    console.error(
      `Failed to load share (attempt ${retryCount + 1}/${MAX_RETRIES}):`,
      err
    )

    // Only retry for transient errors (network issues, 500, etc.)
    if (retryCount < MAX_RETRIES - 1) {
      const delay = RETRY_DELAY * (retryCount + 1)
      console.log(`Retrying in ${delay}ms...`)
      setTimeout(() => {
        loadShare(retryCount + 1)
      }, delay)
    } else {
      const errorMessage = err.response?.data?.message || ''
      // Translate common backend error messages
      if (errorMessage.includes('expired or is inactive')) {
        error.value = t('share.linkExpiredOrInactive')
      } else if (
        errorMessage &&
        errorMessage.length > 10 &&
        !errorMessage.toLowerCase().includes('failed')
      ) {
        // Only use backend message if it's meaningful and not just "failed"
        error.value = errorMessage
      } else {
        error.value = t('share.viewExpired')
      }
      loading.value = false
    }
  }
}

const submitPassword = async (retryCount = 0) => {
  passwordError.value = ''
  const trimmedPassword = passwordInput.value.trim()
  if (!trimmedPassword || !/^\d{6}$/.test(trimmedPassword)) {
    passwordError.value = t('share.passwordRequired')
    return
  }

  verifying.value = true
  error.value = ''

  try {
    const response = await chatApi.verifyPublicShare(token.value, {
      password: passwordInput.value.trim()
    })
    const data = response.data.data || response.data
    requiresPassword.value = false
    threadline.value = prepareThreadline(data.threadline)
    verifying.value = false
  } catch (err) {
    const status = err.response?.status
    const isGone = status === 410
    const isNotFound = status === 404
    const isForbidden = status === 403

    // Handle password errors - don't retry
    if (isForbidden) {
      passwordError.value = t('share.invalidPassword')
      passwordInput.value = ''
      verifying.value = false
      await nextTick()
      if (passwordInputRef.value) {
        passwordInputRef.value.focus()
      }
      return
    }

    // Don't retry for permanent errors (410 Gone, 404 Not Found)
    if (isGone || isNotFound) {
      const errorMessage = err.response?.data?.message || ''
      // Translate common backend error messages
      if (errorMessage.includes('expired or is inactive')) {
        error.value = t('share.linkExpiredOrInactive')
      } else if (
        errorMessage &&
        errorMessage.length > 10 &&
        !errorMessage.toLowerCase().includes('failed')
      ) {
        // Only use backend message if it's meaningful and not just "failed"
        error.value = errorMessage
      } else {
        error.value = t('share.viewExpired')
      }
      verifying.value = false
      return
    }

    // Only retry for transient errors (network issues, 500, etc.)
    if (retryCount < MAX_RETRIES - 1) {
      const delay = RETRY_DELAY * (retryCount + 1)
      console.log(`Password verification failed, retrying in ${delay}ms...`)
      setTimeout(() => {
        submitPassword(retryCount + 1)
      }, delay)
    } else {
      const errorMessage = err.response?.data?.message || ''
      // Translate common backend error messages
      if (errorMessage.includes('expired or is inactive')) {
        error.value = t('share.linkExpiredOrInactive')
      } else if (
        errorMessage &&
        errorMessage.length > 10 &&
        !errorMessage.toLowerCase().includes('failed')
      ) {
        // Only use backend message if it's meaningful and not just "failed"
        error.value = errorMessage
      } else {
        error.value = t('share.viewExpired')
      }
      verifying.value = false
    }
  }
}

const goHome = () => {
  router.push('/chats')
}

// Copy content function with fallback
const copyToClipboard = async (text) => {
  // Try modern clipboard API first
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (err) {
      console.warn('Clipboard API failed, trying fallback:', err)
    }
  }

  // Fallback for older browsers or non-HTTPS contexts
  try {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    const successful = document.execCommand('copy')
    document.body.removeChild(textArea)
    return successful
  } catch (err) {
    console.error('Fallback copy failed:', err)
    return false
  }
}

// Copy content function
const copyContent = async (content, section) => {
  if (!content) {
    showError(t('common.copyFailed'))
    return
  }

  try {
    // Extract plain text from markdown content
    let textContent = content
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/^#+\s+/gm, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/__([^_]+)__/g, '$1')
      .replace(/_([^_]+)_/g, '$1')
      .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
      .replace(/!\[([^\]]*)\]\([^\)]+\)/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim()

    const success = await copyToClipboard(textContent)
    if (success) {
      copiedStates.value[section] = true
      showSuccess(t('common.copied'))
      setTimeout(() => {
        copiedStates.value[section] = false
      }, 2000)
    } else {
      showError(t('common.copyFailed'))
    }
  } catch (error) {
    console.error('Failed to copy content:', error)
    showError(t('common.copyFailed'))
  }
}

// Copy key process function
const copyKeyProcess = async () => {
  const keyProcess = summaryData.value?.key_process || []
  if (keyProcess.length === 0) {
    showError(t('common.copyFailed'))
    return
  }

  try {
    const text = keyProcess
      .map((item, index) => `${index + 1}. ${item}`)
      .join('\n')
    const success = await copyToClipboard(text)
    if (success) {
      copiedStates.value.keyProcess = true
      showSuccess(t('common.copied'))
      setTimeout(() => {
        copiedStates.value.keyProcess = false
      }, 2000)
    } else {
      showError(t('common.copyFailed'))
    }
  } catch (error) {
    console.error('Failed to copy key process:', error)
    showError(t('common.copyFailed'))
  }
}

const focusPasswordInput = async () => {
  await nextTick()
  if (passwordInputRef.value && requiresPassword.value) {
    setTimeout(() => {
      if (passwordInputRef.value) {
        passwordInputRef.value.focus()
      }
    }, 100)
  }
}

watch(requiresPassword, (newVal) => {
  if (newVal) {
    focusPasswordInput()
  }
})

onMounted(() => {
  loadShare()
})

watch(
  token,
  (newToken, oldToken) => {
    if (newToken && newToken !== oldToken) {
      loadShare()
    }
  }
)
</script>
