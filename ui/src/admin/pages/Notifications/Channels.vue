<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('notificationManagement.channels.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('notificationManagement.channels.subtitle') }}
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
              @click="loadList"
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
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span class="sr-only">{{ t('common.refresh') }}</span>
            </BaseButton>
            <BaseButton variant="primary" size="sm" @click="openAddModal">
              {{ t('notificationManagement.channels.addChannel') }}
            </BaseButton>
          </div>

          <BaseLoading v-if="loading" />
          <template v-else>
            <div
              v-if="list.length === 0"
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
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              <p class="text-sm font-medium text-gray-600">
                {{ t('notificationManagement.channels.noChannels') }}
              </p>
            </div>
            <div
              v-else
              class="overflow-x-auto rounded-lg border border-gray-200"
            >
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.channels.channelType') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.channels.name') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.channels.scope') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.channels.configSummary') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.channels.isActive') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.channels.actions') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                  <tr
                    v-for="row in list"
                    :key="row.uuid"
                    class="hover:bg-gray-50"
                  >
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-900"
                    >
                      {{ channelTypeLabel(row.channel_type) }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-700"
                    >
                      {{ row.name || '–' }}
                    </td>
                    <td class="px-4 py-3 whitespace-nowrap text-sm">
                      <span
                        v-if="row.scope === 'global'"
                        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
                      >
                        {{ t('notificationManagement.channels.scopeGlobal') }}
                      </span>
                      <span v-else class="text-gray-700">{{
                        row.user_display || '–'
                      }}</span>
                    </td>
                    <td
                      class="px-4 py-3 text-sm text-gray-600 max-w-xs truncate"
                    >
                      {{ configSummary(row) }}
                    </td>
                    <td class="px-4 py-3 whitespace-nowrap text-sm">
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
                    <td class="px-4 py-3 whitespace-nowrap text-right">
                      <div class="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          :title="t('common.edit')"
                          class="inline-flex items-center justify-center rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                          @click="openEditModal(row)"
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
                          @click="confirmDelete(row)"
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
        :show="showModal"
        :title="
          editingId
            ? t('notificationManagement.channels.editChannelTitle')
            : t('notificationManagement.channels.addChannelTitle')
        "
        @close="closeModal"
      >
        <form @submit.prevent="submitForm" class="space-y-4">
          <p v-if="editingId" class="text-xs text-gray-500 mb-2">
            {{ t('notificationManagement.channels.editSaveHint') }}
          </p>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('notificationManagement.channels.channelType')
            }}</label>
            <select
              v-model="form.channel_type"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white"
              :disabled="!!editingId"
              required
            >
              <option value="webhook">
                {{ t('notificationManagement.channels.typeWebhook') }}
              </option>
              <option value="email">
                {{ t('notificationManagement.channels.typeEmail') }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('notificationManagement.channels.name')
            }}</label>
            <input
              v-model="form.name"
              type="text"
              class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              :placeholder="
                t('notificationManagement.channels.namePlaceholder')
              "
            />
          </div>
          <template v-if="form.channel_type === 'webhook'">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{
                t('notificationManagement.channels.providerType')
              }}</label>
              <select
                v-model="form.config.provider_type"
                class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white"
                required
              >
                <option value="feishu">飞书</option>
                <option value="wecom">WeCom</option>
                <option value="wechat">企业微信</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{
                t('notificationManagement.channels.url')
              }}</label>
              <input
                v-model="form.config.url"
                type="url"
                class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                required
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{
                t('notificationManagement.channels.messagePrefix')
              }}</label>
              <input
                v-model="form.config.message_prefix"
                type="text"
                class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                :placeholder="
                  t('notificationManagement.channels.messagePrefixPlaceholder')
                "
              />
              <p class="mt-1 text-xs text-gray-500">
                {{ t('notificationManagement.channels.messagePrefixDesc') }}
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{
                t('notificationManagement.channels.language')
              }}</label>
              <select
                v-model="form.config.language"
                class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white"
              >
                <option value="zh-hans">
                  {{ t('notificationManagement.channels.languageZhHans') }}
                </option>
                <option value="en">
                  {{ t('notificationManagement.channels.languageEn') }}
                </option>
              </select>
              <p class="mt-1 text-xs text-gray-500">
                {{ t('notificationManagement.channels.languageDesc') }}
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{
                t('notificationManagement.channels.signSecret')
              }}</label>
              <input
                v-model="form.config.sign_secret"
                type="password"
                autocomplete="off"
                class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                :placeholder="
                  t('notificationManagement.channels.signSecretPlaceholder')
                "
              />
              <p class="mt-1 text-xs text-gray-500">
                {{
                  editingId
                    ? t('notificationManagement.channels.signSecretEditHint')
                    : t('notificationManagement.channels.signSecretDesc')
                }}
              </p>
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
                {{ t('notificationManagement.channels.mergeOptions') }}
              </h3>
              <div class="space-y-3">
                <div>
                  <label class="flex cursor-pointer items-center gap-3">
                    <input
                      v-model="form.config.merge_enabled"
                      type="checkbox"
                      class="h-4 w-4 shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span class="text-sm font-medium text-gray-700">{{
                      t('notificationManagement.channels.mergeEnabled')
                    }}</span>
                  </label>
                  <p class="mt-1.5 ml-7 text-xs text-gray-500">
                    {{ t('notificationManagement.channels.mergeEnabledDesc') }}
                  </p>
                </div>
                <div
                  v-if="form.config.merge_enabled"
                  class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1"
                >
                  <div>
                    <label
                      class="block text-xs font-medium text-gray-600 mb-1"
                      >{{
                        t('notificationManagement.channels.mergeWindowMinutes')
                      }}</label
                    >
                    <input
                      v-model.number="form.config.merge_window_minutes"
                      type="number"
                      min="0"
                      max="1440"
                      class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                    />
                    <p class="mt-1 text-xs text-gray-500">
                      {{
                        t(
                          'notificationManagement.channels.mergeWindowMinutesDesc'
                        )
                      }}
                    </p>
                  </div>
                </div>
              </div>
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
                    d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                  />
                </svg>
                {{ t('notificationManagement.channels.silenceOptions') }}
              </h3>
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">{{
                  t('notificationManagement.channels.silenceWindowMinutes')
                }}</label>
                <input
                  v-model.number="form.config.silence_window_minutes"
                  type="number"
                  min="0"
                  max="1440"
                  class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                />
                <p class="mt-1 text-xs text-gray-500">
                  {{
                    t(
                      'notificationManagement.channels.silenceWindowMinutesDesc'
                    )
                  }}
                </p>
              </div>
            </div>
          </template>
          <template v-if="form.channel_type === 'email'">
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
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                {{ t('notificationManagement.channels.smtpOptions') }}
              </h3>
              <div class="space-y-3">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label
                      class="block text-xs font-medium text-gray-600 mb-1"
                      >{{
                        t('notificationManagement.channels.smtpHost')
                      }}</label
                    >
                    <input
                      v-model="form.config.smtp_host"
                      type="text"
                      class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                      placeholder="smtp.example.com"
                    />
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-gray-600 mb-1"
                      >{{
                        t('notificationManagement.channels.smtpPort')
                      }}</label
                    >
                    <input
                      v-model.number="form.config.smtp_port"
                      type="number"
                      min="1"
                      max="65535"
                      class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                      placeholder="587"
                    />
                  </div>
                </div>
                <label class="flex cursor-pointer items-center gap-3">
                  <input
                    v-model="form.config.use_tls"
                    type="checkbox"
                    class="h-4 w-4 shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span class="text-sm font-medium text-gray-700">{{
                    t('notificationManagement.channels.useTls')
                  }}</span>
                </label>
                <label class="flex cursor-pointer items-center gap-3">
                  <input
                    v-model="form.config.use_ssl"
                    type="checkbox"
                    class="h-4 w-4 shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span class="text-sm font-medium text-gray-700">{{
                    t('notificationManagement.channels.useSsl')
                  }}</span>
                </label>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{
                    t('notificationManagement.channels.smtpUser')
                  }}</label>
                  <input
                    v-model="form.config.smtp_user"
                    type="text"
                    class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{
                    t('notificationManagement.channels.smtpPassword')
                  }}</label>
                  <input
                    v-model="form.config.smtp_password"
                    type="password"
                    autocomplete="new-password"
                    class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    :placeholder="
                      editingId
                        ? t(
                            'notificationManagement.channels.smtpPasswordEditHint'
                          )
                        : ''
                    "
                  />
                  <p v-if="editingId" class="mt-1 text-xs text-gray-500">
                    {{
                      t('notificationManagement.channels.smtpPasswordEditHint')
                    }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{
                    t('notificationManagement.channels.fromEmail')
                  }}</label>
                  <input
                    v-model="form.config.from_email"
                    type="email"
                    class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    placeholder="noreply@example.com"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{
                    t('notificationManagement.channels.fromName')
                  }}</label>
                  <input
                    v-model="form.config.from_name"
                    type="text"
                    class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    :placeholder="
                      t('notificationManagement.channels.fromNamePlaceholder')
                    "
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    {{ t('notificationManagement.channels.fromNameDesc') }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">{{
                    t('notificationManagement.channels.subjectPrefix')
                  }}</label>
                  <input
                    v-model="form.config.subject_prefix"
                    type="text"
                    class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    :placeholder="
                      t(
                        'notificationManagement.channels.subjectPrefixPlaceholder'
                      )
                    "
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    {{ t('notificationManagement.channels.subjectPrefixDesc') }}
                  </p>
                </div>
              </div>
            </div>
          </template>
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
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              {{ t('notificationManagement.channels.statusOptions') }}
            </h3>
            <div class="space-y-3">
              <div>
                <label class="flex cursor-pointer items-center gap-3">
                  <input
                    v-model="form.is_active"
                    type="checkbox"
                    class="h-4 w-4 shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span class="text-sm font-medium text-gray-700">{{
                    t('notificationManagement.channels.isActive')
                  }}</span>
                </label>
                <p class="mt-1.5 ml-7 text-xs text-gray-500">
                  {{ t('notificationManagement.channels.isActiveDesc') }}
                </p>
              </div>
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
            class="flex flex-wrap items-center justify-end gap-3 pt-2 border-t border-gray-200"
          >
            <BaseButton
              type="button"
              variant="outline"
              :loading="validating"
              :disabled="validationSuccess"
              @click="validateForm"
            >
              {{ t('notificationManagement.channels.validate') }}
            </BaseButton>
            <BaseButton type="button" variant="outline" @click="closeModal">
              {{ t('common.cancel') }}
            </BaseButton>
            <BaseButton
              type="submit"
              variant="primary"
              :loading="saving"
              :disabled="submitDisabled"
            >
              {{
                editingId
                  ? t('common.save')
                  : t('notificationManagement.channels.addChannel')
              }}
            </BaseButton>
          </div>
        </form>
      </BaseModal>

      <BaseModal
        :show="showDeleteConfirm"
        :title="t('notificationManagement.channels.delete')"
        @close="showDeleteConfirm = false"
      >
        <p class="text-sm text-gray-700 mb-4">
          {{ t('notificationManagement.channels.confirmDelete') }}
        </p>
        <div class="flex flex-wrap items-center justify-end gap-3">
          <BaseButton variant="outline" @click="showDeleteConfirm = false">
            {{ t('common.cancel') }}
          </BaseButton>
          <BaseButton
            variant="primary"
            :loading="deleting"
            class="bg-red-600 hover:bg-red-700"
            @click="doDelete"
          >
            {{ t('common.delete') }}
          </BaseButton>
        </div>
      </BaseModal>

      <BaseModal
        :show="showValidateEmailModal"
        :title="t('notificationManagement.channels.validateEmailDialogTitle')"
        @close="closeValidateEmailModal"
      >
        <p class="text-sm text-gray-700 mb-3">
          {{ t('notificationManagement.channels.validateEmailDialogDesc') }}
        </p>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{
            t('notificationManagement.channels.testRecipientEmail')
          }}</label>
          <input
            v-model="validateModalRecipient"
            type="email"
            class="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            :placeholder="
              t('notificationManagement.channels.testRecipientEmailPlaceholder')
            "
          />
          <p class="mt-1 text-xs text-gray-500">
            {{ t('notificationManagement.channels.testRecipientEmailDesc') }}
          </p>
        </div>
        <div class="flex flex-wrap items-center justify-end gap-3">
          <BaseButton variant="outline" @click="closeValidateEmailModal">
            {{ t('common.cancel') }}
          </BaseButton>
          <BaseButton
            variant="primary"
            :loading="validating"
            @click="confirmValidateEmail"
          >
            {{ t('notificationManagement.channels.validate') }}
          </BaseButton>
        </div>
      </BaseModal>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { notificationsAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BaseModal from '@/components/ui/BaseModal.vue'

const { t } = useI18n()
const { showSuccess, showError } = useToast()

const loading = ref(false)
const list = ref([])
const showModal = ref(false)
const showDeleteConfirm = ref(false)
const editingId = ref(null)
const saving = ref(false)
const validating = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const formMessage = ref('')
const formMessageSuccess = ref(false)
const validationSuccess = ref(false)
const showValidateEmailModal = ref(false)
const validateModalRecipient = ref('')
const isOpeningEdit = ref(false)

const defaultWebhookConfig = () => ({
  provider_type: 'feishu',
  url: '',
  message_prefix: '',
  language: 'zh-hans',
  sign_secret: '',
  merge_enabled: false,
  merge_window_minutes: 0,
  silence_window_minutes: 0
})
const defaultEmailConfig = () => ({
  smtp_host: '',
  smtp_port: 587,
  use_tls: true,
  use_ssl: false,
  smtp_user: '',
  smtp_password: '',
  from_email: '',
  from_name: '',
  subject_prefix: ''
})

const form = reactive({
  channel_type: 'webhook',
  name: '',
  is_active: true,
  config: defaultWebhookConfig()
})

const channelTypeLabels = {
  webhook: 'notificationManagement.channels.typeWebhook',
  email: 'notificationManagement.channels.typeEmail'
}
const providerLabels = { feishu: '飞书', wecom: 'WeCom', wechat: '企业微信' }

function channelTypeLabel(type) {
  return t(channelTypeLabels[type] || type || '–')
}

function normalizeConfig(rawConfig) {
  if (rawConfig && typeof rawConfig === 'object') {
    return { ...rawConfig }
  }
  if (typeof rawConfig === 'string' && rawConfig.trim()) {
    try {
      const parsed = JSON.parse(rawConfig)
      if (parsed && typeof parsed === 'object') {
        return parsed
      }
    } catch (e) {
      return {}
    }
  }
  return {}
}

const submitDisabled = computed(() => {
  return !validationSuccess.value
})

watch(
  () => [form.channel_type, form.config?.url, form.config?.sign_secret],
  () => {
    if (form.channel_type === 'webhook') {
      validationSuccess.value = false
    }
  }
)

watch(
  () => form.config?.use_tls,
  (useTls) => {
    if (form.channel_type !== 'email') return
    if (useTls) {
      form.config.use_ssl = false
    }
  }
)

watch(
  () => form.config?.use_ssl,
  (useSsl) => {
    if (form.channel_type !== 'email') return
    if (useSsl) {
      form.config.use_tls = false
    }
  }
)

async function validateForm() {
  formMessage.value = ''
  if (form.channel_type === 'webhook') {
    const url = (form.config.url || '').trim()
    if (!url) {
      formMessage.value = t(
        'notificationManagement.channels.validateUrlRequired'
      )
      formMessageSuccess.value = false
      return
    }
    try {
      new URL(url)
    } catch {
      formMessage.value = t(
        'notificationManagement.channels.validateUrlInvalid'
      )
      formMessageSuccess.value = false
      return
    }
  } else if (form.channel_type === 'email') {
    const host = (form.config.smtp_host || '').trim()
    if (!host) {
      formMessage.value = t(
        'notificationManagement.channels.validateSmtpHostRequired'
      )
      formMessageSuccess.value = false
      return
    }
    const from = (form.config.from_email || '').trim()
    if (!from) {
      formMessage.value = t(
        'notificationManagement.channels.validateFromEmailRequired'
      )
      formMessageSuccess.value = false
      return
    }
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRe.test(from)) {
      formMessage.value = t(
        'notificationManagement.channels.validateFromEmailInvalid'
      )
      formMessageSuccess.value = false
      return
    }
    showValidateEmailModal.value = true
    validateModalRecipient.value = ''
    return
  }
  validating.value = true
  try {
    const body = {
      channel_type: form.channel_type,
      config:
        form.channel_type === 'webhook'
          ? {
              provider_type: form.config.provider_type || 'feishu',
              url: (form.config.url || '').trim(),
              message_prefix:
                (form.config.message_prefix || '').trim() || undefined,
              language: form.config.language || 'zh-hans',
              sign_secret: (form.config.sign_secret || '').trim() || undefined
            }
          : {
              smtp_host: (form.config.smtp_host || '').trim(),
              smtp_port: Math.max(
                1,
                Math.min(65535, Number(form.config.smtp_port) || 587)
              ),
              use_tls: !!form.config.use_tls,
              use_ssl: !!form.config.use_ssl,
              smtp_user: (form.config.smtp_user || '').trim() || undefined,
              smtp_password:
                (form.config.smtp_password || '').trim() || undefined,
              from_email: (form.config.from_email || '').trim()
            }
    }
    if (editingId.value) body.channel_uuid = editingId.value
    await notificationsAdminApi.validateChannel(body)
    formMessage.value = t('notificationManagement.channels.validateSuccess')
    formMessageSuccess.value = true
    validationSuccess.value = true
  } catch (err) {
    const msg = err?.message || ''
    formMessage.value =
      msg && msg !== 'Request failed with status code 400'
        ? msg
        : t('notificationManagement.channels.validateFailed')
    formMessageSuccess.value = false
  } finally {
    validating.value = false
  }
}

