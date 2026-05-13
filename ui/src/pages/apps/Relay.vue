<template>
  <AppLayout>
    <div class="space-y-6">
      <div
        class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
      >
        <div>
          <h1 class="text-2xl font-semibold text-gray-900">
            {{ t('relay.pageTitle') }}
          </h1>
          <p class="mt-1 text-sm text-gray-500">
            {{ t('relay.pageSubtitle') }}
          </p>
        </div>
      </div>

      <div class="border-b border-gray-200">
        <div
          class="flex gap-6 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          role="tablist"
          aria-label="Relay categories"
        >
          <button
            v-for="tab in tabs"
            :key="tab.value"
            type="button"
            class="flex-shrink-0 border-b-2 px-1 py-3 text-xs font-medium transition-colors sm:text-sm"
            role="tab"
            :aria-selected="activeTab === tab.value"
            :class="
              activeTab === tab.value
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            "
            @click="activeTab = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <BaseCard v-if="activeTab === 'deliveries'">
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <div class="text-base font-semibold text-gray-900">
              {{ t('relay.deliveryListTitle') }}
            </div>
            <span class="text-xs text-gray-500">
              {{ deliveryPagination.total }} {{ t('relay.items') }}
            </span>
          </div>
        </template>

        <div
          v-if="deliveries.length === 0"
          class="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-sm text-gray-500"
        >
          {{ t('relay.noDeliveries') }}
        </div>

        <div v-else class="space-y-3">
          <article
            v-for="event in deliveries"
            :key="event.id"
            class="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-primary-300 hover:shadow-md"
          >
            <div
              class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
            >
              <div class="min-w-0 flex-1">
                <div class="flex min-w-0 items-center gap-2">
                  <MergeStateBadge :state="eventMergeState(event)" size="sm" />
                  <span
                    class="block min-w-0 flex-1 truncate text-base font-semibold text-gray-900"
                  >
                    {{ deliverySummaryTitle(event) }}
                  </span>
                </div>
                <div
                  class="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-500"
                >
                  <template v-if="eventIssueTags(event).length > 0">
                    <a
                      v-for="(tag, index) in eventIssueTags(event)"
                      :key="tag.key"
                      :href="tag.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      :title="tag.title"
                      class="hidden sm:inline-flex shrink-0 items-center rounded-full bg-blue-50 px-2.5 py-0.5 font-medium text-blue-700 ring-1 ring-blue-200 hover:bg-blue-100 transition-colors cursor-pointer"
                    >
                      {{ tag.label }}
                    </a>
                    <a
                      :href="eventChatLink(event)"
                      class="sm:hidden inline-flex shrink-0 items-center rounded-full bg-gray-100 px-2.5 py-0.5 font-medium text-gray-600 ring-1 ring-gray-200 hover:bg-gray-200 transition-colors cursor-pointer"
                      :title="t('relay.openChatDetail')"
                    >
                      +{{ eventIssueTags(event).length }}
                    </a>
                  </template>
                  <span v-else class="text-gray-400">
                    {{ t('relay.noExternalId') }}
                  </span>
                  <span v-if="event.created_at" class="shrink-0">•</span>
                  <span v-if="event.created_at" class="shrink-0">{{
                    formatDeliveryTime(event.created_at)
                  }}</span>
                </div>
              </div>

              <div class="flex shrink-0 flex-wrap gap-2">
                <template v-if="eventRetryMode(event) === 'all'">
                  <span
                    class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1"
                    :class="eventStatusBadgeClass(event.status)"
                  >
                    <svg
                      v-if="statusIconPath(event.status)"
                      class="h-3.5 w-3.5 flex-none"
                      :class="{ 'animate-spin': event.status === 'processing' }"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        :d="statusIconPath(event.status)"
                      />
                    </svg>
                    {{ statusLabel(event.status) }}
                  </span>
                  <BaseButton
                    variant="primary"
                    size="sm"
                    class="!px-2.5 !py-0.5"
                    :disabled="isEventRetryBusy(event)"
                    @click="retryAllDeliveries(event)"
                  >
                    <span class="inline-flex items-center gap-1.5">
                      <svg
                        class="h-3.5 w-3.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      <svg
                        v-if="isEventRetryBusy(event)"
                        class="h-3.5 w-3.5 flex-shrink-0 animate-spin"
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
                      <span class="hidden sm:inline">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                      <span class="sm:hidden">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                    </span>
                  </BaseButton>
                </template>
                <template v-else-if="eventRetryMode(event) === 'single'">
                  <span
                    class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1"
                    :class="eventStatusBadgeClass(event.status)"
                  >
                    <svg
                      v-if="statusIconPath(event.status)"
                      class="h-3.5 w-3.5 flex-none"
                      :class="{ 'animate-spin': event.status === 'processing' }"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        :d="statusIconPath(event.status)"
                      />
                    </svg>
                    {{ statusLabel(event.status) }}
                  </span>
                  <BaseButton
                    variant="primary"
                    size="sm"
                    class="!px-2.5 !py-0.5"
                    :disabled="isEventRetryBusy(event)"
                    @click="retrySelectedDelivery(event)"
                  >
                    <span class="inline-flex items-center gap-1.5">
                      <svg
                        class="h-3.5 w-3.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      <svg
                        v-if="isEventRetryBusy(event)"
                        class="h-3.5 w-3.5 flex-shrink-0 animate-spin"
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
                      <span class="hidden sm:inline">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                      <span class="sm:hidden">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                    </span>
                  </BaseButton>
                </template>
                <template v-else-if="eventRetryMode(event) === 'missing'">
                  <span
                    class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1"
                    :class="eventStatusBadgeClass(event.status)"
                  >
                    <svg
                      v-if="statusIconPath(event.status)"
                      class="h-3.5 w-3.5 flex-none"
                      :class="{ 'animate-spin': event.status === 'processing' }"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        :d="statusIconPath(event.status)"
                      />
                    </svg>
                    {{ statusLabel(event.status) }}
                  </span>
                  <BaseButton
                    variant="primary"
                    size="sm"
                    class="!px-2.5 !py-0.5"
                    :disabled="isEventRetryBusy(event)"
                    @click="retryEvent(event)"
                  >
                    <span class="inline-flex items-center gap-1.5">
                      <svg
                        class="h-3.5 w-3.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      <svg
                        v-if="isEventRetryBusy(event)"
                        class="h-3.5 w-3.5 flex-shrink-0 animate-spin"
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
                      <span class="hidden sm:inline">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                      <span class="sm:hidden">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                    </span>
                  </BaseButton>
                </template>
                <div
                  v-else-if="eventDeliveries(event).length > 1"
                  class="flex items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-xs text-gray-600"
                >
                  <select
                    v-model="retrySelection[event.id]"
                    :disabled="isEventRetryBusy(event)"
                    class="min-w-0 appearance-none border-0 bg-transparent py-0 pl-1 pr-5 text-xs text-gray-700 outline-none focus:ring-0"
                  >
                    <option value="all">
                      {{ t('relay.retryAllChannels') }}
                    </option>
                    <option
                      v-for="item in eventDeliveries(event)"
                      :key="item.id"
                      :value="String(item.id)"
                    >
                      {{ targetLabel(item.target_type) }}
                    </option>
                  </select>
                  <span
                    class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1"
                    :class="eventStatusBadgeClass(event.status)"
                  >
                    <svg
                      v-if="statusIconPath(event.status)"
                      class="h-3.5 w-3.5 flex-none"
                      :class="{ 'animate-spin': event.status === 'processing' }"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        :d="statusIconPath(event.status)"
                      />
                    </svg>
                    {{ statusLabel(event.status) }}
                  </span>
                  <BaseButton
                    variant="primary"
                    size="sm"
                    class="!px-2.5 !py-0.5"
                    :disabled="isEventRetryBusy(event)"
                    @click="retryWithSelection(event)"
                  >
                    <span class="inline-flex items-center gap-1.5">
                      <svg
                        class="h-3.5 w-3.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      <svg
                        v-if="isEventRetryBusy(event)"
                        class="h-3.5 w-3.5 flex-shrink-0 animate-spin"
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
                      <span class="hidden sm:inline">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                      <span class="sm:hidden">
                        {{
                          isEventRetryBusy(event)
                            ? t('relay.retryingDelivery')
                            : t('relay.retryDelivery')
                        }}
                      </span>
                    </span>
                  </BaseButton>
                </div>
              </div>
            </div>
          </article>

          <div
            v-if="deliveryPagination.hasNext || loadingMoreDeliveries"
            ref="deliveryLoadMoreSentinel"
            class="flex items-center justify-center py-4 text-xs text-gray-400"
          >
            <span v-if="loadingMoreDeliveries">{{ t('common.loading') }}</span>
            <span v-else>{{ t('common.loadMore') }}</span>
          </div>
        </div>
      </BaseCard>

      <div v-else class="space-y-6">
        <BaseCard :header-muted="true">
          <template #header>
            <div class="flex items-center justify-between gap-3">
              <div>
                <h3 class="text-base font-semibold leading-5 text-gray-900">
                  {{ t('relay.subscriptionListTitle') }}
                </h3>
                <p class="mt-1 text-xs text-gray-500">
                  {{ t('relay.subscriptionListHelp') }}
                </p>
              </div>
            </div>
          </template>

          <div class="space-y-4">
            <div
              v-if="subscriptions.length === 0"
              class="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-sm text-gray-500"
            >
              {{ t('relay.noSubscriptions') }}
            </div>

            <div v-else class="space-y-3">
              <article
                v-for="sub in subscriptions"
                :key="sub.id"
                class="rounded-2xl border border-gray-200 p-4 shadow-sm transition hover:border-primary-300 hover:shadow-md"
                :class="
                  expandedSubscriptionId === String(sub.id)
                    ? 'border-primary-200 bg-primary-50/40'
                    : 'bg-white'
                "
              >
                <div
                  class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
                >
                  <div class="flex min-w-0 items-start gap-3">
                    <div
                      class="flex h-11 w-11 flex-none items-center justify-center rounded-xl"
                      :class="targetIconBg(sub.target_type)"
                    >
                      <svg
                        class="h-5 w-5 text-white"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          :d="targetIconPath(sub.target_type)"
                        />
                      </svg>
                    </div>

                    <div class="min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <h3 class="text-base font-semibold text-gray-900">
                          {{ sub.name }}
                        </h3>
                        <span
                          class="rounded-full px-2.5 py-0.5 text-xs font-medium"
                          :class="
                            sub.enabled
                              ? 'bg-green-100 text-green-700'
                              : 'bg-gray-100 text-gray-500'
                          "
                        >
                          {{ sub.enabled ? t('common.yes') : t('common.no') }}
                        </span>
                      </div>
                      <div class="mt-1 text-sm text-gray-600">
                        {{ targetLabel(sub.target_type) }}
                      </div>
                    </div>
                  </div>
                  <div
                    v-if="expandedSubscriptionId !== String(sub.id)"
                    class="flex flex-wrap gap-2 sm:justify-end"
                  >
                    <button
                      class="inline-flex items-center gap-1.5 rounded-full border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
                      @click="editSubscription(sub)"
                    >
                      <svg
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M16.862 3.487a2.5 2.5 0 0 1 3.536 3.536L8.25 19.171 3 21l1.829-5.25 12.033-12.263Z"
                        />
                      </svg>
                      {{ t('common.edit') }}
                    </button>
                    <button
                      class="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition"
                      :class="
                        sub.enabled
                          ? 'border-amber-200 text-amber-700 hover:bg-amber-50'
                          : 'border-green-200 text-green-700 hover:bg-green-50'
                      "
                      @click="toggleSubscriptionEnabled(sub)"
                    >
                      <svg
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M12 7v5m0 4h.01M5.5 12a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"
                        />
                      </svg>
                      {{
                        sub.enabled
                          ? t('relay.disableChannel')
                          : t('relay.enableChannel')
                      }}
                    </button>
                    <button
                      class="inline-flex items-center gap-1.5 rounded-full border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 transition hover:bg-red-50"
                      @click="deleteSubscription(sub.id)"
                    >
                      <svg
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M4 7h16M10 11v6m4-6v6m-7 0a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V7H7v10Zm3-7V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2"
                        />
                      </svg>
                      {{ t('common.delete') }}
                    </button>
                  </div>
                </div>

                <div
                  v-if="expandedSubscriptionId === String(sub.id)"
                  class="mt-4 rounded-2xl border border-primary-100 bg-white/90 p-4 shadow-[0_1px_0_rgba(255,255,255,0.8)]"
                >
                  <div class="space-y-5">
                    <div
                      class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
                    >
                      <div class="md:col-span-1">
                        <label
                          class="block text-sm font-medium text-gray-700 mb-1"
                        >
                          {{ t('relay.channelType') }}
                        </label>
                        <p class="text-xs text-gray-500">
                          {{ t('relay.channelTypeHelp') }}
                        </p>
                      </div>
                      <div class="md:col-span-2">
                        <select v-model="editorForm.target_type" class="input">
                          <option value="feishu_bitable">
                            {{ t('relay.targetFeishu') }}
                          </option>
                          <option value="jira">
                            {{ t('relay.targetJira') }}
                          </option>
                        </select>
                      </div>
                    </div>

                    <div
                      class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
                    >
                      <div class="md:col-span-1">
                        <label
                          class="block text-sm font-medium text-gray-700 mb-1"
                        >
                          {{ t('relay.name') }}
                        </label>
                        <p class="text-xs text-gray-500">
                          {{ t('relay.channelNameHelp') }}
                        </p>
                      </div>
                      <div class="md:col-span-2">
                        <input v-model="editorForm.name" class="input" />
                      </div>
                    </div>

                    <div
                      class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-center"
                    >
                      <div class="md:col-span-1">
                        <label
                          class="block text-sm font-medium text-gray-700 mb-1"
                        >
                          {{ t('relay.enabled') }}
                        </label>
                        <p class="text-xs text-gray-500">
                          {{ t('relay.channelEnabledHelp') }}
                        </p>
                      </div>
                      <div class="md:col-span-2">
                        <label
                          class="flex items-center gap-2 text-sm text-gray-700"
                        >
                          <input
                            v-model="editorForm.enabled"
                            type="checkbox"
                            class="rounded border-gray-300"
                          />
                          {{
                            editorForm.enabled
                              ? t('common.yes')
                              : t('common.no')
                          }}
                        </label>
                      </div>
                    </div>

                    <div
                      class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
                    >
                      <div class="md:col-span-1">
                        <label
                          class="block text-sm font-medium text-gray-700 mb-1"
                        >
                          {{ t('relay.language') }}
                        </label>
                        <p class="text-xs text-gray-500">
                          {{ t('relay.languageHelp') }}
                        </p>
                      </div>
                      <div class="md:col-span-2">
                        <select v-model="editorForm.language" class="input">
                          <option value="Chinese">
                            {{ t('relay.languageChinese') }}
                          </option>
                          <option value="English">
                            {{ t('relay.languageEnglish') }}
                          </option>
                        </select>
                      </div>
                    </div>

                    <div
                      class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                    >
                      <div>
                        <h4 class="text-sm font-semibold text-gray-900">
                          {{ t('relay.strategiesTitle') }}
                        </h4>
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('relay.strategiesHelp') }}
                        </p>
                      </div>

                      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
                        <div>
                          <label
                            class="mb-1 block text-sm font-medium text-gray-700"
                          >
                            {{ t('settings.autoMergeStrategy') }}
                          </label>
                          <select
                            v-model="editorForm.strategies.auto_merge_strategy"
                            class="input"
                          >
                            <option value="new">
                              {{ t('settings.autoMergeStrategyNew') }}
                            </option>
                            <option value="update">
                              {{ t('settings.autoMergeStrategyUpdate') }}
                            </option>
                          </select>
                        </div>

                        <div>
                          <label
                            class="mb-1 block text-sm font-medium text-gray-700"
                          >
                            {{ t('settings.manualMergeStrategy') }}
                          </label>
                          <select
                            v-model="
                              editorForm.strategies.manual_merge_strategy
                            "
                            class="input"
                          >
                            <option value="linked">
                              {{ t('settings.manualMergeStrategyLinked') }}
                            </option>
                            <option value="unlinked">
                              {{ t('settings.manualMergeStrategyUnlinked') }}
                            </option>
                          </select>
                        </div>

                        <div>
                          <label
                            class="mb-1 block text-sm font-medium text-gray-700"
                          >
                            {{ t('settings.retryIssueStrategy') }}
                          </label>
                          <select
                            v-model="editorForm.strategies.retry_issue_strategy"
                            class="input"
                          >
                            <option value="new">
                              {{ t('settings.retryIssueStrategyNew') }}
                            </option>
                            <option value="update">
                              {{ t('settings.retryIssueStrategyUpdate') }}
                            </option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div
                      v-if="editorForm.target_type === 'feishu_bitable'"
                      class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                    >
                      <div>
                        <h4 class="text-sm font-semibold text-gray-900">
                          {{ t('relay.feishuConfigTitle') }}
                        </h4>
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('settings.feishuConfigDesc1') }}
                        </p>
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('settings.feishuConfigDesc2') }}
                        </p>
                      </div>

                      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <BaseInput
                          v-model="editorForm.feishuConfig.app_id"
                          :label="t('settings.feishuAppId')"
                          :placeholder="t('settings.feishuAppIdPlaceholder')"
                        />
                        <div>
                          <label
                            class="mb-1 block text-sm font-medium text-gray-700"
                          >
                            {{ t('settings.feishuAppSecret') }}
                          </label>
                          <div class="relative">
                            <input
                              v-model="editorForm.feishuConfig.app_secret"
                              :type="showFeishuAppSecret ? 'text' : 'password'"
                              class="input pr-10"
                              :placeholder="
                                t('settings.feishuAppSecretPlaceholder')
                              "
                              autocomplete="new-password"
                            />
                            <button
                              type="button"
                              class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 transition hover:text-gray-700"
                              :aria-label="
                                showFeishuAppSecret
                                  ? t('common.hide')
                                  : t('common.show')
                              "
                              :title="
                                showFeishuAppSecret
                                  ? t('common.hide')
                                  : t('common.show')
                              "
                              @click="
                                showFeishuAppSecret = !showFeishuAppSecret
                              "
                            >
                              <svg
                                v-if="!showFeishuAppSecret"
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
                                  d="M3.98 8.223A10.48 10.48 0 0 0 1.934 12c1.73 4.943 6.402 8.5 12.066 8.5 1.618 0 3.159-.3 4.578-.845m3.42-2.113A10.44 10.44 0 0 0 22.065 12C20.335 7.057 15.663 3.5 10 3.5c-1.618 0-3.159.3-4.578.845m3.42 2.113A5 5 0 1 1 18 12a5 5 0 0 1-9.158-2.579Z"
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
                                  d="M2.25 3.75 21 22.5m-2.255-2.255A10.47 10.47 0 0 1 12 20.5c-5.664 0-10.336-3.557-12.066-8.5a10.53 10.53 0 0 1 3.034-4.223m3.079-2.113A10.42 10.42 0 0 1 12 3.5c5.664 0 10.336 3.557 12.066 8.5a10.49 10.49 0 0 1-4.143 5.277M9.88 9.88A3 3 0 0 0 14.12 14.12"
                                />
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>

                      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <div class="space-y-1">
                          <label
                            class="mb-1 block text-sm font-medium text-gray-700"
                          >
                            {{ t('settings.feishuAppTokenType') }}
                          </label>
                          <select
                            v-model="editorForm.feishuConfig.app_token_type"
                            class="input"
                          >
                            <option value="bitable">
                              {{ t('settings.feishuAppTokenTypeBitable') }}
                            </option>
                            <option value="wiki">
                              {{ t('settings.feishuAppTokenTypeWiki') }}
                            </option>
                          </select>
                          <p class="text-xs text-gray-500">
                            {{ t('settings.feishuAppTokenTypeHelp') }}
                          </p>
                        </div>

                        <BaseInput
                          v-model="editorForm.feishuConfig.app_token"
                          :label="t('settings.feishuAppToken')"
                          :placeholder="t('settings.feishuAppTokenPlaceholder')"
                          :help="t('settings.feishuAppTokenHelp')"
                        />
                      </div>

                      <BaseInput
                        v-model="editorForm.feishuConfig.table_name"
                        :label="t('settings.feishuTableName')"
                        :placeholder="t('settings.feishuTableNamePlaceholder')"
                        :help="t('settings.feishuTableNameHelp')"
                      />

                      <div
                        class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                      >
                        <div class="space-y-2">
                          <div>
                            <h5 class="text-sm font-semibold text-gray-900">
                              {{ t('settings.feishuFieldMappings') }}
                            </h5>
                            <p class="mt-1 text-xs text-gray-500">
                              {{ t('settings.feishuFieldMappingsHelp') }}
                            </p>
                            <p class="mt-1 text-xs text-gray-500">
                              {{ t('settings.feishuFieldMappingsDetail') }}
                            </p>
                          </div>
                        </div>

                        <div class="space-y-3">
                          <div
                            v-for="(
                              mapping, index
                            ) in editorForm.fieldMappingRows"
                            :key="`mapping-${index}`"
                            class="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_1fr_auto]"
                          >
                            <BaseInput
                              v-model="mapping.source"
                              :label="t('settings.feishuFieldMappingSource')"
                              :placeholder="
                                t(
                                  'settings.feishuFieldMappingSourcePlaceholder'
                                )
                              "
                            />
                            <BaseInput
                              v-model="mapping.target"
                              :label="t('settings.feishuFieldMappingTarget')"
                              :placeholder="
                                t(
                                  'settings.feishuFieldMappingTargetPlaceholder'
                                )
                              "
                            />
                            <div class="flex items-end">
                              <BaseButton
                                variant="secondary"
                                size="sm"
                                class="w-full lg:w-auto"
                                @click="
                                  index === 0
                                    ? addFieldMappingRow()
                                    : removeFieldMappingRow(index)
                                "
                                :aria-label="
                                  index === 0
                                    ? t('relay.addMappingRow')
                                    : t('relay.removeMappingRow')
                                "
                              >
                                <svg
                                  v-if="index === 0"
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
                                    d="M12 5v14m7-7H5"
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
                                    d="M5 12h14"
                                  />
                                </svg>
                              </BaseButton>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div
                        class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                      >
                        <BaseInput
                          v-model="
                            editorForm.feishuConfig.attachment_field_name
                          "
                          :label="t('settings.feishuAttachmentFieldName')"
                          :placeholder="
                            t('settings.feishuAttachmentFieldNamePlaceholder')
                          "
                          :help="t('settings.feishuAttachmentMappingHelp')"
                        />
                      </div>
                    </div>

                    <div
                      v-else
                      class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                    >
                      <div>
                        <h4 class="text-sm font-semibold text-gray-900">
                          {{ t('relay.jiraConfigTitle') }}
                        </h4>
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('relay.jiraConfigHelp') }}
                        </p>
                      </div>

                      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <BaseInput
                          v-model="editorForm.jiraConfig.url"
                          :label="t('relay.jiraUrl')"
                          :placeholder="t('relay.jiraUrlPlaceholder')"
                        />
                        <BaseInput
                          v-model="editorForm.jiraConfig.username"
                          :label="t('relay.jiraUsername')"
                          :placeholder="t('relay.jiraUsernamePlaceholder')"
                        />
                      </div>

                      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <BaseInput
                          v-model="editorForm.jiraConfig.api_token"
                          :label="t('relay.jiraApiToken')"
                          :placeholder="t('relay.jiraApiTokenPlaceholder')"
                        />
                        <BaseInput
                          v-model="editorForm.jiraConfig.project_key"
                          :label="t('relay.jiraProjectKey')"
                          :placeholder="t('relay.jiraProjectKeyPlaceholder')"
                        />
                      </div>

                      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <BaseInput
                          v-model="editorForm.jiraConfig.issue_type_default"
                          :label="t('relay.jiraIssueTypeDefault')"
                          :placeholder="
                            t('relay.jiraIssueTypeDefaultPlaceholder')
                          "
                        />
                        <BaseInput
                          v-model="editorForm.jiraConfig.priority_default"
                          :label="t('relay.jiraPriorityDefault')"
                          :placeholder="
                            t('relay.jiraPriorityDefaultPlaceholder')
                          "
                        />
                      </div>

                      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <BaseInput
                    v-model="editorForm.jiraConfig.summary_prefix"
                    :label="
                      relayText('relay.jiraSummaryPrefix', {
                        en: 'Title prefix',
                        zh: '标题前缀'
                      })
                    "
                    :placeholder="
                      relayText('relay.jiraSummaryPrefixPlaceholder', {
                        en: '[AI]',
                        zh: '[AI]'
                      })
                    "
                  />

                        <div class="space-y-3">
                          <label
                            class="block text-sm font-medium text-gray-700"
                          >
                            {{ t('relay.jiraSummaryOptions') }}
                          </label>
                          <label
                            class="flex items-center gap-2 text-sm text-gray-700"
                          >
                            <input
                              v-model="editorForm.jiraConfig.add_timestamp"
                              type="checkbox"
                              class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                            />
                            {{ t('relay.jiraAddTimestamp') }}
                          </label>
                        </div>
                      </div>

                      <BaseInput
                        v-model="editorForm.jiraConfig.description_field"
                        :label="t('settings.jiraDescriptionField')"
                        :placeholder="
                          t('settings.jiraDescriptionFieldPlaceholder')
                        "
                        :help="t('settings.jiraDescriptionFieldHelp')"
                      />

                      <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                        <label
                          class="flex items-center gap-2 text-sm text-gray-700"
                        >
                          <input
                            v-model="editorForm.jiraConfig.convert_to_jira_wiki"
                            type="checkbox"
                            class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          {{ t('relay.jiraConvertToWiki') }}
                        </label>
                        <label
                          class="flex items-center gap-2 text-sm text-gray-700"
                        >
                          <input
                            v-model="editorForm.jiraConfig.assignee_use_llm"
                            type="checkbox"
                            class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          {{ t('relay.jiraAssigneeUseLlm') }}
                        </label>
                      </div>

                      <div
                        class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                      >
                        <div>
                          <h4 class="text-sm font-semibold text-gray-900">
                            {{ t('settings.jiraAssigneeSectionTitle') }}
                          </h4>
                          <p class="mt-1 text-xs text-gray-500">
                            {{ t('settings.jiraAssigneeSectionDesc') }}
                          </p>
                        </div>

                        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                          <BaseInput
                            v-model="editorForm.jiraConfig.assignee_default"
                            :label="t('settings.jiraAssigneeDefault')"
                            :placeholder="
                              t('settings.jiraAssigneeDefaultPlaceholder')
                            "
                            :help="t('settings.jiraAssigneeDefaultHelp')"
                          />
                          <div>
                            <label
                              class="mb-1 block text-sm font-medium text-gray-700"
                            >
                              {{ t('settings.jiraAssigneeAllowValues') }}
                            </label>
                            <textarea
                              v-model="
                                editorForm.jiraConfig.assignee_allow_values_text
                              "
                              class="input min-h-[96px]"
                              :placeholder="
                                t('settings.jiraAssigneeAllowValuesPlaceholder')
                              "
                            />
                            <p class="mt-1 text-xs text-gray-500">
                              {{ t('settings.jiraAssigneeAllowValuesHelp') }}
                            </p>
                          </div>
                        </div>

                        <div>
                          <label
                            class="mb-1 block text-sm font-medium text-gray-700"
                          >
                            {{ t('settings.jiraAssigneePrompt') }}
                          </label>
                          <textarea
                            v-model="editorForm.jiraConfig.assignee_prompt"
                            class="input min-h-[96px]"
                            :placeholder="
                              t('settings.jiraAssigneePromptPlaceholder')
                            "
                          />
                          <p class="mt-1 text-xs text-gray-500">
                            {{ t('settings.jiraAssigneePromptHelp') }}
                          </p>
                        </div>
                      </div>

                      <div
                        class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                      >
                        <div>
                          <h4 class="text-sm font-semibold text-gray-900">
                            {{ t('settings.jiraComponentsSectionTitle') }}
                          </h4>
                          <p class="mt-1 text-xs text-gray-500">
                            {{ t('settings.jiraComponentsSectionDesc') }}
                          </p>
                        </div>

                        <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                          <label
                            class="flex items-center gap-2 text-sm text-gray-700"
                          >
                            <input
                              v-model="editorForm.jiraConfig.components_use_llm"
                              type="checkbox"
                              class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                            />
                            {{ t('settings.jiraComponentsUseLlm') }}
                          </label>
                          <label
                            class="flex items-center gap-2 text-sm text-gray-700"
                          >
                            <input
                              v-model="
                                editorForm.jiraConfig.components_fetch_from_api
                              "
                              type="checkbox"
                              class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                            />
                            {{ t('settings.jiraComponentsFetchFromApi') }}
                          </label>
                        </div>

                        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                          <div>
                            <label
                              class="mb-1 block text-sm font-medium text-gray-700"
                            >
                              {{ t('settings.jiraComponentsDefault') }}
                            </label>
                            <textarea
                              v-model="
                                editorForm.jiraConfig.components_default_text
                              "
                              class="input min-h-[96px]"
                              :placeholder="
                                t('settings.jiraComponentsDefaultPlaceholder')
                              "
                            />
                            <p class="mt-1 text-xs text-gray-500">
                              {{ t('settings.jiraComponentsDefaultHelp') }}
                            </p>
                          </div>
                          <div>
                            <label
                              class="mb-1 block text-sm font-medium text-gray-700"
                            >
                              {{ t('settings.jiraComponentsPrompt') }}
                            </label>
                            <textarea
                              v-model="editorForm.jiraConfig.components_prompt"
                              class="input min-h-[96px]"
                              :placeholder="
                                t('settings.jiraComponentsPromptPlaceholder')
                              "
                            />
                            <p class="mt-1 text-xs text-gray-500">
                              {{ t('settings.jiraComponentsPromptHelp') }}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div
                        class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                      >
                        <div>
                          <h4 class="text-sm font-semibold text-gray-900">
                            {{ t('settings.jiraEpicLinkSectionTitle') }}
                          </h4>
                          <p class="mt-1 text-xs text-gray-500">
                            {{ t('settings.jiraEpicLinkSectionDesc') }}
                          </p>
                        </div>

                        <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                          <label
                            class="flex items-center gap-2 text-sm text-gray-700"
                          >
                            <input
                              v-model="
                                editorForm.jiraConfig.epic_link_fetch_from_api
                              "
                              type="checkbox"
                              class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                            />
                            {{ t('settings.jiraEpicLinkFetchFromApi') }}
                          </label>
                          <label
                            class="flex items-center gap-2 text-sm text-gray-700"
                          >
                            <input
                              v-model="editorForm.jiraConfig.epic_link_use_llm"
                              type="checkbox"
                              class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                            />
                            {{ t('settings.jiraEpicLinkUseLlm') }}
                          </label>
                        </div>

                        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                          <BaseInput
                            v-model="editorForm.jiraConfig.epic_link_default"
                            :label="t('settings.jiraEpicLinkDefault')"
                            :placeholder="
                              t('settings.jiraEpicLinkDefaultPlaceholder')
                            "
                            :help="t('settings.jiraEpicLinkDefaultHelp')"
                          />
                          <BaseInput
                            v-model="editorForm.jiraConfig.epic_link_jql_filter"
                            :label="t('settings.jiraEpicLinkJqlFilter')"
                            :placeholder="
                              t('settings.jiraEpicLinkJqlFilterPlaceholder')
                            "
                            :help="t('settings.jiraEpicLinkJqlFilterHelp')"
                          />
                        </div>

                        <div>
                          <label
                            class="mb-1 block text-sm font-medium text-gray-700"
                          >
                            {{ t('settings.jiraEpicLinkPrompt') }}
                          </label>
                          <textarea
                            v-model="editorForm.jiraConfig.epic_link_prompt"
                            class="input min-h-[96px]"
                            :placeholder="
                              t('settings.jiraEpicLinkPromptPlaceholder')
                            "
                          />
                          <p class="mt-1 text-xs text-gray-500">
                            {{ t('settings.jiraEpicLinkPromptHelp') }}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <p
                    v-if="
                      expandedSubscriptionId === String(sub.id) && editorError
                    "
                    class="text-sm text-red-600"
                  >
                    {{ editorError }}
                  </p>
                  <p
                    v-if="
                      expandedSubscriptionId === String(sub.id) &&
                      editorSuccess &&
                      editorTestPassed
                    "
                    class="text-sm text-green-600"
                  >
                    {{ editorSuccess }}
                  </p>

                  <div class="flex justify-end pt-2">
                    <div
                      class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row"
                    >
                      <BaseButton
                        variant="secondary"
                        class="w-full sm:w-auto"
                        :disabled="saving"
                        @click="cancelEditor"
                      >
                        {{ t('common.cancel') }}
                      </BaseButton>
                      <BaseButton
                        variant="secondary"
                        class="w-full sm:w-auto"
                        :loading="testing"
                        :disabled="saving"
                        @click="runEditorTest"
                      >
                        {{ t('relay.runTest') }}
                      </BaseButton>
                      <BaseButton
                        class="w-full sm:w-auto"
                        :loading="saving"
                        :disabled="saving || testing || !editorCanSave"
                        @click="saveEditor"
                      >
                        {{ t('relay.saveTargets') }}
                      </BaseButton>
                    </div>
                  </div>
                  <p v-if="!editorCanSave" class="text-xs text-amber-600">
                    {{ t('relay.saveAfterTestHint') }}
                  </p>
                </div>
              </article>
            </div>

            <button
              v-if="!editorVisible || editorMode !== 'create'"
              type="button"
              class="w-full rounded-2xl border border-dashed border-gray-300 bg-gray-50 px-4 py-2.5 text-left transition hover:border-primary-300 hover:bg-primary-50/60"
              @click="openCreatePanel"
            >
              <div class="flex items-start gap-3">
                <div
                  class="flex h-9 w-9 flex-none items-center justify-center rounded-xl bg-primary-600"
                >
                  <svg
                    class="h-4 w-4 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 5v14m7-7H5"
                    />
                  </svg>
                </div>
                <div class="min-w-0">
                  <div class="text-sm font-semibold text-gray-900">
                    {{ t('relay.addChannel') }}
                  </div>
                  <div class="mt-1 text-xs leading-5 text-gray-500">
                    {{ t('relay.addChannelHelp') }}
                  </div>
                </div>
              </div>
            </button>

            <div
              v-if="editorVisible && editorMode === 'create'"
              class="rounded-2xl border border-primary-200 bg-primary-50/30 p-4 shadow-sm"
            >
              <div class="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h4 class="text-sm font-semibold text-gray-900">
                    {{ t('relay.createChannel') }}
                  </h4>
                  <p class="mt-1 text-xs text-gray-500">
                    {{ t('relay.addChannelHelp') }}
                  </p>
                </div>
              </div>

              <div class="space-y-5">
                <div
                  class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
                >
                  <div class="md:col-span-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('relay.channelType') }}
                    </label>
                    <p class="text-xs text-gray-500">
                      {{ t('relay.channelTypeHelp') }}
                    </p>
                  </div>
                  <div class="md:col-span-2">
                    <select v-model="editorForm.target_type" class="input">
                      <option value="feishu_bitable">
                        {{ t('relay.targetFeishu') }}
                      </option>
                      <option value="jira">
                        {{ t('relay.targetJira') }}
                      </option>
                    </select>
                  </div>
                </div>

                <div
                  class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
                >
                  <div class="md:col-span-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('relay.name') }}
                    </label>
                    <p class="text-xs text-gray-500">
                      {{ t('relay.channelNameHelp') }}
                    </p>
                  </div>
                  <div class="md:col-span-2">
                    <input v-model="editorForm.name" class="input" />
                  </div>
                </div>

                <div
                  class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-center"
                >
                  <div class="md:col-span-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('relay.enabled') }}
                    </label>
                    <p class="text-xs text-gray-500">
                      {{ t('relay.channelEnabledHelp') }}
                    </p>
                  </div>
                  <div class="md:col-span-2">
                    <label
                      class="flex items-center gap-2 text-sm text-gray-700"
                    >
                      <input
                        v-model="editorForm.enabled"
                        type="checkbox"
                        class="rounded border-gray-300"
                      />
                      {{
                        editorForm.enabled ? t('common.yes') : t('common.no')
                      }}
                    </label>
                  </div>
                </div>

                <div
                  class="grid grid-cols-1 gap-2 md:grid-cols-3 md:gap-4 md:items-start"
                >
                  <div class="md:col-span-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ t('relay.language') }}
                    </label>
                    <p class="text-xs text-gray-500">
                      {{ t('relay.languageHelp') }}
                    </p>
                  </div>
                  <div class="md:col-span-2">
                    <select v-model="editorForm.language" class="input">
                      <option value="Chinese">
                        {{ t('relay.languageChinese') }}
                      </option>
                      <option value="English">
                        {{ t('relay.languageEnglish') }}
                      </option>
                    </select>
                  </div>
                </div>

                <div
                  class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                >
                  <div>
                    <h4 class="text-sm font-semibold text-gray-900">
                      {{ t('relay.strategiesTitle') }}
                    </h4>
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('relay.strategiesHelp') }}
                    </p>
                  </div>

                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
                    <div>
                      <label
                        class="mb-1 block text-sm font-medium text-gray-700"
                      >
                        {{ t('settings.autoMergeStrategy') }}
                      </label>
                      <select
                        v-model="editorForm.strategies.auto_merge_strategy"
                        class="input"
                      >
                        <option value="new">
                          {{ t('settings.autoMergeStrategyNew') }}
                        </option>
                        <option value="update">
                          {{ t('settings.autoMergeStrategyUpdate') }}
                        </option>
                      </select>
                    </div>

                    <div>
                      <label
                        class="mb-1 block text-sm font-medium text-gray-700"
                      >
                        {{ t('settings.manualMergeStrategy') }}
                      </label>
                      <select
                        v-model="editorForm.strategies.manual_merge_strategy"
                        class="input"
                      >
                        <option value="linked">
                          {{ t('settings.manualMergeStrategyLinked') }}
                        </option>
                        <option value="unlinked">
                          {{ t('settings.manualMergeStrategyUnlinked') }}
                        </option>
                      </select>
                    </div>

                    <div>
                      <label
                        class="mb-1 block text-sm font-medium text-gray-700"
                      >
                        {{ t('settings.retryIssueStrategy') }}
                      </label>
                      <select
                        v-model="editorForm.strategies.retry_issue_strategy"
                        class="input"
                      >
                        <option value="new">
                          {{ t('settings.retryIssueStrategyNew') }}
                        </option>
                        <option value="update">
                          {{ t('settings.retryIssueStrategyUpdate') }}
                        </option>
                      </select>
                    </div>
                  </div>
                </div>

                <div
                  v-if="editorForm.target_type === 'feishu_bitable'"
                  class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                >
                  <div>
                    <h4 class="text-sm font-semibold text-gray-900">
                      {{ t('relay.feishuConfigTitle') }}
                    </h4>
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('settings.feishuConfigDesc1') }}
                    </p>
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('settings.feishuConfigDesc2') }}
                    </p>
                  </div>

                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <BaseInput
                      v-model="editorForm.feishuConfig.app_id"
                      :label="t('settings.feishuAppId')"
                      :placeholder="t('settings.feishuAppIdPlaceholder')"
                    />
                    <div>
                      <label
                        class="mb-1 block text-sm font-medium text-gray-700"
                      >
                        {{ t('settings.feishuAppSecret') }}
                      </label>
                      <div class="relative">
                        <input
                          v-model="editorForm.feishuConfig.app_secret"
                          :type="showFeishuAppSecret ? 'text' : 'password'"
                          class="input pr-10"
                          :placeholder="
                            t('settings.feishuAppSecretPlaceholder')
                          "
                          autocomplete="new-password"
                        />
                        <button
                          type="button"
                          class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 transition hover:text-gray-700"
                          :aria-label="
                            showFeishuAppSecret
                              ? t('common.hide')
                              : t('common.show')
                          "
                          :title="
                            showFeishuAppSecret
                              ? t('common.hide')
                              : t('common.show')
                          "
                          @click="showFeishuAppSecret = !showFeishuAppSecret"
                        >
                          <svg
                            v-if="!showFeishuAppSecret"
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
                              d="M3.98 8.223A10.48 10.48 0 0 0 1.934 12c1.73 4.943 6.402 8.5 12.066 8.5 1.618 0 3.159-.3 4.578-.845m3.42-2.113A10.44 10.44 0 0 0 22.065 12C20.335 7.057 15.663 3.5 10 3.5c-1.618 0-3.159.3-4.578.845m3.42 2.113A5 5 0 1 1 18 12a5 5 0 0 1-9.158-2.579Z"
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
                              d="M2.25 3.75 21 22.5m-2.255-2.255A10.47 10.47 0 0 1 12 20.5c-5.664 0-10.336-3.557-12.066-8.5a10.53 10.53 0 0 1 3.034-4.223m3.079-2.113A10.42 10.42 0 0 1 12 3.5c5.664 0 10.336 3.557 12.066 8.5a10.49 10.49 0 0 1-4.143 5.277M9.88 9.88A3 3 0 0 0 14.12 14.12"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>

                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <div class="space-y-1">
                      <label class="block text-sm font-medium text-gray-700">
                        {{ t('settings.feishuAppTokenType') }}
                      </label>
                      <select
                        v-model="editorForm.feishuConfig.app_token_type"
                        class="input"
                      >
                        <option value="bitable">
                          {{ t('settings.feishuAppTokenTypeBitable') }}
                        </option>
                        <option value="wiki">
                          {{ t('settings.feishuAppTokenTypeWiki') }}
                        </option>
                      </select>
                      <p class="text-xs text-gray-500">
                        {{ t('settings.feishuAppTokenTypeHelp') }}
                      </p>
                    </div>

                    <BaseInput
                      v-model="editorForm.feishuConfig.app_token"
                      :label="t('settings.feishuAppToken')"
                      :placeholder="t('settings.feishuAppTokenPlaceholder')"
                      :help="t('settings.feishuAppTokenHelp')"
                    />
                  </div>

                  <BaseInput
                    v-model="editorForm.feishuConfig.table_name"
                    :label="t('settings.feishuTableName')"
                    :placeholder="t('settings.feishuTableNamePlaceholder')"
                    :help="t('settings.feishuTableNameHelp')"
                  />

                      <BaseInput
                        v-model="editorForm.feishuConfig.summary_prefix"
                        :label="
                          relayText('relay.feishuSummaryPrefix', {
                            en: 'Title prefix',
                            zh: '标题前缀'
                          })
                        "
                        :placeholder="
                        relayText('relay.feishuSummaryPrefixPlaceholder', {
                            en: '[AI] ',
                            zh: '[AI] '
                          })
                        "
                        :help="
                          relayText('relay.feishuSummaryPrefixHelp', {
                            en: 'Automatically prepended to the Feishu title. Leave it empty to disable.',
                            zh: '会自动加在飞书标题前面，留空则不加。'
                          })
                        "
                      />

                  <div
                    class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                  >
                    <div class="space-y-2">
                      <div>
                        <h5 class="text-sm font-semibold text-gray-900">
                          {{ t('settings.feishuFieldMappings') }}
                        </h5>
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('settings.feishuFieldMappingsHelp') }}
                        </p>
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('settings.feishuFieldMappingsDetail') }}
                        </p>
                      </div>
                    </div>

                    <div class="space-y-3">
                      <div
                        v-for="(mapping, index) in editorForm.fieldMappingRows"
                        :key="`mapping-${index}`"
                        class="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_1fr_auto]"
                      >
                        <BaseInput
                          v-model="mapping.source"
                          :label="t('settings.feishuFieldMappingSource')"
                          :placeholder="
                            t('settings.feishuFieldMappingSourcePlaceholder')
                          "
                        />
                        <BaseInput
                          v-model="mapping.target"
                          :label="t('settings.feishuFieldMappingTarget')"
                          :placeholder="
                            t('settings.feishuFieldMappingTargetPlaceholder')
                          "
                        />
                        <div class="flex items-end">
                          <BaseButton
                            variant="secondary"
                            size="sm"
                            class="w-full lg:w-auto"
                            @click="
                              index === 0
                                ? addFieldMappingRow()
                                : removeFieldMappingRow(index)
                            "
                            :aria-label="
                              index === 0
                                ? t('relay.addMappingRow')
                                : t('relay.removeMappingRow')
                            "
                          >
                            <svg
                              v-if="index === 0"
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
                                d="M12 5v14m7-7H5"
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
                                d="M5 12h14"
                              />
                            </svg>
                          </BaseButton>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                  >
                    <BaseInput
                      v-model="editorForm.feishuConfig.attachment_field_name"
                      :label="t('settings.feishuAttachmentFieldName')"
                      :placeholder="
                        t('settings.feishuAttachmentFieldNamePlaceholder')
                      "
                      :help="t('settings.feishuAttachmentMappingHelp')"
                    />
                  </div>
                </div>

                <div
                  v-else
                  class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                >
                  <div>
                    <h4 class="text-sm font-semibold text-gray-900">
                      {{ t('relay.jiraConfigTitle') }}
                    </h4>
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('relay.jiraConfigHelp') }}
                    </p>
                  </div>

                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <BaseInput
                      v-model="editorForm.jiraConfig.url"
                      :label="t('relay.jiraUrl')"
                      :placeholder="t('relay.jiraUrlPlaceholder')"
                    />
                    <BaseInput
                      v-model="editorForm.jiraConfig.username"
                      :label="t('relay.jiraUsername')"
                      :placeholder="t('relay.jiraUsernamePlaceholder')"
                    />
                  </div>

                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <BaseInput
                      v-model="editorForm.jiraConfig.api_token"
                      :label="t('relay.jiraApiToken')"
                      :placeholder="t('relay.jiraApiTokenPlaceholder')"
                    />
                    <BaseInput
                      v-model="editorForm.jiraConfig.project_key"
                      :label="t('relay.jiraProjectKey')"
                      :placeholder="t('relay.jiraProjectKeyPlaceholder')"
                    />
                  </div>

                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <BaseInput
                      v-model="editorForm.jiraConfig.issue_type_default"
                      :label="t('relay.jiraIssueTypeDefault')"
                      :placeholder="t('relay.jiraIssueTypeDefaultPlaceholder')"
                    />
                    <BaseInput
                      v-model="editorForm.jiraConfig.priority_default"
                      :label="t('relay.jiraPriorityDefault')"
                      :placeholder="t('relay.jiraPriorityDefaultPlaceholder')"
                    />
                  </div>

                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                      <BaseInput
                        v-model="editorForm.jiraConfig.summary_prefix"
                        :label="
                          relayText('relay.jiraSummaryPrefix', {
                            en: 'Summary prefix',
                            zh: '标题前缀'
                          })
                        "
                        :placeholder="
                          relayText('relay.jiraSummaryPrefixPlaceholder', {
                            en: '[AI]',
                            zh: '[AI]'
                          })
                        "
                      />

                    <div class="space-y-3">
                      <label class="block text-sm font-medium text-gray-700">
                        {{ t('relay.jiraSummaryOptions') }}
                      </label>
                      <label
                        class="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <input
                          v-model="editorForm.jiraConfig.add_timestamp"
                          type="checkbox"
                          class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        {{ t('relay.jiraAddTimestamp') }}
                      </label>
                    </div>
                  </div>

                  <BaseInput
                    v-model="editorForm.jiraConfig.description_field"
                    :label="t('settings.jiraDescriptionField')"
                    :placeholder="t('settings.jiraDescriptionFieldPlaceholder')"
                    :help="t('settings.jiraDescriptionFieldHelp')"
                  />

                  <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                    <label
                      class="flex items-center gap-2 text-sm text-gray-700"
                    >
                      <input
                        v-model="editorForm.jiraConfig.convert_to_jira_wiki"
                        type="checkbox"
                        class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      {{ t('relay.jiraConvertToWiki') }}
                    </label>
                    <label
                      class="flex items-center gap-2 text-sm text-gray-700"
                    >
                      <input
                        v-model="editorForm.jiraConfig.assignee_use_llm"
                        type="checkbox"
                        class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      {{ t('relay.jiraAssigneeUseLlm') }}
                    </label>
                  </div>

                  <div
                    class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                  >
                    <div>
                      <h4 class="text-sm font-semibold text-gray-900">
                        {{ t('settings.jiraAssigneeSectionTitle') }}
                      </h4>
                      <p class="mt-1 text-xs text-gray-500">
                        {{ t('settings.jiraAssigneeSectionDesc') }}
                      </p>
                    </div>

                    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                      <BaseInput
                        v-model="editorForm.jiraConfig.assignee_default"
                        :label="t('settings.jiraAssigneeDefault')"
                        :placeholder="
                          t('settings.jiraAssigneeDefaultPlaceholder')
                        "
                        :help="t('settings.jiraAssigneeDefaultHelp')"
                      />
                      <div>
                        <label
                          class="mb-1 block text-sm font-medium text-gray-700"
                        >
                          {{ t('settings.jiraAssigneeAllowValues') }}
                        </label>
                        <textarea
                          v-model="
                            editorForm.jiraConfig.assignee_allow_values_text
                          "
                          class="input min-h-[96px]"
                          :placeholder="
                            t('settings.jiraAssigneeAllowValuesPlaceholder')
                          "
                        />
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('settings.jiraAssigneeAllowValuesHelp') }}
                        </p>
                      </div>
                    </div>

                    <div>
                      <label
                        class="mb-1 block text-sm font-medium text-gray-700"
                      >
                        {{ t('settings.jiraAssigneePrompt') }}
                      </label>
                      <textarea
                        v-model="editorForm.jiraConfig.assignee_prompt"
                        class="input min-h-[96px]"
                        :placeholder="
                          t('settings.jiraAssigneePromptPlaceholder')
                        "
                      />
                      <p class="mt-1 text-xs text-gray-500">
                        {{ t('settings.jiraAssigneePromptHelp') }}
                      </p>
                    </div>
                  </div>

                  <div
                    class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                  >
                    <div>
                      <h4 class="text-sm font-semibold text-gray-900">
                        {{ t('settings.jiraComponentsSectionTitle') }}
                      </h4>
                      <p class="mt-1 text-xs text-gray-500">
                        {{ t('settings.jiraComponentsSectionDesc') }}
                      </p>
                    </div>

                    <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                      <label
                        class="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <input
                          v-model="editorForm.jiraConfig.components_use_llm"
                          type="checkbox"
                          class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        {{ t('settings.jiraComponentsUseLlm') }}
                      </label>
                      <label
                        class="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <input
                          v-model="
                            editorForm.jiraConfig.components_fetch_from_api
                          "
                          type="checkbox"
                          class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        {{ t('settings.jiraComponentsFetchFromApi') }}
                      </label>
                    </div>

                    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                      <div>
                        <label
                          class="mb-1 block text-sm font-medium text-gray-700"
                        >
                          {{ t('settings.jiraComponentsDefault') }}
                        </label>
                        <textarea
                          v-model="
                            editorForm.jiraConfig.components_default_text
                          "
                          class="input min-h-[96px]"
                          :placeholder="
                            t('settings.jiraComponentsDefaultPlaceholder')
                          "
                        />
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('settings.jiraComponentsDefaultHelp') }}
                        </p>
                      </div>
                      <div>
                        <label
                          class="mb-1 block text-sm font-medium text-gray-700"
                        >
                          {{ t('settings.jiraComponentsPrompt') }}
                        </label>
                        <textarea
                          v-model="editorForm.jiraConfig.components_prompt"
                          class="input min-h-[96px]"
                          :placeholder="
                            t('settings.jiraComponentsPromptPlaceholder')
                          "
                        />
                        <p class="mt-1 text-xs text-gray-500">
                          {{ t('settings.jiraComponentsPromptHelp') }}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div
                    class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4"
                  >
                    <div>
                      <h4 class="text-sm font-semibold text-gray-900">
                        {{ t('settings.jiraEpicLinkSectionTitle') }}
                      </h4>
                      <p class="mt-1 text-xs text-gray-500">
                        {{ t('settings.jiraEpicLinkSectionDesc') }}
                      </p>
                    </div>

                    <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                      <label
                        class="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <input
                          v-model="
                            editorForm.jiraConfig.epic_link_fetch_from_api
                          "
                          type="checkbox"
                          class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        {{ t('settings.jiraEpicLinkFetchFromApi') }}
                      </label>
                      <label
                        class="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <input
                          v-model="editorForm.jiraConfig.epic_link_use_llm"
                          type="checkbox"
                          class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        {{ t('settings.jiraEpicLinkUseLlm') }}
                      </label>
                    </div>

                    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                      <BaseInput
                        v-model="editorForm.jiraConfig.epic_link_default"
                        :label="t('settings.jiraEpicLinkDefault')"
                        :placeholder="
                          t('settings.jiraEpicLinkDefaultPlaceholder')
                        "
                        :help="t('settings.jiraEpicLinkDefaultHelp')"
                      />
                      <BaseInput
                        v-model="editorForm.jiraConfig.epic_link_jql_filter"
                        :label="t('settings.jiraEpicLinkJqlFilter')"
                        :placeholder="
                          t('settings.jiraEpicLinkJqlFilterPlaceholder')
                        "
                        :help="t('settings.jiraEpicLinkJqlFilterHelp')"
                      />
                    </div>

                    <div>
                      <label
                        class="mb-1 block text-sm font-medium text-gray-700"
                      >
                        {{ t('settings.jiraEpicLinkPrompt') }}
                      </label>
                      <textarea
                        v-model="editorForm.jiraConfig.epic_link_prompt"
                        class="input min-h-[96px]"
                        :placeholder="
                          t('settings.jiraEpicLinkPromptPlaceholder')
                        "
                      />
                      <p class="mt-1 text-xs text-gray-500">
                        {{ t('settings.jiraEpicLinkPromptHelp') }}
                      </p>
                    </div>
                  </div>
                </div>

                <p v-if="editorError" class="text-sm text-red-600">
                  {{ editorError }}
                </p>
                <p
                  v-if="editorSuccess && editorTestPassed"
                  class="text-sm text-green-600"
                >
                  {{ editorSuccess }}
                </p>

                <div class="flex justify-end pt-2">
                  <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                    <BaseButton
                      variant="secondary"
                      class="w-full sm:w-auto"
                      :disabled="saving"
                      @click="cancelEditor"
                    >
                      {{ t('common.cancel') }}
                    </BaseButton>
                    <BaseButton
                      variant="secondary"
                      class="w-full sm:w-auto"
                      :loading="testing"
                      :disabled="saving"
                      @click="runEditorTest"
                    >
                      {{ t('relay.runTest') }}
                    </BaseButton>
                    <BaseButton
                      class="w-full sm:w-auto"
                      :loading="saving"
                      :disabled="saving || testing || !editorCanSave"
                      @click="saveEditor"
                    >
                      {{ t('relay.saveTargets') }}
                    </BaseButton>
                  </div>
                </div>
                <p v-if="!editorCanSave" class="text-xs text-amber-600">
                  {{ t('relay.saveAfterTestHint') }}
                </p>
              </div>
            </div>
          </div>
        </BaseCard>
      </div>
    </div>
    <ConfirmDialog
      :show="retryConfirm.show"
      :title="retryConfirm.title"
      :message="retryConfirm.message"
      :confirm-text="retryConfirm.confirmText"
      variant="warning"
      @close="closeRetryConfirm"
      @confirm="confirmRetry"
    >
      <div
        class="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
      >
        {{ retryConfirm.note }}
      </div>
    </ConfirmDialog>
  </AppLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import MergeStateBadge from '@/components/ui/MergeStateBadge.vue'
