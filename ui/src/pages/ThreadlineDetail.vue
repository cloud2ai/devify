<template>
  <AppLayout>
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="text-center">
        <div
          class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"
        ></div>
        <p class="mt-2 text-sm text-gray-500">{{ t('common.loading') }}</p>
      </div>
    </div>

    <div v-else-if="error" class="text-center py-12">
      <div
        class="mx-auto h-12 w-12 bg-red-100 rounded-full flex items-center justify-center"
      >
        <svg
          class="h-6 w-6 text-red-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      </div>
      <h3 class="mt-2 text-sm font-medium text-gray-900">
        {{ t('chats.errorLoading') }}
      </h3>
      <p class="mt-1 text-sm text-gray-500">{{ error }}</p>
      <div class="mt-6">
        <BaseButton @click="loadThreadline" variant="primary">
          {{ t('common.tryAgain') }}
        </BaseButton>
      </div>
    </div>

    <div v-else-if="threadline" class="space-y-6">
      <!-- Todo Error Message -->
      <div
        v-if="todoErrorMessage"
        class="rounded-md bg-red-50 border border-red-200 p-3"
      >
        <div class="flex gap-2">
          <div class="flex-shrink-0 pt-0.5">
            <svg
              class="h-4 w-4 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <div class="flex-1">
            <p class="text-sm font-medium text-red-800">
              {{ todoErrorMessage }}
            </p>
          </div>
          <button
            @click="todoErrorMessage = ''"
            class="flex-shrink-0 text-red-400 hover:text-red-600"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      <!-- Todo Success Message -->
      <div
        v-if="todoSuccessMessage"
        class="rounded-md bg-green-50 border border-green-200 p-3"
      >
        <div class="flex gap-2">
          <div class="flex-shrink-0 pt-0.5">
            <svg
              class="h-4 w-4 text-green-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <div class="flex-1">
            <p class="text-sm font-medium text-green-800">
              {{ todoSuccessMessage }}
            </p>
          </div>
          <button
            @click="todoSuccessMessage = ''"
            class="flex-shrink-0 text-green-400 hover:text-green-600"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      <!-- Top Actions Bar -->
      <div class="mb-4">
        <div class="flex items-center justify-between gap-3">
          <!-- Back Button -->
          <button
            @click="goBack"
            class="flex-shrink-0 w-9 h-9 rounded-lg bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 flex items-center justify-center transition-all shadow-sm"
            :title="t('common.back')"
          >
            <svg
              class="w-4 h-4 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
          </button>

          <!-- Right Actions: Refresh Button + Retry Button + Share Button + More Menu -->
          <div class="flex items-center gap-2 flex-shrink-0 ml-auto">
            <!-- Refresh Button -->
            <button
              @click="loadThreadline"
              class="flex-shrink-0 w-9 h-9 rounded-lg bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 flex items-center justify-center transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white"
              :disabled="loading || deleting || retrying || isProcessing"
              :title="t('common.refresh')"
            >
              <svg
                v-if="!loading"
                class="w-4 h-4 text-gray-600"
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
              <svg
                v-else
                class="w-4 h-4 text-gray-600 animate-spin"
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
            <!-- Retry Button - Hide text on mobile, show icon only -->
            <BaseButton
              @click="handleRetryClick"
              variant="primary"
              size="sm"
              :loading="retrying || isProcessing"
              :disabled="deleting || retrying || isProcessing"
              class="px-2 sm:px-3"
            >
              <svg
                v-if="!retrying && !isProcessing"
                class="w-4 h-4 sm:mr-1 flex-shrink-0"
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
              <span class="hidden sm:inline">
                {{
                  retrying || isProcessing
                    ? t('common.status.processing')
                    : t('retry.retryButton')
                }}
              </span>
            </BaseButton>
            <BaseButton
              :variant="
                shareStatus?.is_active && !shareStatus?.is_expired
                  ? 'danger'
                  : 'outline'
              "
              size="sm"
              class="px-2 sm:px-3"
              :loading="shareSaving || shareRevoking"
              :disabled="deleting || retrying || isProcessing"
              @click.stop="handleShareButtonClick"
            >
              <svg
                v-if="!(shareStatus?.is_active && !shareStatus?.is_expired)"
                class="w-4 h-4 sm:mr-1 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 12v.01M12 4h.01M20 12v.01M12 20h.01M7.5 7.5l9 9"
                />
              </svg>
              <svg
                v-else
                class="w-4 h-4 sm:mr-1 flex-shrink-0"
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
              <span class="hidden sm:inline">
                {{
                  shareStatus?.is_active && !shareStatus?.is_expired
                    ? t('share.stopSharing')
                    : t('share.title')
                }}
              </span>
            </BaseButton>

            <!-- More Menu Button -->
            <div class="relative" ref="actionMenuRef">
              <button
                @click="showActionMenu = !showActionMenu"
                class="w-9 h-9 rounded-lg bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 flex items-center justify-center transition-all shadow-sm"
                :title="t('common.moreActions')"
              >
                <svg
                  class="w-4 h-4 text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                  />
                </svg>
              </button>

              <!-- Dropdown Menu (Only Delete) -->
              <Transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="transform opacity-0 scale-95"
                enter-to-class="transform opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="transform opacity-100 scale-100"
                leave-to-class="transform opacity-0 scale-95"
              >
                <div
                  v-if="showActionMenu"
                  class="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50"
                >
                  <div class="py-1">
                    <button
                      @click="
                        () => {
                          deleteThreadline()
                          showActionMenu = false
                        }
                      "
                      class="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      :disabled="retrying || isProcessing || deleting"
                    >
                      <svg
                        v-if="!deleting"
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
                      <span>
                        {{
                          deleting ? t('common.deleting') : t('common.delete')
                        }}
                      </span>
                    </button>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>

      <!-- Title and Metadata Card -->
      <BaseCard>
        <div class="space-y-4">
          <!-- Title -->
          <div class="relative">
            <!-- Display Mode -->
            <div v-if="!editingTitle">
              <button
                type="button"
                class="group relative inline-flex items-start gap-2 w-full text-left rounded transition-colors"
                @click="startEditingTitle"
                :disabled="isProcessing"
              >
                <h2
                  class="text-lg font-bold leading-7 text-gray-900 sm:text-xl flex-1 pr-6 line-clamp-5"
                >
                  <span
                    v-if="shareStatus?.is_active"
                    class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium mr-2 align-middle"
                    :class="
                      shareStatus.is_expired
                        ? 'border-red-200 bg-red-50 text-red-600'
                        : 'border-green-200 bg-green-50 text-green-700'
                    "
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
                        d="M15 8a3 3 0 11-6 0 3 3 0 016 0zM5.5 20a6.5 6.5 0 0113 0M4 4l16 16"
                      />
                    </svg>
                    {{
                      shareStatus.is_expired
                        ? t('share.statusExpired')
                        : t('share.statusShared')
                    }}
                  </span>
                  {{
                    threadline.summary_title ||
                    threadline.subject ||
                    t('common.noSubject')
                  }}
                  <svg
                    class="hidden sm:inline-block w-3.5 h-3.5 ml-1.5 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity align-text-bottom"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    style="margin-top: -0.1em"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </h2>
              </button>
              <!-- Share Info Area -->
              <div v-if="shareStatus?.is_active" class="mt-4">
                <!-- Divider -->
                <div class="border-t border-gray-200"></div>
                <div class="pt-4">
                  <div class="space-y-3">
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
                            showShareLink.main
                              ? t('share.hideLink')
                              : t('share.openLink')
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
                            shareCopyState.link
                              ? t('share.copied')
                              : t('share.copyLink')
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
                          <!-- Edit Mode -->
                          <template v-if="editingPassword">
                            <div class="flex items-center gap-2 flex-1 min-w-0">
                              <input
                                v-model="tempPassword"
                                type="text"
                                inputmode="numeric"
                                maxlength="6"
                                minlength="6"
                                pattern="[0-9]*"
                                class="flex-1 min-w-0 font-mono text-sm rounded-md border border-gray-300 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                :placeholder="t('share.passwordPlaceholder')"
                                @keyup.enter="savePassword"
                                @keyup.esc="cancelEditingPassword"
                              />
                              <button
                                type="button"
                                class="p-1 text-green-600 hover:text-green-700 rounded hover:bg-green-50 transition-colors flex-shrink-0"
                                :title="t('common.save')"
                                :disabled="
                                  passwordSaving ||
                                  !tempPassword.trim() ||
                                  tempPassword.trim().length !== 6
                                "
                                @click="savePassword"
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
                                class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
                                :title="t('common.cancel')"
                                :disabled="passwordSaving"
                                @click="cancelEditingPassword"
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
                          </template>
                          <!-- Display Mode -->
                          <template v-else>
                            <span
                              v-if="!showPassword"
                              class="font-mono text-gray-900"
                            >
                              ••••••
                            </span>
                            <span v-else class="font-mono text-gray-900">
                              {{ inlinePassword || shareStatus.password }}
                            </span>

                            <div class="flex items-center gap-1">
                              <button
                                type="button"
                                class="p-1 text-gray-400 hover:text-primary-600 rounded hover:bg-gray-100 transition-colors"
                                :title="t('share.editPassword')"
                                :disabled="passwordSaving || isProcessing"
                                @click="startEditingPassword"
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
                                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                  />
                                </svg>
                              </button>
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
            </div>
            <!-- Edit Mode -->
            <div v-else class="space-y-1">
              <div
                class="relative bg-blue-50 border-2 border-blue-200 rounded-md"
                style="padding: 0.75rem 1rem"
              >
                <textarea
                  ref="titleInputRef"
                  v-model="editingTitleValue"
                  rows="2"
                  class="w-full px-0 py-0 text-lg font-bold leading-7 text-gray-900 sm:text-xl border-0 focus:outline-none bg-transparent resize-none overflow-hidden"
                  :class="{ 'border-red-300': titleError }"
                  :disabled="savingTitle"
                  style="
                    line-height: 1.75rem;
                    min-height: 3.5rem;
                    height: 3.5rem;
                  "
                ></textarea>
                <p v-if="titleError" class="mt-2 text-xs text-red-600">
                  {{ titleError }}
                </p>
              </div>
              <!-- Save/Cancel Icons - Right bottom below input -->
              <div class="flex items-center justify-end gap-1">
                <div
                  class="flex items-center bg-white rounded-md shadow-sm border border-gray-200 overflow-hidden"
                >
                  <button
                    @click="saveTitle"
                    type="button"
                    :disabled="savingTitle"
                    class="p-1.5 pr-2 text-green-600 hover:bg-green-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed relative"
                    :title="t('common.save')"
                  >
                    <svg
                      v-if="!savingTitle"
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
                    <div
                      class="absolute right-0 top-0 bottom-0 w-px bg-gray-200"
                    ></div>
                  </button>
                  <button
                    @click="cancelEditingTitle"
                    type="button"
                    :disabled="savingTitle"
                    class="p-1.5 pl-2 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    :title="t('common.cancel')"
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
            </div>
          </div>

          <!-- Date/Time and Metadata -->
          <div class="mt-4">
            <!-- Divider -->
            <div class="border-t border-gray-200"></div>
            <div class="pt-4">
              <div class="space-y-3">
                <!-- Created Time -->
                <div
                  class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-1.5 text-xs sm:text-sm"
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
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span>{{ t('metadata.createdAt.title') }}</span>
                  </div>
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="text-gray-700">{{
                      formatDate(
                        threadline.received_at || threadline.created_at
                      )
                    }}</span>
                  </div>
                </div>

                <!-- Category -->
                <div
                  v-if="threadline.metadata"
                  class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-1.5 text-xs sm:text-sm"
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
                    <MetadataChipsEditor
                      :model-value="threadline.metadata.category || ''"
                      variant="blue"
                      :disabled="isSaving('category')"
                      :loading="isSaving('category')"
                      @update:modelValue="(v) => onChipsChange('category', v)"
                      @change="(v) => onChipsSave('category', v)"
                    />
                  </div>
                </div>

                <!-- Participants -->
                <div
                  v-if="threadline.metadata"
                  class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-1.5 text-xs sm:text-sm"
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
                    <MetadataChipsEditor
                      :model-value="threadline.metadata.participants || []"
                      variant="green"
                      :disabled="isSaving('participants')"
                      :loading="isSaving('participants')"
                      :max-display="6"
                      @update:modelValue="
                        (v) => onChipsChange('participants', v)
                      "
                      @change="(v) => onChipsSave('participants', v)"
                    />
                  </div>
                </div>

                <!-- Tags -->
                <div
                  v-if="threadline.metadata"
                  class="grid grid-cols-[theme(spacing.28),1fr] gap-y-1 gap-x-1.5 text-xs sm:text-sm"
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
                    <MetadataChipsEditor
                      :model-value="threadline.metadata.keywords || []"
                      variant="rose"
                      :disabled="isSaving('keywords')"
                      :loading="isSaving('keywords')"
                      :max-display="6"
                      @update:modelValue="(v) => onChipsChange('keywords', v)"
                      @change="(v) => onChipsSave('keywords', v)"
                    />
                  </div>
                </div>

                <p
                  v-if="
                    fieldError('keywords') ||
                    fieldError('category') ||
                    fieldError('participants')
                  "
                  class="text-xs sm:text-sm text-red-600"
                >
                  {{
                    fieldError('keywords') ||
                    fieldError('category') ||
                    fieldError('participants')
                  }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </BaseCard>

      <!-- Summary Content - New Format or Old Format -->
      <div v-if="hasNewFormat" class="space-y-6">
        <!-- Details Section -->
        <BaseCard :header-muted="true">
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
              <div class="flex items-center gap-2">
                <BaseButton
                  size="sm"
                  variant="primary"
                  @click="openDetailsEditor"
                  :disabled="isProcessing || editingDetails"
                >
                  <svg
                    class="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                  {{ t('common.edit') }}
                </BaseButton>
                <button
                  v-if="summaryData.details"
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
            </div>
          </template>
          <InlineMarkdownEditor
            ref="detailsEditorRef"
            v-model="detailsValue"
            :label="t('todos.newFormat.details')"
            :placeholder="t('todos.newFormat.details')"
            :hint="t('common.markdownSupported')"
            :saving="savingDetails"
            :error="detailsError"
            :disabled="isProcessing"
            :show-edit-button="false"
            @save="saveDetails"
            @cancel="cancelEditingDetails"
          >
            <template #display>
              <MarkdownRenderer :content="summaryData.details" />
            </template>
          </InlineMarkdownEditor>
        </BaseCard>

        <!-- TODOs Section -->
        <BaseCard :header-muted="true">
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
                  {{ t('todos.newFormat.todos') }}
                </h3>
              </div>
              <BaseButton
                @click="handleAddTodo"
                variant="primary"
                size="sm"
                :disabled="
                  !!tempNewTodo || savingNewTodo || editingTodoIds.size > 0
                "
              >
                <svg
                  class="w-4 h-4 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                {{ t('todos.add') }}
              </BaseButton>
            </div>
          </template>
          <TransitionGroup name="todo-list" tag="div" class="space-y-2">
            <!-- New Todo Item (in edit mode) -->
            <TodoItem
              v-if="tempNewTodo"
              :key="tempNewTodo.id"
              :todo="tempNewTodo"
              :loading="savingNewTodo"
              :email-message-id="threadline?.id"
              :is-new="true"
              @toggle="() => {}"
              @save="saveNewTodo"
              @delete="() => {}"
              @cancel-new="cancelNewTodo"
              @editing-change="
                (editing) => handleTodoEditingChange(tempNewTodo.id, editing)
              "
            />

            <!-- Existing Todo Items -->
            <TodoItem
              v-for="todo in threadlineTodos"
              :key="todo.id"
              :todo="todo"
              :loading="todoLoading[todo.id]"
              :email-message-id="threadline?.id"
              @toggle="handleToggleTodo"
              @save="handleSaveTodoInline"
              @delete="handleDeleteTodo"
              @editing-change="
                (editing) => handleTodoEditingChange(todo.id, editing)
              "
            />
          </TransitionGroup>
          <div
            v-if="threadlineTodos.length === 0 && !tempNewTodo"
            class="text-gray-500 italic text-center py-8"
          >
            <p>{{ t('todos.noTodos') }}</p>
          </div>
        </BaseCard>

        <!-- Key Process Section -->
        <BaseCard :header-muted="true">
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
              <div class="flex items-center gap-2">
                <BaseButton
                  size="sm"
                  variant="primary"
                  @click="openKeyProcessEditor"
                  :disabled="isProcessing || editingKeyProcess"
                >
                  <svg
                    class="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                  {{ t('common.edit') }}
                </BaseButton>
                <button
                  v-if="
                    summaryData.key_process &&
                    summaryData.key_process.length > 0
                  "
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
            </div>
          </template>
          <InlineArrayEditor
            ref="keyProcessEditorRef"
            v-model="keyProcessValue"
            :label="t('todos.newFormat.keyProcess')"
            :placeholder="t('todos.newFormat.keyProcessPlaceholder')"
            :hint="t('todos.newFormat.keyProcessHint')"
            :saving="savingKeyProcess"
            :error="keyProcessError"
            :disabled="isProcessing"
            :show-edit-button="false"
            @save="saveKeyProcess"
            @cancel="cancelEditingKeyProcess"
          />
        </BaseCard>
      </div>

      <!-- Old Format Summary -->
      <BaseCard v-else :header-muted="true">
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
                  d="M9 12h6m-6 4h6M5 7h14"
                />
              </svg>
              <h3 class="text-base font-semibold leading-5">
                {{ t('chats.aiSummary') }}
              </h3>
            </div>
            <button
              v-if="threadline.summary_content"
              @click="copyContent(threadline.summary_content, 'summary')"
              class="flex-shrink-0 inline-flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded transition-colors"
              :title="t('common.copy')"
            >
              <svg
                v-if="!copiedStates.summary"
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
                  copiedStates.summary ? t('common.copied') : t('common.copy')
                }}
              </span>
            </button>
          </div>
        </template>
        <div
          v-if="threadline.summary_title || threadline.summary_content"
          class="space-y-4"
        >
          <div v-if="threadline.summary_title">
            <h3 class="text-lg font-medium text-gray-900 mb-2">
              {{ threadline.summary_title }}
            </h3>
          </div>
          <div v-if="threadline.summary_content">
            <MarkdownRenderer :content="threadline.summary_content" />
          </div>
        </div>
        <div v-else class="text-gray-500 italic text-center py-8">
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
          <p>{{ t('chats.summaryProcessing') }}</p>
          <p class="text-sm mt-2">
            {{ t('common.status') }}: {{ threadline.status || 'pending' }}
          </p>
        </div>
      </BaseCard>

      <!-- LLM Content (AI Processed) -->
      <BaseCard :header-muted="true">
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
              v-if="threadline.llm_content"
              @click="copyContent(threadline.llm_content, 'llm')"
              class="flex-shrink-0 inline-flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded transition-colors"
              :title="t('common.copy')"
            >
              <svg
                v-if="!copiedStates.llm"
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
                {{ copiedStates.llm ? t('common.copied') : t('common.copy') }}
              </span>
            </button>
          </div>
        </template>
        <div v-if="threadline.llm_content">
          <MarkdownRenderer :content="threadline.llm_content" />
        </div>
        <div v-else class="text-gray-500 italic text-center py-8">
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
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <p>{{ t('chats.processedContentProcessing') }}</p>
          <p class="text-sm mt-2">{{ t('chats.processedContentDesc') }}</p>
        </div>
      </BaseCard>
    </div>
    <MetadataFieldEditor
      :show="showEditor"
      :field-key="editorKey"
      :value="editorValue"
      @cancel="closeEditor"
      @save="saveEditor"
    />
    <RetryDialog
      :show="showRetryDialog"
      :status="threadline?.status"
      @close="showRetryDialog = false"
      @confirm="handleRetry"
    />
    <ConfirmDialog
      :show="showDeleteConfirm"
      :title="t('common.delete')"
      message="Are you sure you want to delete this threadline?"
      variant="danger"
      :confirm-text="t('common.delete')"
      :loading="deleting"
      @close="showDeleteConfirm = false"
      @confirm="confirmDelete"
    />

    <BaseModal
      :show="showShareModal"
      :title="t('share.modalTitle')"
      @close="closeShareModal"
    >
      <div class="space-y-4 text-sm text-gray-700">
        <p class="text-gray-600">
          {{ t('share.modalDescription') }}
        </p>

        <div
          v-if="shareStatus?.is_active"
          class="rounded-md border border-gray-200 bg-gray-50 p-3 space-y-2"
        >
          <div class="text-xs font-medium text-gray-500">
            {{ t('share.currentShare') }}
          </div>
          <div class="flex items-center gap-2 min-w-0">
            <a
              v-if="!showShareLink.modal"
              :href="shareStatus.share_url"
              target="_blank"
              class="text-sm text-gray-700 hover:text-primary-600 transition-colors"
            >
              <span>{{ t('share.openLink') }}</span>
            </a>
            <a
              v-else
              :href="shareStatus.share_url"
              target="_blank"
              class="text-sm text-gray-700 truncate font-mono hover:text-primary-600 hover:underline flex-1 min-w-0"
            >
              {{ shareStatus.share_url }}
            </a>
            <button
              type="button"
              class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
              :title="
                showShareLink.modal ? t('share.hideLink') : t('share.openLink')
              "
              @click="showShareLink.modal = !showShareLink.modal"
            >
              <svg
                v-if="!showShareLink.modal"
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
              :title="shareCopyState.link ? t('share.copied') : t('share.copy')"
              @click="copyShareLink"
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

        <div class="space-y-2">
          <span class="text-xs font-medium text-gray-700">{{
            t('share.expirationLabel')
          }}</span>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="option in shareExpirationOptions"
              :key="option.value"
              type="button"
              class="rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
              :class="
                shareForm.expiration === option.value
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-300 text-gray-600'
              "
              @click="shareForm.expiration = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <div class="space-y-2">
          <label
            class="flex items-center gap-2 text-xs font-medium text-gray-700"
          >
            <input
              type="checkbox"
              v-model="shareForm.requirePassword"
              class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            {{ t('share.passwordToggleLabel') }}
          </label>
          <p class="text-xs text-gray-500">
            {{ t('share.passwordHint') }}
          </p>
          <div
            v-if="shareForm.requirePassword"
            class="flex items-stretch gap-2"
          >
            <input
              v-model="shareForm.password"
              inputmode="numeric"
              maxlength="6"
              minlength="6"
              pattern="[0-9]*"
              class="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              :placeholder="t('share.passwordPlaceholder')"
            />
            <BaseButton
              variant="secondary"
              size="sm"
              @click="generateLocalPassword"
            >
              {{ t('share.generatePassword') }}
            </BaseButton>
          </div>
        </div>

        <div
          v-if="sharePasswordDisplay"
          class="rounded-md border border-green-200 bg-green-50 p-3 space-y-2"
        >
          <div class="text-xs font-medium text-green-700">
            {{ t('share.generatedPasswordLabel') }}
          </div>
          <div class="flex items-center justify-between">
            <span class="text-lg font-mono text-gray-900">
              {{ sharePasswordDisplay }}
            </span>
            <button
              class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
              :title="
                shareCopyState.password ? t('share.copied') : t('share.copy')
              "
              type="button"
              @click="copySharePassword"
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
          </div>
        </div>

        <p v-if="shareError" class="text-sm text-red-600">
          {{ shareError }}
        </p>
        <p v-if="shareSuccessMessage" class="text-sm text-green-600">
          {{ shareSuccessMessage }}
        </p>
      </div>
      <template #footer>
        <div class="flex flex-wrap items-center gap-2 w-full">
          <div class="flex-grow"></div>
          <div class="flex items-center gap-2">
            <BaseButton
              v-if="shareStatus?.is_active"
              variant="danger"
              size="sm"
              :loading="shareRevoking"
              @click="handleStopSharing"
            >
              {{ t('share.stopSharing') }}
            </BaseButton>
            <BaseButton
              variant="primary"
              size="sm"
              :loading="shareSaving"
              @click="handleShareSubmit"
            >
              {{
                shareStatus?.is_active
                  ? t('share.updateButton')
                  : t('share.createButton')
              }}
            </BaseButton>
            <BaseButton
              variant="secondary"
              size="sm"
              :disabled="shareSaving || shareRevoking"
              @click="closeShareModal"
            >
              {{ t('common.close') }}
            </BaseButton>
          </div>
        </div>
      </template>
    </BaseModal>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import MetadataFieldEditor from '@/components/MetadataFieldEditor.vue'
