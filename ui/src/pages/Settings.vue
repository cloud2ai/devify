<template>
  <AppLayout>
    <div class="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 class="text-xl font-bold leading-7 text-gray-900 sm:text-2xl">
          {{ t('settings.title') }}
        </h2>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('settings.preferences') }}
        </p>
      </div>

      <!-- User Profile Section -->
      <div class="bg-white rounded-lg border border-gray-200 p-4">
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

      <!-- Basic Information Card -->
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
          <!-- AI Email (First row) -->
          <div>
            <h4 class="text-sm font-medium text-gray-900 mb-2">
              {{ t('settings.aiEmail') }}
            </h4>
            <div class="bg-blue-50 rounded-lg p-3">
              <div class="flex items-center gap-2 mb-1">
                <svg
                  class="w-4 h-4 text-blue-600"
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
                <div class="text-sm text-blue-900 font-mono">
                  {{
                    userStore.userInfo?.virtual_email ||
                    t('settings.noVirtualEmail')
                  }}
                </div>
                <button
                  @click="copyEmail"
                  class="inline-flex items-center p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                  :title="emailCopied ? t('common.copied') : t('common.copy')"
                >
                  <svg
                    class="w-3 h-3"
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
                </button>
              </div>
              <div class="text-xs text-blue-700">
                {{ t('settings.loginEmailDesc') }}
              </div>
            </div>
          </div>

          <!-- Authentication Method -->
          <div>
            <h4 class="text-sm font-medium text-gray-900 mb-2">
              {{ t('settings.authMethod') }}
            </h4>
            <p class="text-sm text-gray-600 mb-3">
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
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                {{ t('settings.emailAuth') }}
              </span>
            </p>
          </div>

          <!-- Security Email -->
          <div v-if="authInfo && authInfo.method === 'email'">
            <h4 class="text-sm font-medium text-gray-900 mb-2">
              {{ t('settings.securityEmail') }}
            </h4>
            <div class="flex items-center gap-2 mb-1">
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
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
              <span class="text-sm text-gray-700">{{
                userStore.userInfo?.email || ''
              }}</span>
            </div>
            <div class="text-xs text-gray-500 ml-6">
              {{ t('settings.securityEmailDesc') }}
            </div>
          </div>

          <!-- OAuth Users -->
          <div v-else-if="authInfo && authInfo.method === 'oauth'" class="mt-2">
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
                <span class="text-xs font-medium text-green-800">{{
                  authInfo.provider || 'OAuth'
                }}</span>
              </div>
              <div class="text-sm text-green-900">
                {{ authInfo.login_identifier || '' }}
              </div>
            </div>
          </div>

          <!-- OAuth specific info -->
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
              <p v-if="authInfo.provider_email">
                <span class="font-medium">{{ t('settings.oauthEmail') }}:</span>
                {{ authInfo.provider_email }}
              </p>
            </div>
          </div>

          <!-- Password Reset Button -->
          <div
            v-if="authInfo?.can_change_password"
            class="flex justify-end mt-4"
          >
            <BaseButton
              variant="primary"
              class="w-full sm:w-auto"
              @click="showPasswordResetConfirm = true"
            >
              {{ t('settings.resetPassword') }}
            </BaseButton>
          </div>

          <!-- Password Change Info -->
          <div
            v-if="!authInfo?.can_change_password"
            class="bg-yellow-50 border border-yellow-200 rounded-lg p-3"
          >
            <div class="flex">
              <div class="flex-shrink-0">
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
              <div class="ml-3">
                <p class="text-sm text-yellow-700">
                  {{ t('settings.oauthPasswordChangeInfo') }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </BaseCard>

      <!-- Password Reset Success/Error Messages -->
      <div v-if="resetEmailSent || resetEmailError" class="mb-6">
        <!-- Password Reset Success Message -->
        <div v-if="resetEmailSent" class="rounded-md bg-green-50 p-4 mb-4">
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

        <!-- Password Reset Error Message -->
        <div v-if="resetEmailError" class="rounded-md bg-red-50 p-4 mb-4">
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
        <form @submit.prevent="saveSettings" class="space-y-3">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 items-start">
            <div class="md:col-span-1">
              <label
                for="language"
                class="block text-sm font-medium text-gray-700 mb-1"
              >
                {{ t('settings.language') }}
              </label>
              <p class="text-xs text-gray-500 mb-2 md:mb-0">
                {{ t('settings.languageDesc') }}
              </p>
            </div>
            <div class="md:col-span-2">
              <div class="relative">
                <select
                  id="language"
                  v-model="formData.language"
                  class="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 rounded-md shadow-sm appearance-none cursor-pointer hover:border-gray-400 transition-colors"
                >
                  <option value="en">{{ t('settings.languages.en') }}</option>
                  <option value="zh-CN">
                    {{ t('settings.languages.zh-CN') }}
                  </option>
                  <option value="es">{{ t('settings.languages.es') }}</option>
                </select>
                <div
                  class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2 text-gray-400"
                >
                  <svg
                    class="h-5 w-5"
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
                </div>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 items-start">
            <div class="md:col-span-1">
              <label
                for="scene"
                class="block text-sm font-medium text-gray-700 mb-1"
              >
                {{ t('settings.scene') }}
              </label>
              <p class="text-xs text-gray-500 mb-2 md:mb-0">
                {{ t('settings.sceneDesc') }}
              </p>
            </div>
            <div class="md:col-span-2">
              <div class="relative">
                <select
                  id="scene"
                  v-model="formData.scene"
                  class="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 rounded-md shadow-sm appearance-none cursor-pointer hover:border-gray-400 transition-colors disabled:bg-gray-50 disabled:cursor-not-allowed"
                  :disabled="loadingScenes"
                >
                  <option value="" disabled>
                    {{
                      loadingScenes
                        ? t('common.loading')
                        : t('auth.selectScene')
                    }}
                  </option>
                  <option
                    v-for="scene in scenes"
                    :key="scene.key"
                    :value="scene.key"
                  >
                    {{ scene.name
                    }}{{ scene.description ? ` - ${scene.description}` : '' }}
                  </option>
                </select>
                <div
                  class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2 text-gray-400"
                >
                  <svg
                    class="h-5 w-5"
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
                </div>
              </div>
            </div>
          </div>

          <div class="bg-blue-50 border border-blue-200 rounded-lg p-2.5">
            <div class="flex gap-2">
              <div class="flex-shrink-0 pt-0.5">
                <svg
                  class="h-4 w-4 text-blue-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="flex-1">
                <p class="text-xs leading-relaxed text-blue-700">
                  {{ t('settings.preferenceChangeWarning') }}
                </p>
              </div>
            </div>
          </div>

          <div v-if="errorMessage" class="rounded-md bg-red-50 p-2.5">
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
                <p class="text-xs font-medium text-red-800">
                  {{ errorMessage }}
                </p>
              </div>
            </div>
          </div>

          <div v-if="successMessage" class="rounded-md bg-green-50 p-2.5">
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
                <p class="text-xs font-medium text-green-800">
                  {{ successMessage }}
                </p>
              </div>
            </div>
          </div>

          <div class="flex justify-end mt-4">
            <BaseButton
              type="submit"
              variant="primary"
              class="w-full sm:w-auto"
              :loading="saving"
              :disabled="saving"
            >
              {{ saving ? t('common.loading') : t('settings.saveSettings') }}
            </BaseButton>
          </div>
        </form>
      </BaseCard>
    </div>

    <!-- Password Reset Confirmation Modal -->
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
              @click="showPasswordResetConfirm = false"
              class="text-gray-400 hover:text-gray-600"
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/store/user'
import { usePreferencesStore } from '@/store/preferences'
import { settingsApi } from '@/api/settings'
import { authApi } from '@/api/auth'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const { t, locale } = useI18n()
const userStore = useUserStore()
const preferencesStore = usePreferencesStore()

const formData = reactive({
  language: '',
  scene: ''
})

const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const emailCopied = ref(false)
const loadingScenes = ref(false)
const scenes = ref([])

// Password reset functionality
const sendingResetEmail = ref(false)
const resetEmailSent = ref(false)
const resetEmailError = ref('')
const showPasswordResetConfirm = ref(false)

const loadSettings = async () => {
  try {
    const preferences = await settingsApi.getPreferences()
    // Load AI prompt language from backend, not UI display language
    formData.language = preferences.language || 'en-US'
    formData.scene = preferences.scene || ''
  } catch (error) {
    console.error('Failed to load settings:', error)
    // Set defaults if load fails
    formData.language = 'en-US'
  }
}

const loadScenes = async () => {
  loadingScenes.value = true
  try {
    const response = await authApi.getAvailableScenes(locale.value)
    const responseData = response.data.data || response.data || []
    scenes.value = Array.isArray(responseData) ? responseData : []

    if (scenes.value.length > 0 && !formData.scene) {
      formData.scene = scenes.value[0].key
    }
  } catch (error) {
    console.error('Failed to load scenes:', error)
  } finally {
    loadingScenes.value = false
  }
}

watch(
  () => locale.value,
  () => {
    loadScenes()
  }
)

const userEmail = computed(
  () => userStore.userInfo?.virtual_email || 'user@example.com'
)

const authInfo = computed(() => userStore.userInfo?.auth_info || null)

const displayName = computed(() => {
  const userInfo = userStore.userInfo
  if (!userInfo) return 'User'

  // Prioritize display_name from backend (uses first_name + last_name for OAuth users)
  if (userInfo.display_name) {
    return userInfo.display_name
  }

  // Fallback to first_name + last_name if available
  if (userInfo.first_name && userInfo.last_name) {
    return `${userInfo.first_name} ${userInfo.last_name}`
  }

  // Fallback to first_name only
  if (userInfo.first_name) {
    return userInfo.first_name
  }

  // Final fallback to username
  return userInfo.username || 'User'
})

const userInitials = computed(() => {
  const name = displayName.value
  // Extract first character from display name
  const firstChar = name.trim().charAt(0).toUpperCase()
  return firstChar || 'U'
})

const avatarBgColor = computed(() => {
  // Generate consistent background color based on user's first initial
  const initial = userInitials.value
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

  // Use character code to deterministically select a color
  const charCode = initial.charCodeAt(0)
  const colorIndex = charCode % colors.length
  return colors[colorIndex]
})

const copyEmail = async () => {
  try {
    await navigator.clipboard.writeText(userEmail.value)
    emailCopied.value = true
    setTimeout(() => {
      emailCopied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy email:', error)
  }
}

const saveSettings = async () => {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await settingsApi.updatePreferences({
      language: formData.language,
      scene: formData.scene
    })

    // Note: Do NOT sync AI prompt language to UI display language
    // They should be independent settings

    successMessage.value = t('settings.settingsSaved')
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (error) {
    console.error('Failed to save settings:', error)
    errorMessage.value =
      error.response?.data?.message || t('settings.settingsError')
  } finally {
    saving.value = false
  }
}

// Password reset functions
const confirmPasswordReset = async () => {
  sendingResetEmail.value = true
  resetEmailError.value = ''
  resetEmailSent.value = false

  try {
    await authApi.resetPassword(userStore.userInfo?.email)
    resetEmailSent.value = true
    showPasswordResetConfirm.value = false

    // Show success message for 5 seconds
    setTimeout(() => {
      resetEmailSent.value = false
    }, 5000)
  } catch (error) {
    console.error('Password reset email failed:', error)

    // Handle different error response formats
    const responseData = error.response?.data
    if (responseData?.data?.error) {
      resetEmailError.value = responseData.data.error
    } else if (
      responseData?.data?.success === false &&
      responseData?.data?.error
    ) {
      resetEmailError.value = responseData.data.error
    } else if (responseData?.error) {
      resetEmailError.value = responseData.error
    } else if (responseData?.errors) {
      const errors = responseData.errors
      resetEmailError.value = Object.values(errors).flat().join(', ')
    } else if (responseData?.detail) {
      resetEmailError.value = responseData.detail
    } else if (responseData?.message) {
      resetEmailError.value = responseData.message
    } else {
      resetEmailError.value = t('settings.passwordResetError')
    }
  } finally {
    sendingResetEmail.value = false
  }
}

onMounted(async () => {
  // Ensure user data is loaded before rendering
  if (!userStore.user) {
    await userStore.checkAuthStatus()
  }

  // Load AI prompt language from backend (independent from UI display language)
  await loadSettings()

  // Load available scenes
  await loadScenes()

  // If no scene is set, use default from loaded scenes
  if (!formData.scene && scenes.value.length > 0) {
    formData.scene = scenes.value[0].key
  }
})
</script>