import { relayApi } from '@/api/relay'
import { useRelayFormatters } from '@/composables/useRelayFormatters'
import { useRelayDeliveryList } from '@/composables/useRelayDeliveryList'
import { useRelayRetry } from '@/composables/useRelayRetry'
import { useRelayEditor } from '@/composables/useRelayEditor'

const { t, locale } = useI18n()

function relayText(key, { en, zh }) {
  const translated = t(key)
  if (translated && translated !== key) return translated
  return String(locale.value || '').startsWith('zh') ? zh : en
}

const activeTab = ref('deliveries')
const subscriptions = ref([])

async function loadSubscriptions() {
  const data = await relayApi.getSubscriptions()
  subscriptions.value = Array.isArray(data) ? data : []
}

const tabs = computed(() => [
  { value: 'deliveries', label: t('relay.tabsDeliveries') },
  { value: 'channels', label: t('relay.tabsChannels') }
])

const deliveryList = useRelayDeliveryList({ loadSubscriptions, activeTab })
const {
  deliveries,
  deliveryPagination,
  deliveryLoadMoreSentinel,
  loadingMoreDeliveries,
  retrySelection,
  reloadAll,
  disconnectDeliveryLoadMoreObserver,
  refreshDeliveryLoadMoreObserver
} = deliveryList