import MetadataChipsEditor from '@/components/MetadataChipsEditor.vue'
import RetryDialog from '@/components/RetryDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import TodoItem from '@/components/TodoItem.vue'
import TodoEditor from '@/components/TodoEditor.vue'
import InlineMarkdownEditor from '@/components/InlineMarkdownEditor.vue'
import InlineArrayEditor from '@/components/InlineArrayEditor.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import MarkdownRenderer from '@/components/ui/MarkdownRenderer.vue'
import { useThreadline } from '@/composables/useThreadline'
import { useThreadlinePolling } from '@/composables/useThreadlinePolling'
import { useThreadlineShare } from '@/composables/useThreadlineShare'
import { useThreadlineTodos } from '@/composables/useThreadlineTodos'
import { useThreadlineMetadata } from '@/composables/useThreadlineMetadata'
import { useThreadlineContent } from '@/composables/useThreadlineContent'

const route = useRoute()
const { t } = useI18n()

// Initialize composables
// Create shared threadline ref first
const threadline = ref(null)

// Initialize polling composable (needs threadline)
const polling = useThreadlinePolling(threadline, route)

// Initialize core threadline composable (needs polling.startPolling)
const {
  loading,
  error,
  deleting,
  showDeleteConfirm,
  showActionMenu,
  actionMenuRef,
  shareStatus: computedShareStatus,
  isProcessing,
  hasNewFormat,
  summaryData,
  formatDate,
  getStatusClass,
  loadThreadline,
  deleteThreadline,
  confirmDelete,
  goBack,
  handleClickOutside
} = useThreadline(route, polling.startPolling, threadline)

