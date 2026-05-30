<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div
        class="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between"
      >
        <div>
          <h1 class="text-lg font-semibold text-gray-900">
            {{ t('billing.plansPageTitle') }}
          </h1>
          <p class="mt-1 text-sm text-gray-500">
            {{ t('billing.plansPageSubtitle') }}
          </p>
        </div>
      </div>

      <div
        v-if="!stripeConfigLoading && !stripeConfigured"
        class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      >
        {{ t('billing.planEditor.syncStripeDisabledHint') }}
      </div>

      <section class="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div
          class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-6 py-5"
        >
          <div class="flex flex-wrap items-center gap-2">
            <BaseButton
              variant="warning"
              size="sm"
              :disabled="!stripeConfigured || syncablePlans.length === 0"
              @click="openSyncStripeModal"
            >
              {{ t('billing.planEditor.syncStripe') }}
            </BaseButton>
            <BaseButton variant="primary" size="sm" @click="openCreatePlan">
              {{ t('billing.planEditor.createTitle') }}
            </BaseButton>
          </div>
          <BaseButton
            variant="outline"
            size="sm"
            :loading="loadingPlans"
            :title="t('common.refresh')"
            class="flex items-center gap-1 shadow-sm hover:shadow-md transition-shadow"
            @click="loadPlans"
          >
            <svg
              v-if="!loadingPlans"
              class="h-4 w-4"
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
        </div>

        <div class="w-full p-6">
          <div
            class="mb-4 flex items-center justify-between gap-3 text-sm text-gray-500"
          >
            <span>{{
              t('billing.plans.totalCount', { count: plans.length })
            }}</span>
          </div>

          <BaseLoading v-if="loadingPlans" />

          <div v-else-if="plans.length === 0">
            <div
              class="rounded-lg border border-gray-200 bg-gray-50 py-12 text-center"
            >
              <p class="text-sm text-gray-600">
                {{ t('billing.plans.noData') }}
              </p>
            </div>
          </div>

          <div
            v-else
            class="w-full overflow-x-auto rounded-lg border border-gray-200"
          >
            <table class="w-full min-w-[1200px] divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.name') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.slug') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.price') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.credits') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.periodDays') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.status') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.internal') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.selfPurchase') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.stripeSyncStatus') }}
                  </th>
                  <th
                    class="whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-700"
                  >
                    {{ t('billing.plans.actions') }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 bg-white">
                <tr
                  v-for="plan in plans"
                  :key="plan.id"
                  class="hover:bg-gray-50"
                >
                  <td class="px-4 py-3">
                    <p class="text-sm font-medium text-gray-900">
                      {{ plan.name }}
                    </p>
                    <p class="mt-1 text-xs text-gray-500 line-clamp-2">
                      {{ plan.description }}
                    </p>
                    <p
                      v-if="getPlanSummary(plan)"
                      class="mt-1 text-xs text-gray-500 line-clamp-2"
                    >
                      {{ t('billing.plans.summary') }}:
                      {{ getPlanSummary(plan) }}
                    </p>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {{ plan.slug }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                    {{ formatMoney(plan.monthly_price_cents) }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {{ getMetadataValue(plan, 'credits_per_period') }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {{ getMetadataValue(plan, 'period_days') }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      class="rounded-full px-2 py-1 text-xs font-medium"
                      :class="
                        plan.status === 'active'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-gray-100 text-gray-600'
                      "
                    >
                      {{
                        plan.status === 'active'
                          ? t('billing.plans.enabled')
                          : t('billing.plans.disabled')
                      }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      class="rounded-full px-2 py-1 text-xs font-medium"
                      :class="
                        plan.is_internal
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-gray-100 text-gray-600'
                      "
                    >
                      {{
                        plan.is_internal
                          ? t('billing.plans.internal')
                          : t('billing.plans.external')
                      }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      class="rounded-full px-2 py-1 text-xs font-medium"
                      :class="
                        plan.allow_self_purchase
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-600'
                      "
                    >
                      {{
                        plan.allow_self_purchase
                          ? t('billing.plans.selfPurchaseAllowed')
                          : t('billing.plans.selfPurchaseAdminOnly')
                      }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      class="rounded-full px-2 py-1 text-xs font-medium"
                      :class="getStripeSyncBadge(plan).className"
                    >
                      {{ getStripeSyncBadge(plan).label }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-right">
                    <div class="flex items-center justify-end gap-2">
                      <BaseButton
                        variant="outline"
                        size="sm"
                        @click="openEditPlan(plan)"
                      >
                        {{ t('billing.planEditor.editTitle') }}
                      </BaseButton>
                      <BaseButton
                        variant="danger"
                        size="sm"
                        @click="confirmDeletePlan(plan)"
                      >
                        {{ t('billing.planEditor.delete') }}
                      </BaseButton>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <BaseModal
        :show="syncStripeModalOpen"
        :title="t('billing.planEditor.syncStripeModalTitle')"
        @close="closeSyncStripeModal"
      >
        <div class="space-y-4">
          <p class="text-sm text-gray-500">
            {{ t('billing.planEditor.syncStripeModalHint') }}
          </p>

          <div
            v-if="syncablePlans.length === 0"
            class="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-10 text-center text-sm text-gray-500"
          >
            {{ t('billing.planEditor.syncStripeModalEmpty') }}
          </div>

          <template v-else>
            <div
              class="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div class="text-sm text-gray-600">
                {{
                  t('billing.planEditor.syncStripeSelectionCount', {
                    count: selectedSyncPlanIds.length,
                    total: syncablePlans.length
                  })
                }}
              </div>
              <div class="flex items-center gap-2">
                <BaseButton
                  variant="outline"
                  size="sm"
                  :disabled="syncingStripePlans"
                  @click="selectAllSyncablePlans"
                >
                  {{ t('billing.planEditor.syncStripeSelectAll') }}
                </BaseButton>
                <BaseButton
                  variant="outline"
                  size="sm"
                  :disabled="syncingStripePlans"
                  @click="clearSyncablePlans"
                >
                  {{ t('billing.planEditor.syncStripeClearAll') }}
                </BaseButton>
              </div>
            </div>

            <div class="max-h-[420px] space-y-2 overflow-y-auto pr-1">
              <label
                v-for="plan in syncablePlans"
                :key="plan.id"
                class="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 transition-colors hover:bg-gray-50"
              >
                <input
                  :checked="selectedSyncPlanIds.includes(plan.id)"
                  :disabled="syncingStripePlans"
                  type="checkbox"
                  class="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  @change="
                    toggleSyncPlanSelection(plan.id, $event.target.checked)
                  "
                />
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-medium text-gray-900">
                      {{ plan.name }}
                    </span>
                    <span class="text-xs text-gray-500">
                      {{ plan.slug }}
                    </span>
                    <span
                      class="rounded-full px-2 py-1 text-xs font-medium"
                      :class="getStripeSyncBadge(plan).className"
                    >
                      {{ getStripeSyncBadge(plan).label }}
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-gray-500">
                    {{ formatMoney(plan.monthly_price_cents) }}
                    ·
                    {{ getPlanSummary(plan) || '—' }}
                  </p>
                </div>
              </label>
            </div>
          </template>
        </div>

        <template #footer>
          <BaseButton
            variant="warning"
            size="sm"
            :disabled="selectedSyncPlanIds.length === 0 || syncingStripePlans"
            :loading="syncingStripePlans"
            @click="syncSelectedPlansToStripe"
          >
            {{ t('billing.planEditor.syncStripeStart') }}
          </BaseButton>
          <BaseButton
            variant="outline"
            size="sm"
            :disabled="syncingStripePlans"
            @click="closeSyncStripeModal"
          >
            {{ t('common.close') }}
          </BaseButton>
        </template>
      </BaseModal>

      <transition
        enter-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="editorOpen"
          class="fixed inset-0 z-50 bg-gray-900/50"
          aria-hidden="true"
          @click="closeEditor"
        />
      </transition>

      <transition
        enter-active-class="transition-all duration-250 ease-out"
        enter-from-class="translate-y-4 scale-95 opacity-0"
        enter-to-class="translate-y-0 scale-100 opacity-100"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="translate-y-0 scale-100 opacity-100"
        leave-to-class="translate-y-4 scale-95 opacity-0"
      >
        <div
          v-if="editorOpen"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <section
            class="w-full max-w-3xl rounded-2xl border border-gray-200 bg-white shadow-2xl"
          >
            <div
              class="flex items-center justify-between border-b border-gray-200 px-6 py-5"
            >
              <div>
                <h2 class="text-base font-semibold text-gray-900">
                  {{
                    editorMode === 'create'
                      ? t('billing.planEditor.createTitle')
                      : t('billing.planEditor.editTitle')
                  }}
                </h2>
                <p class="mt-1 text-sm text-gray-500">
                  {{ t('billing.planEditor.metadataHint') }}
                </p>
              </div>
              <button
                type="button"
                class="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                :aria-label="t('common.close')"
                @click="closeEditor"
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <form class="space-y-5 p-6" @submit.prevent="savePlan">
              <div class="grid gap-4 md:grid-cols-2">
                <label class="space-y-1">
                  <span class="block text-sm font-medium text-gray-700">{{
                    t('billing.planEditor.name')
                  }}</span>
                  <input
                    v-model="planForm.name"
                    type="text"
                    class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </label>
                <label class="space-y-1">
                  <span class="block text-sm font-medium text-gray-700">{{
                    t('billing.planEditor.slug')
                  }}</span>
                  <input
                    v-model="planForm.slug"
                    type="text"
                    class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </label>
              </div>

              <label class="space-y-1 block">
                <span class="block text-sm font-medium text-gray-700">{{
                  t('billing.planEditor.planType')
                }}</span>
                <select
                  v-model="planForm.planType"
                  class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  <option value="public_paid">
                    {{ t('billing.planEditor.planTypePublicPaid') }}
                  </option>
                  <option value="public_grant_only">
                    {{ t('billing.planEditor.planTypePublicGrantOnly') }}
                  </option>
                  <option value="platform_private">
                    {{ t('billing.planEditor.planTypePlatformPrivate') }}
                  </option>
                  <option value="draft">
                    {{ t('billing.planEditor.planTypeDraft') }}
                  </option>
                </select>
                <p class="text-xs text-gray-500">
                  {{ t('billing.planEditor.planTypeHint') }}
                </p>
              </label>

              <label class="space-y-1 block">
                <span class="block text-sm font-medium text-gray-700">{{
                  t('billing.planEditor.description')
                }}</span>
                <textarea
                  v-model="planForm.description"
                  rows="3"
                  class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </label>

              <div class="grid gap-4 md:grid-cols-3">
                <label class="space-y-1">
                  <span class="block text-sm font-medium text-gray-700">{{
                    t('billing.planEditor.price')
                  }}</span>
                  <input
                    v-model.number="planForm.monthly_price_cents"
                    type="number"
                    min="0"
                    class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </label>
                <label class="space-y-1">
                  <span class="block text-sm font-medium text-gray-700">{{
                    t('billing.plans.credits')
                  }}</span>
                  <input
                    v-model.number="planForm.credits_per_period"
                    type="number"
                    min="0"
                    class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </label>
                <label class="space-y-1">
                  <span class="block text-sm font-medium text-gray-700">{{
                    t('billing.plans.periodDays')
                  }}</span>
                  <input
                    v-model.number="planForm.period_days"
                    type="number"
                    min="1"
                    class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </label>
              </div>

              <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div class="space-y-3">
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('billing.planEditor.metadataTitle') }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {{ t('billing.planEditor.metadataHint') }}
                    </p>
                  </div>

                  <div class="grid gap-4 md:grid-cols-3">
                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.planEditor.creditsPerPeriod') }}
                      </span>
                      <input
                        v-model.number="planForm.credits_per_period"
                        type="number"
                        min="0"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </label>

                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.planEditor.periodDays') }}
                      </span>
                      <input
                        v-model.number="planForm.period_days"
                        type="number"
                        min="1"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </label>

                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.planEditor.workflowCostCredits') }}
                      </span>
                      <input
                        v-model.number="planForm.workflow_cost_credits"
                        type="number"
                        min="0"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </label>

                    <label class="flex h-full flex-col space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.planEditor.attachmentLimit') }}
                      </span>
                      <div class="flex h-full flex-col justify-start gap-2">
                        <label
                          class="inline-flex h-6 items-center gap-2 text-xs text-gray-500"
                        >
                          <input
                            v-model="planForm.max_attachment_count_unlimited"
                            type="checkbox"
                            class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span>{{ t('billing.planEditor.unlimited') }}</span>
                        </label>
                        <input
                          v-model.number="planForm.max_attachment_count"
                          type="number"
                          min="0"
                          :disabled="planForm.max_attachment_count_unlimited"
                          class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:bg-gray-100 disabled:text-gray-400"
                        />
                      </div>
                    </label>

                    <label class="flex h-full flex-col space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.planEditor.storageQuota') }}
                      </span>
                      <div class="flex h-full flex-col justify-start gap-2">
                        <label
                          class="inline-flex h-6 items-center gap-2 text-xs text-gray-500"
                        >
                          <input
                            v-model="planForm.storage_quota_unlimited"
                            type="checkbox"
                            class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span>{{ t('billing.planEditor.unlimited') }}</span>
                        </label>
                        <input
                          v-model.number="planForm.storage_quota_gb"
                          type="number"
                          min="0"
                          step="0.1"
                          :disabled="planForm.storage_quota_unlimited"
                          class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:bg-gray-100 disabled:text-gray-400"
                        />
                      </div>
                    </label>

                    <label class="flex h-full flex-col space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.planEditor.retentionDays') }}
                      </span>
                      <div class="flex h-full flex-col justify-start gap-2">
                        <label
                          class="inline-flex h-6 items-center gap-2 text-xs text-gray-500"
                        >
                          <input
                            v-model="planForm.retention_days_unlimited"
                            type="checkbox"
                            class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span>{{ t('billing.planEditor.unlimited') }}</span>
                        </label>
                        <input
                          v-model.number="planForm.retention_days"
                          type="number"
                          min="0"
                          :disabled="planForm.retention_days_unlimited"
                          class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:bg-gray-100 disabled:text-gray-400"
                        />
                      </div>
                    </label>
                  </div>
                </div>
              </div>

              <p v-if="editorError" class="text-sm text-red-600">
                {{ editorError }}
              </p>

              <div
                class="flex items-center justify-end gap-3 border-t border-gray-200 pt-5"
              >
                <BaseButton
                  variant="secondary"
                  size="sm"
                  :disabled="savingPlan"
                  @click="closeEditor"
                >
                  {{ t('billing.planEditor.cancel') }}
                </BaseButton>
                <BaseButton
                  variant="primary"
                  size="sm"
                  type="submit"
                  :loading="savingPlan"
                >
                  {{ t('billing.planEditor.save') }}
                </BaseButton>
              </div>
            </form>
          </section>
        </div>
      </transition>
    </div>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import { billingAdminApi } from '@/admin/api'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BaseModal from '@/components/ui/BaseModal.vue'

const { t } = useI18n()
const toast = useToast()

const plans = ref([])
const loadingPlans = ref(true)
const stripeConfigLoading = ref(true)
const stripeConfigured = ref(false)
const savingPlan = ref(false)
const syncingStripePlans = ref(false)
const syncStripeModalOpen = ref(false)
const editorOpen = ref(false)
const editorError = ref('')
const editorMode = ref('create')
const editingPlanId = ref(null)
const selectedSyncPlanIds = ref([])

const planForm = reactive({
  name: '',
  slug: '',
  description: '',
  monthly_price_cents: 0,
  planType: 'public_paid',
  credits_per_period: 10,
  period_days: 30,
  workflow_cost_credits: 1,
  max_attachment_count: '',
  max_attachment_count_unlimited: false,
  storage_quota_gb: '',
  storage_quota_unlimited: false,
  retention_days: '',
  retention_days_unlimited: false,
  metadataBase: {}
})

const defaultMetadata = () => ({
  credits_per_period: 10,
  period_days: 30,
  workflow_cost_credits: 1,
  max_attachment_count: '',
  storage_quota_mb: '',
  retention_days: ''
})

const PLAN_TYPE_MAP = {
  public_paid: {
    status: 'active',
    is_active: true,
    is_internal: false,
    allow_self_purchase: true
  },
  public_grant_only: {
    status: 'active',
    is_active: true,
    is_internal: false,
    allow_self_purchase: false
  },
  platform_private: {
    status: 'active',
    is_active: true,
    is_internal: true,
    allow_self_purchase: false
  },
  draft: {
    status: 'draft',
    is_active: false,
    is_internal: false,
    allow_self_purchase: false
  }
}

function resolvePlanType(plan) {
  if (!plan) return 'public_paid'
  if (plan.status && plan.status !== 'active') return 'draft'
  if (plan.status !== 'active' && plan.is_active === false) return 'draft'
  if (plan.is_internal) return 'platform_private'
  if (plan.allow_self_purchase === false) return 'public_grant_only'
  return 'public_paid'
}

function formatMoney(cents) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format((Number(cents) || 0) / 100)
}

function getMetadataValue(plan, key) {
  const value = plan?.metadata?.[key]
  return value === undefined || value === null || value === '' ? '—' : value
}

function isUnlimitedValue(value) {
  return Number(value) === -1
}

function formatUnlimitedValue(value, formatter) {
  if (value === undefined || value === null || value === '') {
    return '—'
  }

  if (isUnlimitedValue(value)) {
    return t('billing.planEditor.unlimited')
  }

  return formatter(Number(value))
}

function formatStorageQuota(mb) {
  const value = Number(mb)
  if (!Number.isFinite(value)) {
    return '—'
  }

  if (value < 0) {
    return t('billing.planEditor.unlimited')
  }

  if (value === 0) {
    return '0 MB'
  }

  if (value >= 1024) {
    const gb = value / 1024
    const normalizedGb = Number.isInteger(gb)
      ? `${gb}`
      : gb.toFixed(1).replace(/\.0$/, '')
    return `${normalizedGb} GB`
  }

  return `${value} MB`
}

function formatRetentionDays(days) {
  return formatUnlimitedValue(days, (value) => {
    if (!Number.isFinite(value)) {
      return '—'
    }

    return `${value} ${value === 1 ? t('billing.planEditor.dayUnit') : t('billing.planEditor.daysUnit')}`
  })
}

function formatAttachmentLimit(value) {
  return formatUnlimitedValue(value, (numberValue) => `${numberValue}`)
}

function formatStorageQuotaInputValue(mb) {
  const value = Number(mb)
  if (!Number.isFinite(value) || value <= 0) {
    return ''
  }

  return Number((value / 1024).toFixed(2))
}

function getPlanSummary(plan) {
  const metadata = plan?.metadata || {}
  const summary = []

  const creditsPerPeriod =
    metadata.credits_per_period ?? plan?.credits_per_period
  if (
    creditsPerPeriod !== undefined &&
    creditsPerPeriod !== null &&
    creditsPerPeriod !== ''
  ) {
    summary.push(
      `${t('billing.creditsInfo.emailLimit')}: ${creditsPerPeriod} ${t('billing.creditsInfo.emails')}`
    )
  }

  if (
    metadata.max_attachment_count !== undefined &&
    metadata.max_attachment_count !== null &&
    metadata.max_attachment_count !== ''
  ) {
    summary.push(
      `${t('billing.creditsInfo.attachmentLimit')}: ${formatAttachmentLimit(metadata.max_attachment_count)}${isUnlimitedValue(metadata.max_attachment_count) ? '' : ` ${t('billing.creditsInfo.attachments')}`}`
    )
  }

  if (
    metadata.storage_quota_mb !== undefined &&
    metadata.storage_quota_mb !== null &&
    metadata.storage_quota_mb !== ''
  ) {
    summary.push(
      `${t('billing.creditsInfo.storageQuota')}: ${formatStorageQuota(metadata.storage_quota_mb)}`
    )
  }

  if (
    metadata.retention_days !== undefined &&
    metadata.retention_days !== null &&
    metadata.retention_days !== ''
  ) {
    summary.push(
      `${t('billing.creditsInfo.retentionPeriod')}: ${formatRetentionDays(metadata.retention_days)}`
    )
  }

  return summary.length > 0 ? summary.join(' · ') : ''
}

function resetForm(plan = null) {
  const metadata = plan?.metadata || defaultMetadata()
  planForm.name = plan?.name || ''
  planForm.slug = plan?.slug || ''
  planForm.description = plan?.description || ''
  planForm.monthly_price_cents = Number(plan?.monthly_price_cents || 0)
  planForm.planType = resolvePlanType(plan)
  planForm.credits_per_period = Number(metadata.credits_per_period ?? 10)
  planForm.period_days = Number(metadata.period_days ?? 30)
  planForm.workflow_cost_credits = Number(metadata.workflow_cost_credits ?? 1)
  planForm.max_attachment_count_unlimited = isUnlimitedValue(
    metadata.max_attachment_count
  )
  planForm.max_attachment_count = planForm.max_attachment_count_unlimited
    ? ''
    : (metadata.max_attachment_count ?? '')
  planForm.storage_quota_unlimited = isUnlimitedValue(metadata.storage_quota_mb)
  planForm.storage_quota_gb = planForm.storage_quota_unlimited
    ? ''
    : formatStorageQuotaInputValue(metadata.storage_quota_mb)
  planForm.retention_days_unlimited = isUnlimitedValue(metadata.retention_days)
  planForm.retention_days = planForm.retention_days_unlimited
    ? ''
    : (metadata.retention_days ?? '')
  planForm.metadataBase = { ...metadata }
}

async function loadPlans() {
  loadingPlans.value = true
  try {
    plans.value = await billingAdminApi.getPlans()
  } catch (error) {
    console.error('Failed to load billing plans:', error)
    plans.value = []
    toast.showError(t('billing.planEditor.saveFailed'))
  } finally {
    loadingPlans.value = false
  }
}

async function loadStripeConfig() {
  stripeConfigLoading.value = true
  try {
    const config = await billingAdminApi.getConfig()
    stripeConfigured.value = Boolean(config?.stripe_configured)
  } catch (error) {
    console.error('Failed to load billing config for plan page:', error)
    stripeConfigured.value = false
  } finally {
    stripeConfigLoading.value = false
  }
}

function openCreatePlan() {
  editorMode.value = 'create'
  editingPlanId.value = null
  editorError.value = ''
  resetForm()
  editorOpen.value = true
}

function openEditPlan(plan) {
  editorMode.value = 'edit'
  editingPlanId.value = plan.id
  editorError.value = ''
  resetForm(plan)
  editorOpen.value = true
}

function canSyncPlanToStripe(plan) {
  return (
    plan?.status === 'active' && !plan?.is_internal && plan?.allow_self_purchase
  )
}

const syncablePlans = computed(() => {
  return plans.value.filter((plan) => canSyncPlanToStripe(plan))
})

function resetSyncStripeSelection() {
  const plansToSelect = syncablePlans.value.filter(
    (plan) => !plan.stripe_price_id
  )
  const fallbackPlans = syncablePlans.value
  const nextSelection = plansToSelect.length > 0 ? plansToSelect : fallbackPlans
  selectedSyncPlanIds.value = nextSelection.map((plan) => plan.id)
}

function openSyncStripeModal() {
  if (syncablePlans.value.length === 0) {
    return
  }
  resetSyncStripeSelection()
  syncStripeModalOpen.value = true
}

function closeSyncStripeModal() {
  if (syncingStripePlans.value) {
    return
  }
  syncStripeModalOpen.value = false
}

function selectAllSyncablePlans() {
  selectedSyncPlanIds.value = syncablePlans.value.map((plan) => plan.id)
}

function clearSyncablePlans() {
  selectedSyncPlanIds.value = []
}

function toggleSyncPlanSelection(planId, checked) {
  if (checked) {
    if (!selectedSyncPlanIds.value.includes(planId)) {
      selectedSyncPlanIds.value = [...selectedSyncPlanIds.value, planId]
    }
    return
  }

  selectedSyncPlanIds.value = selectedSyncPlanIds.value.filter(
    (selectedPlanId) => selectedPlanId !== planId
  )
}

function getStripeSyncBadge(plan) {
  if (!canSyncPlanToStripe(plan)) {
    return {
      label: '—',
      className: 'bg-gray-100 text-gray-600'
    }
  }

  if (plan?.stripe_price_id) {
    return {
      label: t('billing.plans.stripeSynced'),
      className: 'bg-emerald-100 text-emerald-800'
    }
  }

  return {
    label: t('billing.plans.stripeUnsynced'),
    className: 'bg-gray-100 text-gray-600'
  }
}

function closeEditor() {
  editorOpen.value = false
  editorError.value = ''
}

async function savePlan() {
  editorError.value = ''
  savingPlan.value = true
  try {
    const metadata = {
      ...planForm.metadataBase,
      credits_per_period: Number(planForm.credits_per_period || 0),
      period_days: Number(planForm.period_days || 1),
      workflow_cost_credits: Number(planForm.workflow_cost_credits || 1),
      max_attachment_count: planForm.max_attachment_count_unlimited
        ? -1
        : Number(planForm.max_attachment_count || 0),
      storage_quota_mb: planForm.storage_quota_unlimited
        ? -1
        : Math.round(Number(planForm.storage_quota_gb || 0) * 1024),
      retention_days: planForm.retention_days_unlimited
        ? -1
        : Number(planForm.retention_days || 0)
    }

    const planType =
      PLAN_TYPE_MAP[planForm.planType] || PLAN_TYPE_MAP.public_paid

    const payload = {
      name: planForm.name,
      slug: planForm.slug,
      description: planForm.description,
      monthly_price_cents: Number(planForm.monthly_price_cents || 0),
      metadata,
      status: planType.status,
      is_active: planType.is_active,
      is_internal: planType.is_internal,
      allow_self_purchase: planType.allow_self_purchase
    }

    if (!payload.name || !payload.slug) {
      throw new Error('Name and slug are required')
    }

    if (editorMode.value === 'create') {
      await billingAdminApi.createPlan(payload)
      toast.showSuccess(t('billing.planEditor.saveSuccess'))
    } else {
      await billingAdminApi.updatePlan(editingPlanId.value, payload)
      toast.showSuccess(t('billing.planEditor.saveSuccess'))
    }

    editorOpen.value = false
    await loadPlans()
  } catch (error) {
    console.error('Failed to save billing plan:', error)
    editorError.value = error?.message || t('billing.planEditor.saveFailed')
    toast.showError(t('billing.planEditor.saveFailed'))
  } finally {
    savingPlan.value = false
  }
}

async function syncSelectedPlansToStripe() {
  const selectedPlans = syncablePlans.value.filter((plan) =>
    selectedSyncPlanIds.value.includes(plan.id)
  )

  if (selectedPlans.length === 0) {
    toast.showWarning(t('billing.planEditor.syncStripeNoSelection'))
    return
  }

  syncingStripePlans.value = true
  let successCount = 0
  let failureCount = 0

  try {
    for (const plan of selectedPlans) {
      try {
        await billingAdminApi.syncPlanToStripe(plan.id)
        successCount += 1
      } catch (error) {
        failureCount += 1
        console.error(`Failed to sync plan ${plan.id} to Stripe:`, error)
      }
    }

    if (successCount > 0 && failureCount === 0) {
      toast.showSuccess(t('billing.planEditor.syncStripeSuccess'))
    } else if (successCount > 0) {
      toast.showWarning(
        t('billing.planEditor.syncStripePartialSuccess', {
          successCount,
          failureCount
        })
      )
    } else {
      toast.showError(t('billing.planEditor.syncStripeFailed'))
    }

    syncStripeModalOpen.value = false
    await loadPlans()
  } finally {
    syncingStripePlans.value = false
  }
}

async function confirmDeletePlan(plan) {
  const confirmed = window.confirm(t('billing.planEditor.deleteConfirm'))
  if (!confirmed) return
  try {
    await billingAdminApi.deletePlan(plan.id)
    toast.showSuccess(t('billing.planEditor.deleteSuccess'))
    await loadPlans()
  } catch (error) {
    console.error('Failed to delete billing plan:', error)
    toast.showError(t('billing.planEditor.saveFailed'))
  }
}

onMounted(() => {
  loadPlans()
  loadStripeConfig()
})
</script>