function closeValidateEmailModal() {
  showValidateEmailModal.value = false
  validateModalRecipient.value = ''
}

async function confirmValidateEmail() {
  formMessage.value = ''
  const body = {
    channel_type: 'email',
    config: {
      smtp_host: (form.config.smtp_host || '').trim(),
      smtp_port: Math.max(
        1,
        Math.min(65535, Number(form.config.smtp_port) || 587)
      ),
      use_tls: !!form.config.use_tls,
      use_ssl: !!form.config.use_ssl,
      smtp_user: (form.config.smtp_user || '').trim() || undefined,
      smtp_password: (form.config.smtp_password || '').trim() || undefined,
      from_email: (form.config.from_email || '').trim()
    }
  }
  if (editingId.value) body.channel_uuid = editingId.value
  const to = (validateModalRecipient.value || '').trim()
  if (to) body.test_recipient = to
  validating.value = true
  try {
    await notificationsAdminApi.validateChannel(body)
    formMessage.value = t('notificationManagement.channels.validateSuccess')
    formMessageSuccess.value = true
    validationSuccess.value = true
    closeValidateEmailModal()
  } catch (err) {
    const msg = err?.message || ''
    formMessage.value =
      msg && msg !== 'Request failed with status code 400'
        ? msg
        : t('notificationManagement.channels.validateFailed')
    formMessageSuccess.value = false
    closeValidateEmailModal()
  } finally {
    validating.value = false
  }
}