// Initialize share composable
const share = useThreadlineShare(threadline, route)

// Initialize todos composable
const todos = useThreadlineTodos(threadline)

// Initialize metadata composable
const metadata = useThreadlineMetadata(threadline, route)

// Initialize content composable (needs summaryData getter)
const content = useThreadlineContent(threadline, route, () => summaryData.value)

// Expose composable values for template
const shareStatus = computedShareStatus
const shareForm = share.shareForm
const showShareModal = share.showShareModal
const shareSaving = share.shareSaving
const shareRevoking = share.shareRevoking
const shareError = share.shareError
const shareSuccessMessage = share.shareSuccessMessage
const sharePasswordDisplay = share.sharePasswordDisplay
const shareCopyState = share.shareCopyState
const inlinePassword = share.inlinePassword
const passwordSaving = share.passwordSaving
const editingPassword = share.editingPassword
const tempPassword = share.tempPassword
const inlineExpiration = share.inlineExpiration
const expirationSaving = share.expirationSaving
const showPassword = share.showPassword
const editingExpiration = share.editingExpiration
const tempExpiration = share.tempExpiration
const showShareLink = share.showShareLink
const shareExpirationOptions = share.shareExpirationOptions
const shareExpirationDisplay = share.shareExpirationDisplay

const retrying = polling.retrying
const showRetryDialog = polling.showRetryDialog

