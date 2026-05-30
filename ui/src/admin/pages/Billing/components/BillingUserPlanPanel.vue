<template>
  <transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="open"
      class="fixed inset-0 z-50 bg-gray-900/50"
      aria-hidden="true"
      @click="$emit('close')"
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
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <section
        class="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white shadow-2xl"
        role="dialog"
        :aria-label="t('billing.users.assignPlanTitle')"
      >
        <div
          class="flex items-center justify-between border-b border-gray-200 px-6 py-5"
        >
          <div>
            <h2 class="text-base font-semibold text-gray-900">
              {{ t('billing.users.assignPlanTitle') }}
            </h2>
            <p class="mt-1 text-sm text-gray-500">
              {{ t('billing.users.assignPlanHint') }}
            </p>
          </div>
          <button
            type="button"
            class="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            :aria-label="t('common.close')"
            @click="$emit('close')"
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

        <div class="space-y-4 p-6">
          <template v-if="selectedUser">
            <div
              class="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm"
            >
              <p class="font-medium text-gray-900">
                {{ selectedUser.username }}
              </p>
              <p class="mt-1 break-all text-gray-500">
                {{ selectedUser.email || '—' }}
              </p>
              <dl class="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt class="text-gray-500">
                    {{ t('billing.users.currentPlan') }}
                  </dt>
                  <dd class="mt-1 font-medium text-gray-900">
                    {{
                      selectedUser.plan_name ||
                      t('billing.users.noSubscription')
                    }}
                  </dd>
                </div>
                <div>
                  <dt class="text-gray-500">
                    {{ t('billing.users.availableCredits') }}
                  </dt>
                  <dd class="mt-1 font-medium text-gray-900">
                    {{ selectedUser.available_credits }}
                  </dd>
                </div>
              </dl>
            </div>

            <div
              v-if="
                isStripeSubscription(
                  selectedUser.provider_key,
                  selectedUser.provider_name
                )
              "
              class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
            >
              {{ t('billing.users.assignPlanBlockedStripe') }}
            </div>

            <div class="space-y-2">
              <label class="block text-xs font-medium text-gray-700">
                {{ t('billing.users.targetPlan') }}
              </label>
              <select
                :value="selectedPlanId ?? ''"
                class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="
                  $emit(
                    'update:selectedPlanId',
                    $event.target.value === ''
                      ? null
                      : Number($event.target.value)
                  )
                "
              >
                <option value="" disabled>
                  {{ t('billing.users.targetPlanPlaceholder') }}
                </option>
                <option v-for="plan in plans" :key="plan.id" :value="plan.id">
                  {{ formatPlanLabel(plan) }}
                </option>
              </select>
            </div>

            <div
              class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900"
            >
              {{ t('billing.users.assignPlanNote') }}
            </div>

            <div class="flex items-center justify-end gap-3">
              <BaseButton variant="outline" size="sm" @click="$emit('close')">
                {{ t('common.close') }}
              </BaseButton>
              <BaseButton
                variant="primary"
                size="sm"
                :disabled="
                  isStripeSubscription(
                    selectedUser.provider_key,
                    selectedUser.provider_name
                  )
                "
                :loading="switching"
                @click="$emit('switch-plan')"
              >
                {{ t('billing.users.assignPlanAction') }}
              </BaseButton>
            </div>
          </template>

          <div
            v-else
            class="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-10 text-center text-sm text-gray-500"
          >
            {{ t('billing.users.assignPlanPanelEmpty') }}
          </div>
        </div>
      </section>
    </div>
  </transition>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/ui/BaseButton.vue'
import { isStripeProvider } from '../utils/provider'

const { t } = useI18n()

defineProps({
  open: {
    type: Boolean,
    default: false
  },
  plans: {
    type: Array,
    default: () => []
  },
  selectedPlanId: {
    type: [Number, String, null],
    default: null
  },
  selectedUser: {
    type: Object,
    default: null
  },
  switching: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close', 'switch-plan', 'update:selectedPlanId'])

function formatPlanLabel(plan) {
  const parts = [plan.name]
  if (plan.is_internal) {
    parts.push(`(${t('billing.plans.internal')})`)
  }
  return parts.join(' ')
}

function isStripeSubscription(providerKey, providerName) {
  return isStripeProvider(providerKey, providerName)
}
</script>