const languageLabels = { 'zh-hans': '简体中文', en: 'English' }
function configSummary(row) {
  if (!row.config || typeof row.config !== 'object') return '–'
  if (row.channel_type === 'webhook') {
    const p = row.config.provider_type
    const label = providerLabels[p] || p || ''
    const url = row.config.url
      ? `${row.config.url.slice(0, 40)}${row.config.url.length > 40 ? '…' : ''}`
      : ''
    const lang = row.config.language
      ? languageLabels[row.config.language] || row.config.language
      : ''
    const parts = [label, url].filter(Boolean)
    if (lang) parts.push(lang)
    return parts.length ? parts.join(' · ') : '–'
  }
  if (row.channel_type === 'email') {
    const host = row.config.smtp_host || ''
    const from = row.config.from_email || ''
    if (host && from) return `${host} · ${from}`
    return host || from || '–'
  }
  const str = JSON.stringify(row.config)
  return str.length > 60 ? str.slice(0, 60) + '…' : str || '–'
}

function resetForm() {
  form.channel_type = 'webhook'
  form.name = ''
  form.is_active = true
  form.config = defaultWebhookConfig()
  editingId.value = null
  formMessage.value = ''
  formMessageSuccess.value = false
  validationSuccess.value = false
}

watch(
  () => form.channel_type,
  (type) => {
    if (isOpeningEdit.value) return
    validationSuccess.value = false
    if (type === 'email') {
      form.config = defaultEmailConfig()
    } else {
      form.config = defaultWebhookConfig()
    }
  }
)

