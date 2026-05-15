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
        <div class="flex items-center gap-2">
          <BaseButton
            variant="outline"
            size="sm"
            :loading="loadingPlans"
            @click="loadPlans"
          >
            {{ t('common.refresh') }}
          </BaseButton>
          <BaseButton variant="primary" size="sm" @click="openCreatePlan">
            {{ t('billing.planEditor.createTitle') }}
          </BaseButton>
        </div>
      </div>

      <section class="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div class="border-b border-gray-200 px-6 py-5">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-base font-semibold text-gray-900">
                {{ t('billing.plansPageTitle') }}
              </h2>
              <p class="mt-1 text-sm text-gray-500">
                {{ t('billing.sections.plansDesc') }}
              </p>
            </div>
            <span class="text-sm text-gray-500">
              {{ t('billing.plans.totalCount', { count: plans.length }) }}
            </span>
          </div>
        </div>

        <BaseLoading v-if="loadingPlans" class="p-6" />
        <div v-else-if="plans.length === 0" class="p-6">
          <div
            class="rounded-lg border border-gray-200 bg-gray-50 py-12 text-center"
          >
            <p class="text-sm text-gray-600">
              {{ t('billing.plans.noData') }}
            </p>
          </div>
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.name') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.slug') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.price') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.credits') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.periodDays') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.active') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.internal') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.stripePrice') }}
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.stripeProduct') }}
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-700"
                >
                  {{ t('billing.plans.actions') }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 bg-white">
              <tr v-for="plan in plans" :key="plan.id" class="hover:bg-gray-50">
                <td class="px-4 py-3">
                  <p class="text-sm font-medium text-gray-900">
                    {{ plan.name }}
                  </p>
                  <p class="mt-1 text-xs text-gray-500 line-clamp-2">
                    {{ plan.description }}
                  </p>
                </td>
                <td class="px-4 py-3 text-sm text-gray-600">{{ plan.slug }}</td>
                <td class="px-4 py-3 text-sm text-gray-900">
                  {{ formatMoney(plan.monthly_price_cents) }}
                </td>
                <td class="px-4 py-3 text-sm text-gray-600">
                  {{ getMetadataValue(plan, 'credits_per_period') }}
                </td>
                <td class="px-4 py-3 text-sm text-gray-600">
                  {{ getMetadataValue(plan, 'period_days') }}
                </td>
                <td class="px-4 py-3 text-sm">
                  <span
                    class="rounded-full px-2 py-1 text-xs font-medium"
                    :class="
                      plan.is_active
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-gray-100 text-gray-600'
                    "
                  >
                    {{
                      plan.is_active
                        ? t('billing.plans.enabled')
                        : t('billing.plans.disabled')
                    }}
                  </span>
                </td>
                <td class="px-4 py-3 text-sm">
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
                <td class="px-4 py-3 text-xs text-gray-600 font-mono">
                  {{ plan.stripe_price_id || '—' }}
                </td>
                <td class="px-4 py-3 text-xs text-gray-600 font-mono">
                  {{ plan.stripe_product_id || '—' }}
                </td>
                <td class="px-4 py-3 text-right">
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
      </section>

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

              <label class="space-y-1 block">
                <span class="block text-sm font-medium text-gray-700">{{
                  t('billing.planEditor.metadata')
                }}</span>
                <textarea
                  v-model="planForm.metadataJson"
                  rows="8"
                  class="w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </label>

              <div class="grid gap-4 md:grid-cols-2">
                <label
                  class="flex items-center gap-3 rounded-lg border border-gray-200 px-4 py-3"
                >
                  <input
                    v-model="planForm.is_active"
                    type="checkbox"
                    class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span class="text-sm font-medium text-gray-700">{{
                    t('billing.planEditor.active')
                  }}</span>
                </label>
                <label
                  class="flex items-center gap-3 rounded-lg border border-gray-200 px-4 py-3"
                >
                  <input
                    v-model="planForm.is_internal"
                    type="checkbox"
                    class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span class="text-sm font-medium text-gray-700">{{
                    t('billing.planEditor.internal')
                  }}</span>
                </label>
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
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import { billingAdminApi } from '@/admin/api'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t } = useI18n()
const toast = useToast()

const plans = ref([])
const loadingPlans = ref(true)
const savingPlan = ref(false)
const editorOpen = ref(false)
const editorError = ref('')
const editorMode = ref('create')
const editingPlanId = ref(null)

const planForm = reactive({
  name: '',
  slug: '',
  description: '',
  monthly_price_cents: 0,
  credits_per_period: 10,
  period_days: 30,
  workflow_cost_credits: 1,
  metadataJson: '{}',
  is_active: true,
  is_internal: false
})

const defaultMetadata = () => ({
  credits_per_period: 10,
  period_days: 30,
  workflow_cost_credits: 1
})

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

function resetForm(plan = null) {
  const metadata = plan?.metadata || defaultMetadata()
  planForm.name = plan?.name || ''
  planForm.slug = plan?.slug || ''
  planForm.description = plan?.description || ''
  planForm.monthly_price_cents = Number(plan?.monthly_price_cents || 0)
  planForm.credits_per_period = Number(metadata.credits_per_period ?? 10)
  planForm.period_days = Number(metadata.period_days ?? 30)
  planForm.workflow_cost_credits = Number(metadata.workflow_cost_credits ?? 1)
  planForm.metadataJson = JSON.stringify(metadata, null, 2)
  planForm.is_active = plan?.is_active ?? true
  planForm.is_internal = plan?.is_internal ?? false
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

function closeEditor() {
  editorOpen.value = false
  editorError.value = ''
}

function parseMetadata() {
  if (!planForm.metadataJson.trim()) return {}
  const parsed = JSON.parse(planForm.metadataJson)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Metadata must be a JSON object')
  }
  return parsed
}

async function savePlan() {
  editorError.value = ''
  savingPlan.value = true
  try {
    const metadata = parseMetadata()
    metadata.credits_per_period = Number(planForm.credits_per_period || 0)
    metadata.period_days = Number(planForm.period_days || 1)
    metadata.workflow_cost_credits = Number(planForm.workflow_cost_credits || 1)

    const payload = {
      name: planForm.name,
      slug: planForm.slug,
      description: planForm.description,
      monthly_price_cents: Number(planForm.monthly_price_cents || 0),
      metadata,
      is_active: !!planForm.is_active,
      is_internal: !!planForm.is_internal
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
})
</script>