const copiedStates = content.copiedStates
const detailsEditorRef = content.detailsEditorRef
const keyProcessEditorRef = content.keyProcessEditorRef

const showEditor = metadata.showEditor
const editorKey = metadata.editorKey
const editorValue = metadata.editorValue
const savingKeys = metadata.savingKeys
const errorsByKey = metadata.errorsByKey

// Use composable methods
const openEdit = metadata.openEdit
const openAdd = metadata.openAdd
const closeEditor = metadata.closeEditor
const saveEditor = metadata.saveEditor
const onChipsChange = metadata.onChipsChange
const onChipsSave = metadata.onChipsSave
const isSaving = metadata.isSaving
const fieldError = metadata.fieldError

const handleQuickShare = share.handleQuickShare
const openShareModal = share.openShareModal
const closeShareModal = share.closeShareModal
const handleShareSubmit = share.handleShareSubmit
const handleStopSharing = share.handleStopSharing
const confirmStopSharing = share.confirmStopSharing
const generateLocalPassword = share.generateLocalPassword
const copyLinkOnly = share.copyLinkOnly
const copyShareLink = share.copyShareLink
const copyFullInvite = share.copyFullInvite
const copySharePassword = share.copySharePassword
const createRandomPassword = share.createRandomPassword
const removePassword = share.removePassword
const startEditingPassword = share.startEditingPassword
const cancelEditingPassword = share.cancelEditingPassword
const savePassword = share.savePassword
const startEditingExpiration = share.startEditingExpiration
const cancelEditingExpiration = share.cancelEditingExpiration
const saveExpiration = share.saveExpiration