watch(
  () => form.config,
  () => {
    if (isOpeningEdit.value) return
    validationSuccess.value = false
  },
  { deep: true }
)

function openAddModal() {
  resetForm()
  showModal.value = true
}

function openEditModal(row) {
  isOpeningEdit.value = true
  editingId.value = row.uuid
  form.channel_type = row.channel_type
  form.name = row.name || ''
  form.is_active = !!row.is_active
  const config = normalizeConfig(row.config)
  if (row.channel_type === 'webhook') {
    const c = config
    form.config = {
      ...defaultWebhookConfig(),
      ...c,
      provider_type: c.provider_type || 'feishu',
      message_prefix: (c.message_prefix || '').trim(),
      language: c.language || 'zh-hans',
      sign_secret: (c.sign_secret || '').trim(),
      merge_window_minutes: c.merge_window_minutes ?? 0,
      silence_window_minutes: Math.max(
        0,
        Math.min(1440, Number(c.silence_window_minutes) ?? 0)
      )
    }
  } else if (row.channel_type === 'email') {
    const c = config
    form.config = {
      ...defaultEmailConfig(),
      ...c,
      smtp_port: c.smtp_port ?? 587,
      use_tls: c.use_tls !== false,
      use_ssl: c.use_ssl === true
    }
  } else {
    form.config = config
  }
  showModal.value = true
  nextTick(() => {
    isOpeningEdit.value = false
    validationSuccess.value = true
  })
}

