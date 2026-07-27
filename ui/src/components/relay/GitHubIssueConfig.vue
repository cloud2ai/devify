<template>
  <section
    class="space-y-4 rounded-lg border border-gray-200 bg-gray-50 p-4"
    aria-labelledby="github-issue-config-title"
  >
    <div>
      <h4
        id="github-issue-config-title"
        class="text-sm font-semibold text-gray-900"
      >
        {{ t('relay.githubConfigTitle') }}
      </h4>
      <p class="mt-1 text-xs text-gray-500">
        {{ t('relay.githubConfigHelp') }}
      </p>
    </div>

    <BaseInput
      v-model="config.repo"
      :label="t('relay.githubRepo')"
      :placeholder="t('relay.githubRepoPlaceholder')"
      :help="t('relay.githubRepoHelp')"
      required
      autocomplete="off"
    />

    <div class="space-y-1">
      <label
        for="github-issue-token"
        class="block text-sm font-medium text-gray-700"
      >
        {{ t('relay.githubToken') }}
        <span class="text-red-500">*</span>
      </label>
      <div class="relative">
        <input
          id="github-issue-token"
          v-model="config.token"
          :type="showToken ? 'text' : 'password'"
          class="input pr-10"
          :placeholder="t('relay.githubTokenPlaceholder')"
          autocomplete="new-password"
          required
        />
        <button
          type="button"
          class="absolute inset-y-0 right-0 flex items-center px-3 text-sm text-gray-500 transition hover:text-gray-800"
          :aria-label="showToken ? t('common.hide') : t('common.show')"
          :title="showToken ? t('common.hide') : t('common.show')"
          @click="showToken = !showToken"
        >
          {{ showToken ? t('common.hide') : t('common.show') }}
        </button>
      </div>
      <p class="text-xs text-gray-500">
        {{ t('relay.githubTokenHelp') }}
      </p>
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div>
        <label
          for="github-issue-labels"
          class="mb-1 block text-sm font-medium text-gray-700"
        >
          {{ t('relay.githubLabels') }}
        </label>
        <textarea
          id="github-issue-labels"
          v-model="config.labels_text"
          class="input min-h-[96px]"
          :placeholder="t('relay.githubLabelsPlaceholder')"
        />
        <p class="mt-1 text-xs text-gray-500">
          {{ t('relay.githubLabelsHelp') }}
        </p>
      </div>

      <div>
        <label
          for="github-issue-assignees"
          class="mb-1 block text-sm font-medium text-gray-700"
        >
          {{ t('relay.githubAssignees') }}
        </label>
        <textarea
          id="github-issue-assignees"
          v-model="config.assignees_text"
          class="input min-h-[96px]"
          :placeholder="t('relay.githubAssigneesPlaceholder')"
        />
        <p class="mt-1 text-xs text-gray-500">
          {{ t('relay.githubAssigneesHelp') }}
        </p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseInput from '@/components/ui/BaseInput.vue'

const config = defineModel({
  type: Object,
  required: true
})

const { t } = useI18n()
const showToken = ref(false)
</script>
