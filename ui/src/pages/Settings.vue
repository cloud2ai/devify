<template>
  <AppLayout>
    <div class="max-w-5xl mx-auto space-y-6">
      <div class="space-y-1">
        <h2 class="text-xl font-bold leading-7 text-gray-900 sm:text-2xl">
          {{ t('settings.title') }}
        </h2>
        <p class="text-sm text-gray-500">
          {{ t('settings.subtitle') }}
        </p>
      </div>

      <div
        v-if="loadingSettings"
        class="rounded-md bg-gray-50 border border-gray-200 p-4 text-sm text-gray-600"
      >
        {{ t('settings.loadingSettings') }}
      </div>

      <div class="border-b border-gray-200">
        <div
          class="flex gap-6 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          role="tablist"
          aria-label="Settings categories"
        >
          <button
            v-for="tab in settingsTabs"
            :key="tab.value"
            type="button"
            class="flex-shrink-0 border-b-2 px-1 py-3 text-xs font-medium transition-colors sm:text-sm"
            role="tab"
            :aria-selected="activeSettingsTab === tab.value"
            :class="
              activeSettingsTab === tab.value
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            "
            @click="activeSettingsTab = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div v-if="activeSettingsTab === 'account'" class="space-y-6">
        <div class="bg-white rounded-lg border border-gray-200 p-4 sm:p-5">
          <div class="flex items-center gap-3">
            <div
              :class="avatarBgColor"
              class="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
            >
              <span class="text-white font-medium text-lg">
                {{ userInitials }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-lg font-semibold text-gray-900 truncate">
                {{ displayName }}
              </div>
              <div class="text-sm text-gray-500 truncate">
                {{ userStore.userInfo?.email || '' }}
              </div>
            </div>
          </div>
        </div>

        <BaseCard :header-muted="true">
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
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
              <h3 class="text-base font-semibold leading-5">
                {{ t('settings.basicInfo') }}
              </h3>
            </div>
          </template>

          <div class="space-y-4">
            <div>
              <h4 class="text-sm font-medium text-gray-900 mb-2">
                {{ t('settings.aiEmail') }}
              </h4>
              <div
                v-if="hasDisplayedAiEmail"
                class="rounded-lg border border-blue-200 bg-blue-50 p-3"
              >
                <div class="flex items-center justify-between gap-3">
                  <div class="min-w-0 flex-1">
                    <div
                      class="text-xs font-medium tracking-wide text-blue-700"
                    >
                      {{ t('settings.aiEmail') }}
                    </div>
                    <div class="mt-1 text-sm font-mono text-blue-900 truncate">
                      {{ displayedAiEmail }}
                    </div>
                  </div>
                  <button
                    type="button"
                    class="flex-shrink-0 inline-flex items-center text-xs font-medium text-blue-700 hover:text-blue-900 bg-blue-100 hover:bg-blue-200 px-2.5 py-1 rounded-md transition-colors"
                    @click="goToEmailSettings"
                  >
                    {{ t('settings.goToEmailSettings') }}
                  </button>
                </div>
                <div class="mt-2 text-xs leading-5 text-blue-700">
                  {{ t('settings.aiEmailDesc') }}
                </div>
              </div>

              <div
                v-else
                class="rounded-lg border border-amber-200 bg-amber-50 p-3"
              >
                <div class="flex items-start gap-2">
                  <svg
                    class="mt-0.5 h-4 w-4 flex-none text-amber-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01M10.29 3.86l-7.2 12.48A1.5 1.5 0 004.39 18h15.22a1.5 1.5 0 001.3-2.24l-7.2-12.48a1.5 1.5 0 00-2.62 0z"
                    />
                  </svg>
                  <div class="min-w-0 flex-1">
                    <p class="text-sm font-medium text-amber-900">
                      {{ t('settings.noAiEmailConfigured') }}
                    </p>
                    <p class="mt-1 text-xs leading-5 text-amber-800">
                      {{ t('settings.noAiEmailHint') }}
                    </p>
                    <button
                      type="button"
                      class="mt-2 inline-flex items-center text-xs font-medium text-amber-700 hover:text-amber-900"
                      @click="goToEmailSettings"
                    >
                      {{ t('settings.goToEmailSettings') }}
                      <svg
                        class="ml-1 h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h4 class="text-sm font-medium text-gray-900 mb-2">
                {{ t('settings.authMethod') }}
              </h4>
              <p class="text-sm text-gray-600">
                <span
                  v-if="authInfo && authInfo.method === 'email'"
                  class="inline-flex items-center"
                >
                  <svg
                    class="h-4 w-4 mr-1.5 text-blue-600"
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
                  {{ t('settings.emailAuth') }}
                </span>
                <span
                  v-else-if="authInfo && authInfo.method === 'oauth'"
                  class="inline-flex items-center"
                >
                  <svg
                    class="h-4 w-4 mr-1.5 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                  {{ t('settings.oauthAuth') }}
                </span>
                <span v-else class="inline-flex items-center">
                  {{ t('settings.emailAuth') }}
                </span>
              </p>
            </div>

            <div v-if="authInfo && authInfo.method === 'oauth'">
              <div class="bg-green-50 rounded-lg p-3">
                <div class="flex items-center gap-2 mb-1">
                  <svg
                    class="w-4 h-4 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                  <span class="text-xs font-medium text-green-800">
                    {{ authInfo.provider || 'OAuth' }}
                  </span>
                </div>
                <div class="text-sm text-green-900">
                  {{ authInfo.login_identifier || '' }}
                </div>
              </div>
            </div>

            <div
              v-if="authInfo?.method === 'oauth' && authInfo?.provider_email"
              class="bg-gray-50 rounded-lg p-3"
            >
              <div class="text-xs text-gray-500 space-y-1">
                <p>
                  <span class="font-medium"
                    >{{ t('settings.oauthProvider') }}:</span
                  >
                  {{ authInfo.provider }}
                </p>
                <p>
                  <span class="font-medium"
                    >{{ t('settings.oauthEmail') }}:</span
                  >
                  {{ authInfo.provider_email }}
                </p>
              </div>
            </div>

            <div v-if="authInfo?.can_change_password" class="flex justify-end">
              <BaseButton
                variant="primary"
                class="w-full sm:w-auto"
                @click="showPasswordResetConfirm = true"
              >
                {{ t('settings.resetPassword') }}
              </BaseButton>
            </div>

            <div
              v-if="!authInfo?.can_change_password"
              class="bg-yellow-50 border border-yellow-200 rounded-lg p-3"
            >
              <div class="flex gap-2">
                <div class="flex-shrink-0 pt-0.5">
                  <svg
                    class="h-5 w-5 text-yellow-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </div>
                <div class="ml-1">
                  <p class="text-sm text-yellow-700">
                    {{ t('settings.oauthPasswordChangeInfo') }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </BaseCard>

        <div v-if="resetEmailSent || resetEmailError" class="space-y-4">
          <div v-if="resetEmailSent" class="rounded-md bg-green-50 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg
                  class="h-5 w-5 text-green-400"
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
              <div class="ml-3">
                <p class="text-sm font-medium text-green-800">
                  {{ t('settings.passwordResetEmailSent') }}
                </p>
                <p class="text-xs text-green-700 mt-1">
                  {{ t('settings.passwordResetEmailSentDesc') }}
                </p>
              </div>
            </div>
          </div>

          <div v-if="resetEmailError" class="rounded-md bg-red-50 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg
                  class="h-5 w-5 text-red-400"
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
              <div class="ml-3">
                <p class="text-sm font-medium text-red-800">
                  {{ resetEmailError }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="activeSettingsTab === 'message'" class="space-y-6">
        <BaseCard :header-muted="true">
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
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              <h3 class="text-base font-semibold leading-5">
                {{ t('settings.preferences') }}
              </h3>
            </div>
          </template>

          <div class="space-y-5">
            <div
              class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
            >
              <div class="md:col-span-1">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ t('settings.language') }}
                </label>
                <p class="text-xs text-gray-500">
                  {{ t('settings.languageDesc') }}
                </p>
              </div>
              <div class="md:col-span-2">
                <select
                  v-model="preferenceForm.language"
                  class="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 rounded-md shadow-sm appearance-none cursor-pointer hover:border-gray-400 transition-colors"
                >
                  <option value="en">{{ t('settings.languages.en') }}</option>
                  <option value="zh-CN">
                    {{ t('settings.languages.zh-CN') }}
                  </option>
                  <option value="es">{{ t('settings.languages.es') }}</option>
                </select>
              </div>
            </div>

            <div
              class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
            >
              <div class="md:col-span-1">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ t('settings.timezone') }}
                </label>
                <p class="text-xs text-gray-500">
                  {{ t('settings.timezoneDesc') }}
                </p>
              </div>
              <div class="md:col-span-2">
                <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div class="text-sm font-medium text-gray-900">
                    {{ matchedTimezoneLabel }}
                  </div>
                  <div class="mt-1 text-xs text-gray-500">
                    {{ t('settings.detectedTimezone') }}:
                    {{ detectedTimezoneLabel }}
                  </div>
                </div>
              </div>
            </div>

            <div
              class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
            >
              <div class="md:col-span-1">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ t('settings.scene') }}
                </label>
                <p class="text-xs text-gray-500">
                  {{ t('settings.sceneDesc') }}
                </p>
              </div>
              <div class="md:col-span-2">
                <SceneSelector
                  v-model="preferenceForm.scene"
                  :label="''"
                  :error="''"
                />
              </div>
            </div>

            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p class="text-xs leading-relaxed text-blue-700">
                {{ t('settings.preferenceChangeWarning') }}
              </p>
            </div>

            <div v-if="preferenceError" class="rounded-md bg-red-50 p-3">
              <p class="text-sm text-red-700">{{ preferenceError }}</p>
            </div>

            <div v-if="preferenceSuccess" class="rounded-md bg-green-50 p-3">
              <p class="text-sm font-medium text-green-800">
                {{ preferenceSuccess }}
              </p>
            </div>

            <div class="flex justify-end">
              <BaseButton
                type="button"
                variant="primary"
                class="w-full sm:w-auto"
                :loading="savingPreferences"
                :disabled="savingPreferences"
                @click="savePreferences"
              >
                {{ savingPreferences ? t('common.saving') : t('common.save') }}
              </BaseButton>
            </div>
          </div>
        </BaseCard>
      </div>

      <div v-else-if="activeSettingsTab === 'email'" class="space-y-6">
        <BaseCard :header-muted="true">
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
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
              <h3 class="text-base font-semibold leading-5">
                {{ t('settings.emailConfigTitle') }}
              </h3>
            </div>
          </template>

          <div class="space-y-5">
            <div
              class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
            >
              <div class="md:col-span-1">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ t('settings.emailMode') }}
                </label>
                <p class="text-xs text-gray-500">
                  {{ t('settings.emailModeDesc') }}
                </p>
              </div>
              <div class="md:col-span-2">
                <select
                  v-model="emailForm.mode"
                  class="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 rounded-md shadow-sm appearance-none cursor-pointer hover:border-gray-400 transition-colors"
                >
                  <option value="auto_assign">
                    {{ t('settings.emailModeAutoAssign') }}
                  </option>
                  <option value="custom_imap">
                    {{ t('settings.emailModeCustomImap') }}
                  </option>
                </select>
                <div
                  v-if="emailForm.mode === 'auto_assign'"
                  class="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3"
                >
                  <div class="text-xs font-medium text-blue-700">
                    {{ t('settings.currentAutoAssignedEmail') }}
                  </div>
                  <div
                    class="mt-1 text-sm font-mono text-blue-900 truncate"
                    :title="autoAssignedEmail || t('settings.noVirtualEmail')"
                  >
                    {{ autoAssignedEmail || t('settings.noVirtualEmail') }}
                  </div>
                </div>
              </div>
            </div>

            <div
              v-if="emailForm.mode === 'custom_imap'"
              class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
            >
              <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <BaseInput
                  v-model="emailForm.imapHost"
                  :label="t('settings.imapHost')"
                  :placeholder="t('settings.imapHostPlaceholder')"
                />
                <BaseInput
                  v-model="emailForm.username"
                  :label="t('settings.imapUsername')"
                  :placeholder="t('settings.imapUsernamePlaceholder')"
                />
              </div>

              <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <BaseInput
                  v-model="emailForm.password"
                  :label="t('settings.imapPassword')"
                  type="password"
                  :placeholder="t('settings.imapPasswordPlaceholder')"
                />
                <BaseInput
                  v-model="emailForm.imapSslPort"
                  :label="t('settings.imapSslPort')"
                  type="number"
                  :placeholder="t('settings.imapSslPortPlaceholder')"
                />
              </div>

              <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <BaseInput
                  v-model="emailForm.folder"
                  :label="t('settings.imapFolder')"
                  :placeholder="t('settings.imapFolderPlaceholder')"
                />
                <BaseInput
                  v-model="emailForm.maxAgeDays"
                  :label="t('settings.maxAgeDays')"
                  type="number"
                  :placeholder="t('settings.maxAgeDaysPlaceholder')"
                />
              </div>

              <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <label class="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    v-model="emailForm.useSsl"
                    type="checkbox"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  {{ t('settings.useSsl') }}
                </label>

                <label class="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    v-model="emailForm.useStarttls"
                    type="checkbox"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  {{ t('settings.useStarttls') }}
                </label>

                <label class="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    v-model="emailForm.deleteAfterFetch"
                    type="checkbox"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  {{ t('settings.deleteAfterFetch') }}
                </label>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ t('settings.imapFilters') }}
                </label>
                <textarea
                  v-model="emailForm.filtersText"
                  class="input min-h-[96px]"
                  :placeholder="t('settings.imapFiltersPlaceholder')"
                />
                <p class="mt-1 text-xs text-gray-500">
                  {{ t('settings.imapFiltersHelp') }}
                </p>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ t('settings.excludePatterns') }}
                </label>
                <textarea
                  v-model="emailForm.excludePatternsText"
                  class="input min-h-[96px]"
                  :placeholder="t('settings.excludePatternsPlaceholder')"
                />
                <p class="mt-1 text-xs text-gray-500">
                  {{ t('settings.excludePatternsHelp') }}
                </p>
              </div>
            </div>

            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p class="text-xs leading-relaxed text-blue-700">
                {{ t('settings.emailConfigHint') }}
              </p>
            </div>

            <div v-if="emailError" class="rounded-md bg-red-50 p-3">
              <p class="text-sm text-red-700">{{ emailError }}</p>
            </div>

            <div v-if="emailSuccess" class="rounded-md bg-green-50 p-3">
              <p class="text-sm font-medium text-green-800">
                {{ emailSuccess }}
              </p>
            </div>

            <div class="flex justify-end">
              <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                <BaseButton
                  v-if="emailForm.mode === 'custom_imap'"
                  type="button"
                  variant="secondary"
                  class="w-full sm:w-auto"
                  :loading="validatingEmailConfig"
                  :disabled="validatingEmailConfig || savingEmailConfig"
                  @click="validateEmailConfigOnly"
                >
                  {{
                    validatingEmailConfig
                      ? t('settings.validatingConnection')
                      : t('settings.validateConnection')
                  }}
                </BaseButton>
                <BaseButton
                  type="button"
                  variant="primary"
                  class="w-full sm:w-auto"
                  :loading="savingEmailConfig"
                  :disabled="savingEmailConfig || validatingEmailConfig"
                  @click="saveEmailConfig"
                >
                  {{ saveEmailButtonLabel }}
                </BaseButton>
              </div>
            </div>
          </div>
        </BaseCard>
      </div>

      <div v-else class="space-y-6">
        <BaseCard :header-muted="true">
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
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              <h3 class="text-base font-semibold leading-5">
                {{ t('settings.issueConfigTitle') }}
              </h3>
            </div>
          </template>

          <div class="space-y-5">
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p class="text-xs leading-relaxed text-blue-700">
                {{ t('settings.issueConfigHint') }}
              </p>
            </div>

            <div class="rounded-lg border border-gray-200 bg-white p-3 sm:p-4 space-y-4">
              <label class="flex items-center gap-2 text-sm font-medium text-gray-700">
                <input
                  v-model="issueConfigForm.enable"
                  type="checkbox"
                  class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                {{ t('settings.issueEnabled') }}
              </label>
              <p class="text-xs text-gray-500">
                {{ t('settings.issueEnabledHelp') }}
              </p>

              <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                <div class="space-y-2">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('settings.issueEngine') }}
                    </label>
                    <p class="text-xs text-gray-500">
                      {{ t('settings.issueEngineHelp') }}
                    </p>
                  </div>
                  <select
                    v-model="issueConfigForm.issueEngine"
                    :disabled="!issueConfigForm.enable"
                    class="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 bg-white rounded-md shadow-sm appearance-none transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400 disabled:border-gray-200"
                  >
                    <option value="jira">
                      {{ t('settings.issueEngineJira') }}
                    </option>
                    <option value="feishu_bitable">
                      {{ t('settings.issueEngineFeishu') }}
                    </option>
                  </select>
                </div>

                <div class="space-y-2">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('settings.issueLanguage') }}
                    </label>
                    <p class="text-xs text-gray-500">
                      {{ t('settings.issueLanguageHelp') }}
                    </p>
                  </div>
                  <select
                    v-model="issueConfigForm.language"
                    :disabled="!issueConfigForm.enable"
                    class="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 bg-white rounded-md shadow-sm appearance-none transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400 disabled:border-gray-200"
                  >
                    <option value="Chinese">
                      {{ t('settings.issueLanguageChinese') }}
                    </option>
                    <option value="English">
                      {{ t('settings.issueLanguageEnglish') }}
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <div v-if="issueError" class="rounded-md bg-red-50 p-3">
              <p class="text-sm text-red-700">{{ issueError }}</p>
            </div>

            <div v-if="issueSuccess" class="rounded-md bg-green-50 p-3">
              <p class="text-sm font-medium text-green-800">
                {{ issueSuccess }}
              </p>
            </div>

            <div
              v-if="showJiraConfig"
              class="space-y-4 rounded-lg border border-gray-200 bg-gray-50/80 p-3 sm:p-4"
            >
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h4 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.jiraConfigTitle') }}
                  </h4>
                  <p class="mt-1 text-xs leading-5 text-gray-500">
                    {{ t('settings.jiraConfigDesc1') }}
                  </p>
                </div>
              </div>

              <div
                class="rounded-md border border-amber-200 bg-amber-50 p-2.5 text-xs leading-5 text-amber-800"
              >
                <p>{{ t('settings.jiraLegacyWarning') }}</p>
              </div>

              <div
                class="rounded-md border border-white bg-white p-3 space-y-3 sm:p-4"
              >
                <div class="space-y-1">
                  <h5 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.jiraConnectionTitle') }}
                  </h5>
                  <p class="text-xs leading-5 text-gray-500">
                    {{ t('settings.jiraConnectionDesc') }}
                  </p>
                </div>

                <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div class="space-y-1 lg:col-span-2">
                    <BaseInput
                      v-model="jiraForm.url"
                      :label="t('settings.jiraUrl')"
                      :placeholder="t('settings.jiraUrlPlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraUrlHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.username"
                      :label="t('settings.jiraUsername')"
                      :placeholder="t('settings.jiraUsernamePlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraUsernameHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.apiToken"
                      :label="t('settings.jiraApiToken')"
                      type="password"
                      :placeholder="t('settings.jiraApiTokenPlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraConnectionHelp') }}
                    </p>
                  </div>
                </div>
              </div>

              <div
                class="rounded-md border border-white bg-white p-3 space-y-3 sm:p-4"
              >
                <div class="space-y-1">
                  <h5 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.jiraRequiredFieldsTitle') }}
                  </h5>
                  <p class="text-xs leading-5 text-gray-500">
                    {{ t('settings.jiraRequiredFieldsDesc') }}
                  </p>
                </div>

                <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.projectKey"
                      :label="t('settings.jiraProjectKey')"
                      :placeholder="t('settings.jiraProjectKeyPlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraProjectKeyHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.issueType"
                      :label="t('settings.jiraIssueType')"
                      :placeholder="t('settings.jiraIssueTypePlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraIssueTypeHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.priority"
                      :label="t('settings.jiraPriority')"
                      :placeholder="t('settings.jiraPriorityPlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraPriorityHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.descriptionField"
                      :label="t('settings.jiraDescriptionField')"
                      :placeholder="
                        t('settings.jiraDescriptionFieldPlaceholder')
                      "
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraDescriptionFieldHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1 lg:col-span-2">
                    <BaseInput
                      v-model="jiraForm.summaryPrefix"
                      :label="t('settings.jiraSummaryPrefix')"
                      :placeholder="t('settings.jiraSummaryPrefixPlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraSummaryPrefixHelp') }}
                    </p>
                  </div>
                  <label class="flex items-start gap-2 text-sm text-gray-700">
                    <input
                      v-model="jiraForm.convertToJiraWiki"
                      type="checkbox"
                      class="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span>
                      {{ t('settings.jiraConvertToJiraWiki') }}
                      <span class="block text-xs text-gray-500">
                        {{ t('settings.jiraConvertToJiraWikiHelp') }}
                      </span>
                    </span>
                  </label>
                </div>

                <label class="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    v-model="jiraForm.addTimestamp"
                    type="checkbox"
                    class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  {{ t('settings.jiraSummaryAddTimestamp') }}
                </label>
              </div>

              <div
                class="rounded-md border border-white bg-white p-3 space-y-3 sm:p-4"
              >
                <div class="space-y-1">
                  <h5 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.jiraAssigneeSectionTitle') }}
                  </h5>
                  <p class="text-xs leading-5 text-gray-500">
                    {{ t('settings.jiraAssigneeSectionDesc') }}
                  </p>
                </div>

                <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.assigneeDefault"
                      :label="t('settings.jiraAssigneeDefault')"
                      :placeholder="
                        t('settings.jiraAssigneeDefaultPlaceholder')
                      "
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraAssigneeDefaultHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1 lg:col-span-2">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('settings.jiraAssigneeAllowValues') }}
                    </label>
                    <textarea
                      v-model="jiraForm.assigneeAllowValuesText"
                      class="input min-h-[88px]"
                      :placeholder="
                        t('settings.jiraAssigneeAllowValuesPlaceholder')
                      "
                    />
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('settings.jiraAssigneeAllowValuesHelp') }}
                    </p>
                  </div>
                  <label class="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      v-model="jiraForm.assigneeUseLlm"
                      type="checkbox"
                      class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    {{ t('settings.jiraAssigneeUseLlm') }}
                  </label>
                  <div
                    v-if="jiraForm.assigneeUseLlm"
                    class="space-y-1 lg:col-span-2"
                  >
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('settings.jiraAssigneePrompt') }}
                    </label>
                    <textarea
                      v-model="jiraForm.assigneePrompt"
                      class="input min-h-[96px]"
                      :placeholder="t('settings.jiraAssigneePromptPlaceholder')"
                    />
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('settings.jiraAssigneePromptHelp') }}
                    </p>
                  </div>
                </div>
              </div>

              <div
                class="rounded-md border border-white bg-white p-3 space-y-3 sm:p-4"
              >
                <div class="space-y-1">
                  <h5 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.jiraComponentsSectionTitle') }}
                  </h5>
                  <p class="text-xs leading-5 text-gray-500">
                    {{ t('settings.jiraComponentsSectionDesc') }}
                  </p>
                </div>

                <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div class="space-y-1 lg:col-span-2">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('settings.jiraComponentsDefault') }}
                    </label>
                    <textarea
                      v-model="jiraForm.componentsDefaultText"
                      class="input min-h-[88px]"
                      :placeholder="
                        t('settings.jiraComponentsDefaultPlaceholder')
                      "
                    />
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('settings.jiraComponentsDefaultHelp') }}
                    </p>
                  </div>
                  <label class="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      v-model="jiraForm.componentsUseLlm"
                      type="checkbox"
                      class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    {{ t('settings.jiraComponentsUseLlm') }}
                  </label>
                  <label class="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      v-model="jiraForm.componentsFetchFromApi"
                      type="checkbox"
                      class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    {{ t('settings.jiraComponentsFetchFromApi') }}
                  </label>
                </div>

                <div v-if="jiraForm.componentsUseLlm" class="space-y-1">
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ t('settings.jiraComponentsPrompt') }}
                  </label>
                  <textarea
                    v-model="jiraForm.componentsPrompt"
                    class="input min-h-[96px]"
                    :placeholder="t('settings.jiraComponentsPromptPlaceholder')"
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    {{ t('settings.jiraComponentsPromptHelp') }}
                  </p>
                </div>
              </div>

              <div
                class="rounded-lg border border-white bg-white p-4 space-y-4"
              >
                <div class="space-y-1">
                  <h5 class="text-sm font-semibold text-gray-900">
                    {{ t('settings.jiraEpicLinkSectionTitle') }}
                  </h5>
                  <p class="text-xs text-gray-500">
                    {{ t('settings.jiraEpicLinkSectionDesc') }}
                  </p>
                </div>

                <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.epicLinkDefault"
                      :label="t('settings.jiraEpicLinkDefault')"
                      :placeholder="
                        t('settings.jiraEpicLinkDefaultPlaceholder')
                      "
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraEpicLinkDefaultHelp') }}
                    </p>
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="jiraForm.epicLinkJqlFilter"
                      :label="t('settings.jiraEpicLinkJqlFilter')"
                      :placeholder="
                        t('settings.jiraEpicLinkJqlFilterPlaceholder')
                      "
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('settings.jiraEpicLinkJqlFilterHelp') }}
                    </p>
                  </div>
                  <label class="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      v-model="jiraForm.epicLinkUseLlm"
                      type="checkbox"
                      class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    {{ t('settings.jiraEpicLinkUseLlm') }}
                  </label>
                  <label class="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      v-model="jiraForm.epicLinkFetchFromApi"
                      type="checkbox"
                      class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    {{ t('settings.jiraEpicLinkFetchFromApi') }}
                  </label>
                </div>

                <div v-if="jiraForm.epicLinkUseLlm" class="space-y-1">
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ t('settings.jiraEpicLinkPrompt') }}
                  </label>
                  <textarea
                    v-model="jiraForm.epicLinkPrompt"
                    class="input min-h-[96px]"
                    :placeholder="t('settings.jiraEpicLinkPromptPlaceholder')"
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    {{ t('settings.jiraEpicLinkPromptHelp') }}
                  </p>
                </div>
              </div>

              <div class="rounded-md border border-white bg-white p-3 sm:p-4">
                <p class="text-xs leading-5 text-gray-500">
                  {{ t('settings.jiraConfigDesc2') }}
                </p>
              </div>
            </div>

            <div
              v-else-if="showFeishuConfig"
              class="space-y-4 rounded-lg border border-gray-200 bg-gray-50/80 p-3 sm:p-4"
            >
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h4 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.feishuConfigTitle') }}
                  </h4>
                  <p class="mt-1 text-xs leading-5 text-gray-500">
                    {{ t('settings.feishuConfigDesc1') }}
                  </p>
                  <p class="mt-1 text-xs leading-5 text-gray-500">
                    {{ t('settings.feishuConfigDesc2') }}
                  </p>
                </div>
              </div>

              <div
                class="rounded-md border border-white bg-white p-3 space-y-3 sm:p-4"
              >
                <div class="space-y-1">
                  <h5 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.feishuConnectionTitle') }}
                  </h5>
                  <p class="text-xs leading-5 text-gray-500">
                    {{ t('settings.feishuConnectionDesc') }}
                  </p>
                </div>

                <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.appId"
                      :label="t('settings.feishuAppId')"
                      :placeholder="t('settings.feishuAppIdPlaceholder')"
                    />
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.appSecret"
                      :label="t('settings.feishuAppSecret')"
                      type="password"
                      :placeholder="t('settings.feishuAppSecretPlaceholder')"
                    />
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.tenantAccessToken"
                      :label="t('settings.feishuTenantAccessToken')"
                      :placeholder="
                        t('settings.feishuTenantAccessTokenPlaceholder')
                      "
                    />
                  </div>
                  <div class="space-y-1 lg:col-span-2">
                    <BaseInput
                      v-model="feishuForm.appToken"
                      :label="t('settings.feishuAppToken')"
                      :placeholder="t('settings.feishuAppTokenPlaceholder')"
                    />
                  </div>
                </div>
              </div>

              <div
                class="rounded-md border border-white bg-white p-3 space-y-3 sm:p-4"
              >
                <div class="space-y-1">
                  <h5 class="text-sm font-semibold leading-5 text-gray-900">
                    {{ t('settings.feishuTableSectionTitle') }}
                  </h5>
                  <p class="text-xs leading-5 text-gray-500">
                    {{ t('settings.feishuTableSectionDesc') }}
                  </p>
                  <p class="text-xs leading-5 text-gray-500">
                    {{ t('settings.feishuTableSectionDesc2') }}
                  </p>
                </div>

                <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.defaultTableName"
                      :label="t('settings.feishuDefaultTableName')"
                      :placeholder="
                        t('settings.feishuDefaultTableNamePlaceholder')
                      "
                    />
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.tableName"
                      :label="t('settings.feishuTableName')"
                      :placeholder="t('settings.feishuTableNamePlaceholder')"
                    />
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.attachmentFieldName"
                      :label="t('settings.feishuAttachmentFieldName')"
                      :placeholder="
                        t('settings.feishuAttachmentFieldNamePlaceholder')
                      "
                    />
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.imageFieldName"
                      :label="t('settings.feishuImageFieldName')"
                      :placeholder="
                        t('settings.feishuImageFieldNamePlaceholder')
                      "
                    />
                  </div>
                  <div class="space-y-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('settings.feishuAttachmentUploadParentType') }}
                    </label>
                    <select
                      v-model="feishuForm.attachmentUploadParentType"
                      class="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 rounded-md shadow-sm appearance-none cursor-pointer hover:border-gray-400 transition-colors"
                    >
                      <option value="bitable">
                        {{
                          t('settings.feishuAttachmentUploadParentTypeBitable')
                        }}
                      </option>
                      <option value="folder">
                        {{
                          t('settings.feishuAttachmentUploadParentTypeFolder')
                        }}
                      </option>
                    </select>
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.attachmentUploadParentNode"
                      :label="t('settings.feishuAttachmentUploadParentNode')"
                      :placeholder="
                        t(
                          'settings.feishuAttachmentUploadParentNodePlaceholder'
                        )
                      "
                    />
                  </div>
                  <div class="space-y-1">
                    <BaseInput
                      v-model="feishuForm.attachmentUploadParentFolderToken"
                      :label="
                        t('settings.feishuAttachmentUploadParentFolderToken')
                      "
                      :placeholder="
                        t(
                          'settings.feishuAttachmentUploadParentFolderTokenPlaceholder'
                        )
                      "
                    />
                  </div>
                  <div class="space-y-1 lg:col-span-2">
                    <BaseInput
                      v-model="feishuForm.recordUrlTemplate"
                      :label="t('settings.feishuRecordUrlTemplate')"
                      :placeholder="
                        t('settings.feishuRecordUrlTemplatePlaceholder')
                      "
                    />
                  </div>
                </div>
              </div>

              <div
                class="rounded-md border border-white bg-white p-3 space-y-3 sm:p-4"
              >
                <div
                  class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div class="space-y-1">
                    <h5 class="text-sm font-semibold leading-5 text-gray-900">
                      {{ t('settings.feishuFieldMappings') }}
                    </h5>
                    <p class="text-xs leading-5 text-gray-500">
                      {{ t('settings.feishuFieldMappingsHelp') }}
                    </p>
                    <p class="text-xs leading-5 text-gray-500">
                      {{ t('settings.feishuFieldMappingsDetail') }}
                    </p>
                    <p class="text-xs leading-5 text-gray-500">
                      {{ t('settings.feishuAttachmentMappingHelp') }}
                    </p>
                  </div>
                  <BaseButton
                    variant="secondary"
                    size="sm"
                    type="button"
                    class="shrink-0 whitespace-nowrap self-start"
                    @click="addFeishuMapping"
                  >
                    {{ t('settings.addFeishuFieldMapping') }}
                  </BaseButton>
                </div>

                <div class="space-y-2.5">
                  <div
                    v-for="(mapping, index) in feishuFieldMappings"
                    :key="`${mapping.source}-${index}`"
                    class="grid grid-cols-1 gap-3 rounded-md border border-gray-200 bg-gray-50 p-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end"
                  >
                    <div class="min-w-0 space-y-1">
                      <BaseInput
                        v-model="mapping.source"
                        :label="t('settings.feishuFieldMappingSource')"
                        :placeholder="
                          t('settings.feishuFieldMappingSourcePlaceholder')
                        "
                      />
                    </div>
                    <div class="min-w-0 space-y-1">
                      <BaseInput
                        v-model="mapping.target"
                        :label="t('settings.feishuFieldMappingTarget')"
                        :placeholder="
                          t('settings.feishuFieldMappingTargetPlaceholder')
                        "
                      />
                    </div>
                    <div class="flex justify-end lg:self-end">
                      <BaseButton
                        variant="secondary"
                        type="button"
                        :disabled="feishuFieldMappings.length <= 1"
                        class="inline-flex h-8 w-8 items-center justify-center rounded-md border border-red-300 bg-red-50 text-red-700 shadow-sm transition-colors hover:border-red-400 hover:bg-red-100 hover:text-red-800 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-50 disabled:text-gray-300 disabled:shadow-none disabled:hover:bg-gray-50"
                        :title="t('common.delete')"
                        :aria-label="t('common.delete')"
                        @click="removeFeishuMapping(index)"
                      >
                        <span
                          class="text-base font-medium leading-none"
                          aria-hidden="true"
                        >
                          −
                        </span>
                        <span class="sr-only">{{ t('common.delete') }}</span>
                      </BaseButton>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div
              v-else
              class="rounded-md border border-dashed border-gray-300 bg-gray-50 p-3 text-sm text-gray-500"
            >
              {{ t('settings.issueDisabledHint') }}
            </div>

            <div class="flex flex-col gap-2 sm:flex-row sm:justify-end">
              <BaseButton
                v-if="showIssueTestButton"
                type="button"
                variant="secondary"
                size="sm"
                class="w-full sm:w-auto"
                :loading="testingIssueConfig"
                :disabled="testingIssueConfig || savingIssueConfig"
                @click="sendTestIssue"
              >
                {{ testTaskButtonLabel }}
              </BaseButton>
              <BaseButton
                type="button"
                variant="primary"
                size="sm"
                class="w-full sm:w-auto"
                :loading="savingIssueConfig"
                :disabled="savingIssueConfig || testingIssueConfig"
                @click="saveIssueConfig"
              >
                {{ saveIssueButtonLabel }}
              </BaseButton>
            </div>
          </div>
        </BaseCard>
      </div>
    </div>

    <div
      v-if="showPasswordResetConfirm"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click.self="showPasswordResetConfirm = false"
    >
      <div
        class="relative top-20 mx-auto p-6 border max-w-sm w-full shadow-lg rounded-md bg-white"
      >
        <div class="mt-3">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-gray-900">
              {{ t('settings.confirmPasswordReset') }}
            </h3>
            <button
              class="text-gray-400 hover:text-gray-600"
              @click="showPasswordResetConfirm = false"
            >
              <svg
                class="w-6 h-6"
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

          <div class="mb-6">
            <div class="flex items-start gap-3">
              <div class="flex-shrink-0">
                <svg
                  class="h-6 w-6 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <div>
                <p class="text-sm text-gray-700 mb-2">
                  {{ t('settings.passwordResetConfirmDesc') }}
                </p>
                <div class="bg-gray-50 rounded-lg p-3">
                  <div class="text-sm font-medium text-gray-900 mb-1">
                    {{ t('settings.securityEmail') }}
                  </div>
                  <div class="text-sm text-gray-700">
                    {{ userStore.userInfo?.email || '' }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end space-x-3">
            <BaseButton
              variant="secondary"
              @click="showPasswordResetConfirm = false"
            >
              {{ t('common.cancel') }}
            </BaseButton>
            <BaseButton
              variant="primary"
              :loading="sendingResetEmail"
              :disabled="sendingResetEmail"
              @click="confirmPasswordReset"
            >
              {{
                sendingResetEmail
                  ? t('settings.sendingResetEmail')
                  : t('settings.sendPasswordReset')
              }}
            </BaseButton>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/store/user'
import { usePreferencesStore } from '@/store/preferences'
import { authApi } from '@/api/auth'
import { settingsApi } from '@/api/settings'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import SceneSelector from '@/components/ui/SceneSelector.vue'
import { getTimezoneLabel } from '@/utils/timezones'

const { t } = useI18n()
const userStore = useUserStore()
const preferencesStore = usePreferencesStore()

const activeSettingsTab = ref('account')
const loadingSettings = ref(false)
const savingPreferences = ref(false)
const savingEmailConfig = ref(false)
const savingIssueConfig = ref(false)
const testingIssueConfig = ref(false)
const validatingEmailConfig = ref(false)
const errorMessage = ref('')
const preferenceError = ref('')
const preferenceSuccess = ref('')
const emailError = ref('')
const emailSuccess = ref('')
const issueError = ref('')
const issueSuccess = ref('')

const sendingResetEmail = ref(false)
const resetEmailSent = ref(false)
const resetEmailError = ref('')
const showPasswordResetConfirm = ref(false)

const preferenceForm = reactive({
  language: 'en',
  timezone: 'UTC',
  scene: ''
})

const emailForm = reactive({
  mode: 'auto_assign',
  imapHost: '',
  username: '',
  password: '',
  imapSslPort: 993,
  useSsl: true,
  useStarttls: false,
  deleteAfterFetch: false,
  folder: 'INBOX',
  filtersText: '',
  excludePatternsText: '',
  maxAgeDays: 7
})

const issueConfigForm = reactive({
  enable: false,
  issueEngine: 'jira',
  language: 'Chinese'
})

const jiraForm = reactive({
  url: '',
  username: '',
  apiToken: '',
  projectKey: '',
  issueType: '',
  priority: '',
  summaryPrefix: '',
  addTimestamp: true,
  descriptionField: 'description',
  convertToJiraWiki: true,
  assigneeUseLlm: true,
  assigneeDefault: '',
  assigneeAllowValuesText: '',
  assigneePrompt: '',
  componentsUseLlm: false,
  componentsFetchFromApi: false,
  componentsDefaultText: '',
  componentsPrompt: '',
  epicLinkUseLlm: true,
  epicLinkFetchFromApi: true,
  epicLinkDefault: '',
  epicLinkJqlFilter: '',
  epicLinkPrompt: ''
})

const feishuForm = reactive({
  appId: '',
  appSecret: '',
  tenantAccessToken: '',
  appToken: '',
  defaultTableName: '',
  tableName: '',
  attachmentFieldName: '',
  imageFieldName: '',
  attachmentUploadParentType: 'bitable',
  attachmentUploadParentNode: '',
  attachmentUploadParentFolderToken: '',
  recordUrlTemplate: ''
})

const feishuFieldMappings = ref([
  { source: '任务简述', target: 'title' },
  { source: '需求收集管理', target: 'summary_content' },
  { source: '备注', target: 'llm_content' },
  { source: '优先级', target: 'feishu_priority' },
  { source: '状态', target: 'feishu_status' },
  { source: 'SourceID', target: 'email_id_str' }
])

const issueConfigRaw = ref({})

const settingsTabs = computed(() => [
  {
    value: 'account',
    label: t('settings.basicInfo')
  },
  {
    value: 'message',
    label: t('settings.preferences')
  },
  {
    value: 'email',
    label: t('settings.emailConfigTitle')
  },
  {
    value: 'sync',
    label: t('settings.issueConfigTitle')
  }
])

const authInfo = computed(() => userStore.userInfo?.auth_info || null)

const displayedAiEmail = computed(() => {
  const customImapEmail =
    emailForm.mode === 'custom_imap' ? emailForm.username.trim() : ''
  if (customImapEmail) {
    return customImapEmail
  }

  return userStore.userInfo?.virtual_email?.trim() || ''
})

const hasDisplayedAiEmail = computed(() => Boolean(displayedAiEmail.value))

const autoAssignedEmail = computed(() => {
  return userStore.userInfo?.virtual_email?.trim() || ''
})

const saveEmailButtonLabel = computed(() => {
  return savingEmailConfig.value ? t('common.saving') : t('common.save')
})

const saveIssueButtonLabel = computed(() => {
  return savingIssueConfig.value
    ? t('common.saving')
    : t('settings.saveIssueConfig')
})

const testTaskButtonLabel = computed(() => {
  return testingIssueConfig.value
    ? t('settings.sendingTestIssue')
    : t('settings.sendTestIssue')
})

const displayName = computed(() => {
  const userInfo = userStore.userInfo
  if (!userInfo) return 'User'
  if (userInfo.display_name) return userInfo.display_name
  if (userInfo.first_name && userInfo.last_name) {
    return `${userInfo.first_name} ${userInfo.last_name}`
  }
  if (userInfo.first_name) return userInfo.first_name
  return userInfo.username || 'User'
})

const userInitials = computed(() => {
  const name = displayName.value || 'User'
  return name.trim().charAt(0).toUpperCase() || 'U'
})

const avatarBgColor = computed(() => {
  const colors = [
    'bg-blue-500',
    'bg-indigo-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-rose-500',
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-yellow-500',
    'bg-lime-500',
    'bg-green-500',
    'bg-emerald-500',
    'bg-teal-500',
    'bg-cyan-500',
    'bg-sky-500'
  ]
  return colors[userInitials.value.charCodeAt(0) % colors.length]
})

const detectedTimezoneLabel = computed(() => {
  return getTimezoneLabel(preferencesStore.detectedTimezone || 'UTC')
})

const matchedTimezoneLabel = computed(() => {
  const timezone = preferenceForm.timezone || preferencesStore.detectedTimezone
  return getTimezoneLabel(timezone || 'UTC')
})

const showJiraConfig = computed(
  () => issueConfigForm.enable && issueConfigForm.issueEngine === 'jira'
)

const showFeishuConfig = computed(
  () =>
    issueConfigForm.enable && issueConfigForm.issueEngine === 'feishu_bitable'
)

const showIssueTestButton = computed(() => {
  return (
    issueConfigForm.enable &&
    ['jira', 'feishu_bitable'].includes(issueConfigForm.issueEngine)
  )
})

function goToEmailSettings() {
  activeSettingsTab.value = 'email'
}

function parseListValue(text) {
  return text
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function normalizeUiLanguageCode(language) {
  if (!language || typeof language !== 'string') {
    return 'en'
  }

  const value = language.trim().toLowerCase()
  if (value.startsWith('zh')) {
    return 'zh-CN'
  }
  if (value.startsWith('es')) {
    return 'es'
  }
  return 'en'
}

function formatListValue(value) {
  if (!Array.isArray(value)) return ''
  return value.join('\n')
}

function normalizeEmailConfig(value) {
  const raw = value && typeof value === 'object' ? value : {}
  const imapConfig =
    raw.imap_config && typeof raw.imap_config === 'object'
      ? raw.imap_config
      : {}
  const filterConfig =
    raw.filter_config && typeof raw.filter_config === 'object'
      ? raw.filter_config
      : {}

  emailForm.mode = raw.mode || 'auto_assign'
  emailForm.imapHost = imapConfig.imap_host || ''
  emailForm.username = imapConfig.username || ''
  emailForm.password = imapConfig.password || ''
  emailForm.imapSslPort = imapConfig.imap_ssl_port || 993
  emailForm.useSsl =
    imapConfig.use_ssl !== undefined ? Boolean(imapConfig.use_ssl) : true
  emailForm.useStarttls = Boolean(imapConfig.use_starttls)
  emailForm.deleteAfterFetch = Boolean(imapConfig.delete_after_fetch)
  emailForm.folder = filterConfig.folder || 'INBOX'
  emailForm.filtersText = formatListValue(filterConfig.filters)
  emailForm.excludePatternsText = formatListValue(filterConfig.exclude_patterns)
  emailForm.maxAgeDays = filterConfig.max_age_days || 7
}

function normalizeIssueConfig(value) {
  const raw = value && typeof value === 'object' ? value : {}
  const jiraConfig = raw.jira && typeof raw.jira === 'object' ? raw.jira : {}
  const fields = raw.fields && typeof raw.fields === 'object' ? raw.fields : {}
  const feishuConfig =
    raw.feishu_bitable && typeof raw.feishu_bitable === 'object'
      ? raw.feishu_bitable
      : raw.feishu && typeof raw.feishu === 'object'
        ? raw.feishu
        : {}

  issueConfigRaw.value = raw
  issueConfigForm.enable = Boolean(raw.enable)
  issueConfigForm.issueEngine = raw.issue_engine || 'jira'
  issueConfigForm.language = raw.language || 'Chinese'

  jiraForm.url = jiraConfig.url || ''
  jiraForm.username = jiraConfig.username || ''
  jiraForm.apiToken = jiraConfig.api_token || ''
  jiraForm.projectKey = fields.project_key_config?.default || ''
  jiraForm.issueType = fields.issue_type_config?.default || ''
  jiraForm.priority = fields.priority_config?.default || ''
  jiraForm.summaryPrefix = fields.summary_config?.prefix || '[AI]'
  jiraForm.addTimestamp = Boolean(fields.summary_config?.add_timestamp)
  jiraForm.descriptionField =
    fields.description_config?.jira_field || 'description'
  jiraForm.convertToJiraWiki = Boolean(
    fields.description_config?.convert_to_jira_wiki !== undefined
      ? fields.description_config.convert_to_jira_wiki
      : true
  )
  jiraForm.assigneeUseLlm =
    fields.assignee_config?.use_llm !== undefined
      ? Boolean(fields.assignee_config.use_llm)
      : true
  jiraForm.assigneeDefault = fields.assignee_config?.default || ''
  jiraForm.assigneeAllowValuesText = formatListValue(
    fields.assignee_config?.allow_values
  )
  jiraForm.assigneePrompt = fields.assignee_config?.prompt || ''
  jiraForm.componentsUseLlm =
    fields.components_config?.use_llm !== undefined
      ? Boolean(fields.components_config.use_llm)
      : false
  jiraForm.componentsFetchFromApi =
    fields.components_config?.fetch_from_api !== undefined
      ? Boolean(fields.components_config.fetch_from_api)
      : false
  jiraForm.componentsDefaultText = formatListValue(
    fields.components_config?.default
  )
  jiraForm.componentsPrompt = fields.components_config?.prompt || ''
  jiraForm.epicLinkUseLlm =
    fields.epic_link_config?.use_llm !== undefined
      ? Boolean(fields.epic_link_config.use_llm)
      : true
  jiraForm.epicLinkFetchFromApi =
    fields.epic_link_config?.fetch_from_api !== undefined
      ? Boolean(fields.epic_link_config.fetch_from_api)
      : true
  jiraForm.epicLinkDefault = fields.epic_link_config?.default || ''
  jiraForm.epicLinkJqlFilter = fields.epic_link_config?.jql_filter || ''
  jiraForm.epicLinkPrompt = fields.epic_link_config?.prompt || ''

  feishuForm.appId = feishuConfig.app_id || ''
  feishuForm.appSecret = feishuConfig.app_secret || ''
  feishuForm.tenantAccessToken = feishuConfig.tenant_access_token || ''
  feishuForm.appToken = feishuConfig.app_token || ''
  feishuForm.defaultTableName = feishuConfig.default_table_name || ''
  feishuForm.tableName = feishuConfig.table_name || ''
  feishuForm.attachmentFieldName = feishuConfig.attachment_field_name || ''
  feishuForm.imageFieldName = feishuConfig.image_field_name || ''
  feishuForm.attachmentUploadParentType =
    feishuConfig.attachment_upload_parent_type || 'bitable'
  feishuForm.attachmentUploadParentNode =
    feishuConfig.attachment_upload_parent_node || ''
  feishuForm.attachmentUploadParentFolderToken =
    feishuConfig.attachment_upload_parent_folder_token || ''
  feishuForm.recordUrlTemplate = feishuConfig.record_url_template || ''

  const fieldMappings = feishuConfig.field_mappings || {}
  const mappingEntries = Object.entries(fieldMappings)
  feishuFieldMappings.value = mappingEntries.length
    ? mappingEntries.map(([source, target]) => ({
        source,
        target: String(target || '')
      }))
    : [
        { source: '任务简述', target: 'title' },
        { source: '需求收集管理', target: 'summary_content' },
        { source: '备注', target: 'llm_content' },
        { source: '优先级', target: 'feishu_priority' },
        { source: '状态', target: 'feishu_status' },
        { source: 'SourceID', target: 'email_id_str' }
      ]
}

function buildIssueConfigPayload() {
  const payload = JSON.parse(JSON.stringify(issueConfigRaw.value || {}))

  payload.enable = Boolean(issueConfigForm.enable)
  payload.issue_engine = issueConfigForm.issueEngine
  payload.language = issueConfigForm.language
  payload.jira = {
    ...(payload.jira && typeof payload.jira === 'object' ? payload.jira : {}),
    url: jiraForm.url.trim(),
    username: jiraForm.username.trim(),
    api_token: jiraForm.apiToken
  }
  payload.fields = {
    ...(payload.fields && typeof payload.fields === 'object'
      ? payload.fields
      : {}),
    project_key_config: {
      jira_field: 'project',
      default: jiraForm.projectKey.trim()
    },
    issue_type_config: {
      jira_field: 'issuetype',
      default: jiraForm.issueType.trim()
    },
    priority_config: {
      jira_field: 'priority',
      default: jiraForm.priority.trim()
    },
    summary_config: {
      prefix: jiraForm.summaryPrefix.trim() || '[AI]',
      add_timestamp: Boolean(jiraForm.addTimestamp)
    },
    description_config: {
      jira_field: jiraForm.descriptionField.trim() || 'description',
      convert_to_jira_wiki: Boolean(jiraForm.convertToJiraWiki)
    },
    assignee_config: {
      use_llm: Boolean(jiraForm.assigneeUseLlm),
      jira_field: 'assignee',
      default: jiraForm.assigneeDefault.trim(),
      allow_values: parseListValue(jiraForm.assigneeAllowValuesText),
      prompt: jiraForm.assigneePrompt.trim()
    },
    epic_link_config: {
      use_llm: Boolean(jiraForm.epicLinkUseLlm),
      fetch_from_api: Boolean(jiraForm.epicLinkFetchFromApi),
      jira_field: 'customfield_10014',
      default: jiraForm.epicLinkDefault.trim(),
      jql_filter: jiraForm.epicLinkJqlFilter.trim(),
      prompt: jiraForm.epicLinkPrompt.trim()
    }
  }
  const componentsDefault = parseListValue(jiraForm.componentsDefaultText)
  const componentsConfig = {
    use_llm: Boolean(jiraForm.componentsUseLlm),
    fetch_from_api: Boolean(jiraForm.componentsFetchFromApi),
    jira_field: 'components',
    default: componentsDefault,
    prompt: jiraForm.componentsPrompt.trim()
  }
  if (
    componentsConfig.use_llm ||
    componentsConfig.fetch_from_api ||
    componentsConfig.default.length > 0 ||
    componentsConfig.prompt
  ) {
    payload.fields.components_config = componentsConfig
  } else {
    delete payload.fields.components_config
  }
  payload.feishu_bitable = {
    ...(payload.feishu_bitable && typeof payload.feishu_bitable === 'object'
      ? payload.feishu_bitable
      : payload.feishu && typeof payload.feishu === 'object'
        ? payload.feishu
        : {}),
    base_url: 'https://open.feishu.cn/open-apis',
    app_id: feishuForm.appId.trim(),
    app_secret: feishuForm.appSecret,
    tenant_access_token: feishuForm.tenantAccessToken.trim(),
    app_token: feishuForm.appToken.trim(),
    default_table_name: feishuForm.defaultTableName.trim(),
    table_name: feishuForm.tableName.trim(),
    attachment_field_name: feishuForm.attachmentFieldName.trim(),
    image_field_name: feishuForm.imageFieldName.trim(),
    attachment_upload_parent_type: feishuForm.attachmentUploadParentType,
    attachment_upload_parent_node: feishuForm.attachmentUploadParentNode.trim(),
    attachment_upload_parent_folder_token:
      feishuForm.attachmentUploadParentFolderToken.trim(),
    record_url_template: feishuForm.recordUrlTemplate.trim(),
    field_mappings: Object.fromEntries(
      feishuFieldMappings.value
        .map((mapping) => [mapping.source.trim(), mapping.target.trim()])
        .filter(([source, target]) => source && target)
    )
  }

  return payload
}

function validateJiraConfig() {
  const missingFields = []
  if (!jiraForm.url.trim()) missingFields.push(t('settings.jiraUrl'))
  if (!jiraForm.username.trim()) missingFields.push(t('settings.jiraUsername'))
  if (!jiraForm.apiToken.trim()) missingFields.push(t('settings.jiraApiToken'))

  if (issueConfigForm.enable && issueConfigForm.issueEngine === 'jira') {
    if (!jiraForm.projectKey.trim()) {
      missingFields.push(t('settings.jiraProjectKey'))
    }
    if (!jiraForm.issueType.trim()) {
      missingFields.push(t('settings.jiraIssueType'))
    }
  }

  if (missingFields.length) {
    return `${t('settings.settingsError')}: ${missingFields.join(', ')}`
  }

  return null
}

function validateFeishuConfig() {
  const missingFields = []
  if (!feishuForm.appId.trim()) missingFields.push(t('settings.feishuAppId'))
  if (!feishuForm.appSecret.trim()) {
    missingFields.push(t('settings.feishuAppSecret'))
  }
  if (!feishuForm.appToken.trim())
    missingFields.push(t('settings.feishuAppToken'))
  if (!feishuForm.tableName.trim() && !feishuForm.defaultTableName.trim()) {
    missingFields.push(t('settings.feishuTableName'))
  }

  if (
    issueConfigForm.enable &&
    issueConfigForm.issueEngine === 'feishu_bitable'
  ) {
    if (
      !feishuFieldMappings.value.some(
        (mapping) => mapping.source.trim() && mapping.target.trim()
      )
    ) {
      missingFields.push(t('settings.feishuFieldMappings'))
    }
  }

  if (missingFields.length) {
    return `${t('settings.settingsError')}: ${missingFields.join(', ')}`
  }

  return null
}
function validateIssueConfig() {
  if (!['jira', 'feishu_bitable'].includes(issueConfigForm.issueEngine)) {
    return t('settings.issueEngineInvalid')
  }

  if (!issueConfigForm.enable) {
    return null
  }

  if (issueConfigForm.issueEngine === 'jira') {
    return validateJiraConfig()
  }

  if (issueConfigForm.issueEngine === 'feishu_bitable') {
    return validateFeishuConfig()
  }

  return null
}
function buildEmailConfig() {
  return {
    mode: emailForm.mode,
    imap_config: {
      imap_host: emailForm.imapHost.trim(),
      username: emailForm.username.trim(),
      password: emailForm.password,
      imap_ssl_port: Number(emailForm.imapSslPort) || 993,
      use_ssl: Boolean(emailForm.useSsl),
      use_starttls: Boolean(emailForm.useStarttls),
      delete_after_fetch: Boolean(emailForm.deleteAfterFetch)
    },
    filter_config: {
      folder: emailForm.folder.trim() || 'INBOX',
      filters: parseListValue(emailForm.filtersText),
      exclude_patterns: parseListValue(emailForm.excludePatternsText),
      max_age_days: Number(emailForm.maxAgeDays) || 7
    }
  }
}

function extractErrorMessage(error, fallback) {
  return (
    error?.response?.data?.message ||
    error?.response?.data?.error ||
    error?.response?.data?.detail ||
    error?.response?.data?.data?.error ||
    fallback
  )
}

async function loadSettings() {
  loadingSettings.value = true
  errorMessage.value = ''

  try {
    if (!userStore.userInfo || !userStore.userInfo.virtual_email) {
      await userStore.checkAuthStatus()
    }

    const settingsList = await settingsApi.getSettingsList()
    const settingsByKey = Object.fromEntries(
      settingsList.map((setting) => [setting.key, setting])
    )

    const profile = userStore.userInfo?.profile || {}
    const promptConfig = settingsByKey.prompt_config?.value || {}

    preferenceForm.language = normalizeUiLanguageCode(
      promptConfig.language || profile.language || 'en'
    )
    preferenceForm.timezone =
      profile.timezone ||
      preferencesStore.currentTimezone ||
      preferencesStore.detectedTimezone ||
      'UTC'
    preferenceForm.scene = promptConfig.scene || ''

    normalizeEmailConfig(settingsByKey.email_config?.value)

    normalizeIssueConfig(settingsByKey.issue_config?.value)
  } catch (error) {
    console.error('Failed to load settings:', error)
    errorMessage.value = extractErrorMessage(error, t('settings.settingsError'))
    normalizeIssueConfig({
      enable: false,
      issue_engine: 'jira',
      language: 'Chinese'
    })
  } finally {
    loadingSettings.value = false
  }
}

function clearSectionFeedback(section) {
  if (section === 'preference') {
    preferenceError.value = ''
    preferenceSuccess.value = ''
  } else if (section === 'email') {
    emailError.value = ''
    emailSuccess.value = ''
  } else if (section === 'issue') {
    issueError.value = ''
    issueSuccess.value = ''
  }
}

function setSectionSuccess(section, message) {
  if (section === 'preference') {
    preferenceSuccess.value = message
    setTimeout(() => {
      if (preferenceSuccess.value === message) {
        preferenceSuccess.value = ''
      }
    }, 3000)
  } else if (section === 'email') {
    emailSuccess.value = message
    setTimeout(() => {
      if (emailSuccess.value === message) {
        emailSuccess.value = ''
      }
    }, 3000)
  } else if (section === 'issue') {
    issueSuccess.value = message
    setTimeout(() => {
      if (issueSuccess.value === message) {
        issueSuccess.value = ''
      }
    }, 3000)
  }
}

function setSectionError(section, message) {
  if (section === 'preference') {
    preferenceError.value = message
  } else if (section === 'email') {
    emailError.value = message
  } else if (section === 'issue') {
    issueError.value = message
  }
}

function validateEmailConfig() {
  if (emailForm.mode !== 'custom_imap') {
    return null
  }

  const missingFields = []
  if (!emailForm.imapHost.trim()) missingFields.push(t('settings.imapHost'))
  if (!emailForm.username.trim()) missingFields.push(t('settings.imapUsername'))
  if (!emailForm.password) missingFields.push(t('settings.imapPassword'))

  const port = Number(emailForm.imapSslPort)
  if (!Number.isInteger(port) || port <= 0) {
    missingFields.push(t('settings.imapSslPort'))
  }

  if (missingFields.length) {
    return `${t('settings.settingsError')}: ${missingFields.join(', ')}`
  }

  return null
}

function addFeishuMapping() {
  feishuFieldMappings.value.push({ source: '', target: '' })
}

function removeFeishuMapping(index) {
  if (feishuFieldMappings.value.length <= 1) {
    return
  }
  feishuFieldMappings.value.splice(index, 1)
}

async function savePreferences() {
  savingPreferences.value = true
  clearSectionFeedback('preference')

  try {
    await userStore.updateProfile({
      language: preferenceForm.language,
      timezone: preferenceForm.timezone
    })

    await settingsApi.saveSettingByKey({
      key: 'prompt_config',
      value: {
        language: preferenceForm.language,
        scene: preferenceForm.scene
      },
      description: 'User prompt configuration (language and scene)'
    })

    preferencesStore.setTimezone(preferenceForm.timezone)
    preferencesStore.loadFromBackend({
      language: preferenceForm.language,
      scene: preferenceForm.scene
    })

    setSectionSuccess('preference', t('settings.settingsSaved'))
  } catch (error) {
    console.error('Failed to save preferences:', error)
    setSectionError(
      'preference',
      extractErrorMessage(error, t('settings.settingsError'))
    )
  } finally {
    savingPreferences.value = false
  }
}

async function saveEmailConfig() {
  savingEmailConfig.value = true
  clearSectionFeedback('email')

  try {
    const nextEmailConfig = buildEmailConfig()
    const validationError = validateEmailConfig()
    if (validationError) {
      throw new Error(validationError)
    }

    if (emailForm.mode === 'custom_imap') {
      await settingsApi.validateImapConfig(nextEmailConfig)
    }

    await settingsApi.saveSettingByKey({
      key: 'email_config',
      value: nextEmailConfig,
      description: 'User email configuration'
    })

    setSectionSuccess('email', t('settings.settingsSaved'))
  } catch (error) {
    console.error('Failed to save email config:', error)
    setSectionError(
      'email',
      extractErrorMessage(error, t('settings.settingsError'))
    )
  } finally {
    savingEmailConfig.value = false
  }
}

async function validateEmailConfigOnly() {
  clearSectionFeedback('email')

  const validationError = validateEmailConfig()
  if (validationError) {
    setSectionError('email', validationError)
    return
  }

  if (emailForm.mode !== 'custom_imap') {
    setSectionSuccess('email', t('settings.emailValidationNotRequired'))
    return
  }

  validatingEmailConfig.value = true

  try {
    await settingsApi.validateImapConfig(buildEmailConfig())
    setSectionSuccess('email', t('settings.imapValidationPassed'))
  } catch (error) {
    console.error('Failed to validate IMAP config:', error)
    setSectionError(
      'email',
      extractErrorMessage(error, t('settings.imapValidationFailed'))
    )
  } finally {
    validatingEmailConfig.value = false
  }
}

async function saveIssueConfig() {
  savingIssueConfig.value = true
  clearSectionFeedback('issue')

  try {
    const validationError = validateIssueConfig()
    if (validationError) {
      throw new Error(validationError)
    }

    const nextIssueConfig = buildIssueConfigPayload()
    await settingsApi.saveSettingByKey({
      key: 'issue_config',
      value: nextIssueConfig,
      description: 'User issue creation configuration'
    })

    issueConfigRaw.value = nextIssueConfig
    setSectionSuccess('issue', t('settings.settingsSaved'))
  } catch (error) {
    console.error('Failed to save issue config:', error)
    setSectionError(
      'issue',
      extractErrorMessage(error, t('settings.settingsError'))
    )
  } finally {
    savingIssueConfig.value = false
  }
}

async function sendTestIssue() {
  clearSectionFeedback('issue')

  const validationError = validateIssueConfig()
  if (validationError) {
    setSectionError('issue', validationError)
    return
  }

  testingIssueConfig.value = true

  try {
    const response = await settingsApi.testIssueConfig(
      buildIssueConfigPayload()
    )
    const data = response?.data?.data || response?.data || {}
    const issueKey = data.issue_key || data.record_id || data.key || ''
    const issueUrl = data.issue_url || data.url || ''
    const successMessage = issueKey
      ? t('settings.testIssueSuccessWithKey', { key: issueKey })
      : t('settings.testIssueSuccess')
    setSectionSuccess(
      'issue',
      issueUrl ? `${successMessage} ${issueUrl}` : successMessage
    )
  } catch (error) {
    console.error('Failed to send test issue:', error)
    setSectionError(
      'issue',
      extractErrorMessage(error, t('settings.testIssueFailed'))
    )
  } finally {
    testingIssueConfig.value = false
  }
}

async function confirmPasswordReset() {
  sendingResetEmail.value = true
  resetEmailError.value = ''
  resetEmailSent.value = false

  try {
    await authApi.resetPassword(userStore.userInfo?.email)
    resetEmailSent.value = true
    showPasswordResetConfirm.value = false

    setTimeout(() => {
      resetEmailSent.value = false
    }, 5000)
  } catch (error) {
    console.error('Password reset email failed:', error)
    resetEmailError.value = extractErrorMessage(
      error,
      t('settings.passwordResetError')
    )
  } finally {
    sendingResetEmail.value = false
  }
}

onMounted(async () => {
  await loadSettings()
})
</script>