const retry = useRelayRetry({
  retrySelection,
  deliveryPagination,
  loadDeliveries: deliveryList.loadDeliveries,
  findEventByDeliveryId: deliveryList.findEventByDeliveryId,
  markEventProcessing: deliveryList.markEventProcessing,
  activeTab
})

const editor = useRelayEditor({ reloadAll, activeTab })
const formatters = useRelayFormatters()

// Export retry functions and state used in template
const {
  retryConfirm,
  isEventRetryBusy,
  eventRetryMode,
  confirmRetry,
  closeRetryConfirm,
  retryAllDeliveries,
  retrySelectedDelivery,
  retryEvent,
  retryWithSelection
} = retry

// Export editor state and functions used in template
const {
  saving,
  testing,
  showFeishuAppSecret,
  editorVisible,
  editorMode,
  expandedSubscriptionId,
  editorError,
  editorSuccess,
  editorForm,
  editorTestPassed,
  editorCanSave,
  addFieldMappingRow,
  removeFieldMappingRow,
  openCreatePanel,
  cancelEditor,
  editSubscription,
  saveEditor,
  deleteSubscription,
  runEditorTest,
  toggleSubscriptionEnabled
} = editor

// Export formatter functions used in template
const {
  targetLabel,
  statusLabel,
  statusIconPath,
  deliverySummaryTitle,
  eventMergeState,
  eventChatLink,
  eventIssueTags,
  eventDeliveries,
  formatDeliveryTime,
  eventStatusBadgeClass,
  targetIconBg,
  targetIconPath
} = formatters

watch(activeTab, async (value) => {
  if (value === 'deliveries') {
    await nextTick()
    refreshDeliveryLoadMoreObserver()
  } else {
    disconnectDeliveryLoadMoreObserver()
  }
})

onMounted(async () => {
  await reloadAll()
})

onBeforeUnmount(() => {
  disconnectDeliveryLoadMoreObserver()
  retry.cancelAllPolls()
})
</script>
