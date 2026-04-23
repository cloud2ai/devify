<template>
  <div v-if="shareStatus?.is_active" class="mt-1.5 sm:mt-3">
    <!-- Divider -->
    <div class="border-t border-gray-200"></div>
    <div class="pt-3">
      <div class="space-y-2 sm:space-y-3">
        <!-- Expiration Row -->
        <div
          class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-2 text-xs sm:text-sm"
        >
          <div class="flex items-center gap-1 text-gray-500">
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
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{{ t('share.expirationTime') }}</span>
          </div>
          <div class="flex items-center gap-2 min-w-0">
            <template v-if="!editingExpiration">
              <div
                class="flex items-center gap-2 group cursor-pointer"
                @click="startEditingExpiration"
              >
                <span class="text-gray-700 truncate">
                  {{ shareExpirationDisplay }}
                </span>
                <svg
                  class="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                  />
                </svg>
              </div>
            </template>
            <template v-else>
              <div class="flex items-center gap-2 flex-wrap">
                <div class="flex flex-wrap gap-1">
                  <button
                    v-for="option in shareExpirationOptions"
                    :key="option.value"
                    type="button"
                    class="rounded-md border px-2 py-0.5 text-xs font-medium transition-colors"
                    :class="
                      tempExpiration === option.value
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    "
                    :disabled="expirationSaving"
                    @click="tempExpiration = option.value"
                  >
                    {{ option.label }}
                  </button>
                </div>
                <div class="flex items-center gap-1">
                  <button
                    type="button"
                    class="p-1 text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50"
                    :disabled="expirationSaving"
                    @click="saveExpiration"
                  >
                    <svg
                      v-if="!expirationSaving"
                      class="w-4 h-4"
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
                    <svg
                      v-else
                      class="w-4 h-4 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                      ></circle>
                      <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                    :disabled="expirationSaving"
                    @click="cancelEditingExpiration"
                  >
                    <svg
                      class="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Link Row -->
        <div
          class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-2 text-xs sm:text-sm"
        >
          <div class="flex items-center gap-1 text-gray-500">
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
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
              />
            </svg>
            <span>{{ t('share.shareLink') }}</span>
          </div>
          <div class="flex items-center gap-2 min-w-0">
            <a
              v-if="!showShareLink.main"
              :href="shareStatus.share_url"
              target="_blank"
              class="text-gray-700 hover:text-primary-600 transition-colors"
            >
              <span>{{ t('share.openLink') }}</span>
            </a>
            <a
              v-else
              :href="shareStatus.share_url"
              target="_blank"
              class="text-gray-700 truncate font-mono hover:text-primary-600 hover:underline flex-1 min-w-0"
            >
              {{ shareStatus.share_url }}
            </a>
            <button
              type="button"
              class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
              :title="
                showShareLink.main ? t('share.hideLink') : t('share.openLink')
              "
              @click="showShareLink.main = !showShareLink.main"
            >
              <svg
                v-if="!showShareLink.main"
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
              <svg
                v-else
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                />
              </svg>
            </button>
            <button
              type="button"
              class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
              :title="
                shareCopyState.link ? t('share.copied') : t('share.copyLink')
              "
              :disabled="!shareStatus.share_url"
              @click="copyLinkOnly"
            >
              <svg
                v-if="!shareCopyState.link"
                class="w-4 h-4"
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
                class="w-4 h-4 text-green-600"
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
            </button>
          </div>
        </div>

        <!-- Password Row -->
        <div
          class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-2 text-xs sm:text-sm"
        >
          <div class="flex items-center gap-1 text-gray-500">
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
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
            <span>{{ t('share.passwordLabel') }}</span>
          </div>
          <div class="flex items-center gap-2 min-w-0">
            <template v-if="shareStatus.has_password">
              <span v-if="!showPassword" class="font-mono text-gray-900">
                ••••••
              </span>
              <span v-else class="font-mono text-gray-900">
                {{ inlinePassword || shareStatus.password }}
              </span>

              <div class="flex items-center gap-1">
                <button
                  type="button"
                  class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors"
                  :title="
                    showPassword
                      ? t('share.hidePassword')
                      : t('share.showPassword')
                  "
                  @click="showPassword = !showPassword"
                >
                  <svg
                    v-if="!showPassword"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    />
                  </svg>
                  <svg
                    v-else
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                    />
                  </svg>
                </button>
                <button
                  type="button"
                  class="p-1 text-gray-400 hover:text-red-600 rounded hover:bg-gray-100 transition-colors"
                  :title="t('common.delete')"
                  :disabled="passwordSaving"
                  @click="removePassword"
                >
                  <svg
                    v-if="!passwordSaving"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                  <svg
                    v-else
                    class="w-4 h-4 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    ></circle>
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                </button>
              </div>
              <button
                type="button"
                class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
                :title="
                  shareCopyState.password
                    ? t('share.copied')
                    : t('share.copyAll')
                "
                @click="copyFullInvite"
              >
                <svg
                  v-if="!shareCopyState.password"
                  class="w-4 h-4"
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
                  class="w-4 h-4 text-green-600"
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
              </button>
            </template>
            <template v-else>
              <span class="text-gray-500">
                {{ t('share.noPassword') }}
              </span>
              <button
                type="button"
                class="p-1 text-gray-400 hover:text-primary-600 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
                :title="t('share.addPassword')"
                :disabled="passwordSaving"
                @click="createRandomPassword"
              >
                <svg
                  v-if="!passwordSaving"
                  class="w-4 h-4"
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
                <svg
                  v-else
                  class="w-4 h-4 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  shareStatus: {
    type: Object,
    default: null
  },
  shareExpirationDisplay: {
    type: String,
    default: ''
  },
  shareExpirationOptions: {
    type: Array,
    default: () => []
  },
  editingExpiration: {
    type: Boolean,
    default: false
  },
  tempExpiration: {
    type: String,
    default: '30d'
  },
  expirationSaving: {
    type: Boolean,
    default: false
  },
  showShareLink: {
    type: Object,
    required: true
  },
  shareCopyState: {
    type: Object,
    required: true
  },
  showPassword: {
    type: Boolean,
    default: false
  },
  inlinePassword: {
    type: String,
    default: ''
  },
  passwordSaving: {
    type: Boolean,
    default: false
  }
})

defineEmits([
  'start-editing-expiration',
  'save-expiration',
  'cancel-editing-expiration',
  'update:tempExpiration',
  'toggle-share-link',
  'copy-link-only',
  'toggle-password',
  'remove-password',
  'copy-full-invite',
  'create-random-password'
])
</script>