function closeModal() {
  showModal.value = false
  resetForm()
}

async function loadList() {
  loading.value = true
  try {
    const data = await notificationsAdminApi.getChannels()
    const rawList = Array.isArray(data)
      ? data
      : Array.isArray(data?.results)
        ? data.results
        : []
    list.value = rawList.map((row) => ({
      ...row,
      config: normalizeConfig(row?.config)
    }))
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function submitForm() {
  saving.value = true
  formMessage.value = ''
  try {
    let config
    if (form.channel_type === 'webhook') {
      config = {
        provider_type: form.config.provider_type,
        url: (form.config.url || '').trim(),
        message_prefix: (form.config.message_prefix || '').trim(),
        language: form.config.language || 'zh-hans',
        sign_secret: (form.config.sign_secret || '').trim() || undefined,
        merge_enabled: !!form.config.merge_enabled,
        merge_window_minutes: Math.max(
          0,
          Math.min(1440, Number(form.config.merge_window_minutes) || 0)
        ),
        silence_window_minutes: Math.max(
          0,
          Math.min(1440, Number(form.config.silence_window_minutes) ?? 0)
        )
      }
    } else if (form.channel_type === 'email') {
      config = {
        smtp_host: (form.config.smtp_host || '').trim(),
        smtp_port: Math.max(
          1,
          Math.min(65535, Number(form.config.smtp_port) || 587)
        ),
        use_tls: !!form.config.use_tls,
        use_ssl: !!form.config.use_ssl,
        smtp_user: (form.config.smtp_user || '').trim(),
        smtp_password: (form.config.smtp_password || '').trim(),
        from_email: (form.config.from_email || '').trim(),
        from_name: (form.config.from_name || '').trim(),
        subject_prefix: (form.config.subject_prefix || '').trim()
      }
    } else {
      config = form.config && typeof form.config === 'object' ? form.config : {}
    }
    const payload = {
      channel_type: form.channel_type,
      name: form.name.trim(),
      is_active: form.is_active,
      config
    }
    if (editingId.value) {
      await notificationsAdminApi.putChannel(editingId.value, payload)
      showSuccess(t('notificationManagement.channels.saveSuccess'))
    } else {
      await notificationsAdminApi.postChannel(payload)
      showSuccess(t('notificationManagement.channels.saveSuccess'))
    }
    closeModal()
    loadList()
  } catch (e) {
    showError(
      e?.response?.data?.detail ||
        e?.message ||
        t('notificationManagement.channels.saveFailed')
    )
  } finally {
    saving.value = false
  }
}

function confirmDelete(row) {
  deleteTarget.value = row
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await notificationsAdminApi.deleteChannel(deleteTarget.value.uuid)
    showSuccess(t('common.success'))
    showDeleteConfirm.value = false
    deleteTarget.value = null
    loadList()
  } catch (e) {
    showError(
      e?.response?.data?.detail ||
        e?.message ||
        t('notificationManagement.channels.saveFailed')
    )
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadList()
})
</script>