const handleRetryClick = () =>
  polling.handleRetryClick(isProcessing.value, deleting.value)
const handleRetry = polling.handleRetry
const stopRetryPolling = polling.stopRetryPolling

onMounted(() => {
  loadThreadline()
  document.addEventListener('click', handleClickOutside)
})

watch(
  () => route.params.id,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      stopRetryPolling()
      loadThreadline()
    }
  }
)

onUnmounted(() => {
  stopRetryPolling()
  document.removeEventListener('click', handleClickOutside)
})

const isAnySaving = computed(
  () => isSaving('category') || isSaving('participants') || isSaving('keywords')
)

// Use composable methods for todos
const threadlineTodos = todos.threadlineTodos
const showTodoEditor = todos.showTodoEditor
const editingTodo = todos.editingTodo
const savingTodo = todos.savingTodo
const todoLoading = todos.todoLoading
const todoErrorMessage = todos.todoErrorMessage
const todoSuccessMessage = todos.todoSuccessMessage
const tempNewTodo = todos.tempNewTodo
const savingNewTodo = todos.savingNewTodo
const editingTodoIds = todos.editingTodoIds
const handleAddTodo = todos.handleAddTodo
const saveNewTodo = todos.saveNewTodo
const cancelNewTodo = todos.cancelNewTodo
const handleTodoEditingChange = todos.handleTodoEditingChange
const handleEditTodo = todos.handleEditTodo
const handleSaveTodoInline = todos.handleSaveTodoInline
const handleSaveTodo = todos.handleSaveTodo
const handleToggleTodo = todos.handleToggleTodo
const handleDeleteTodo = todos.handleDeleteTodo

// Use composable methods for content editing
const editingTitle = content.editingTitle
const editingTitleValue = content.editingTitleValue
const savingTitle = content.savingTitle
const titleError = content.titleError
const titleInputRef = content.titleInputRef
const startEditingTitle = content.startEditingTitle
const cancelEditingTitle = content.cancelEditingTitle
const saveTitle = content.saveTitle

const detailsValue = content.detailsValue
const savingDetails = content.savingDetails
const detailsError = content.detailsError
const editingDetails = content.editingDetails
const cancelEditingDetails = content.cancelEditingDetails
const saveDetails = content.saveDetails

const keyProcessValue = content.keyProcessValue
const editingKeyProcess = content.editingKeyProcess
const savingKeyProcess = content.savingKeyProcess
const keyProcessError = content.keyProcessError
const cancelEditingKeyProcess = content.cancelEditingKeyProcess
const saveKeyProcess = content.saveKeyProcess

const copyContent = content.copyContent
const openDetailsEditor = content.openDetailsEditor
const openKeyProcessEditor = content.openKeyProcessEditor
const copyKeyProcess = content.copyKeyProcess

// Share button click handler - uses composable method
const handleShareButtonClick = async () => {
  if (!threadline.value) {
    return
  }

  if (shareSaving.value || shareRevoking.value) {
    return
  }

  if (
    shareStatus.value &&
    shareStatus.value.is_active &&
    !shareStatus.value.is_expired
  ) {
    handleStopSharing()
    return
  }

  if (isProcessing.value || deleting.value || retrying.value) {
    return
  }

  // Use handleQuickShare from composable
  await handleQuickShare()
}
</script>

<style scoped>
/* Todo list animation */
.todo-list-enter-active,
.todo-list-leave-active {
  transition: all 0.3s ease;
}

.todo-list-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.todo-list-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.todo-list-move {
  transition: transform 0.3s ease;
}
</style>
