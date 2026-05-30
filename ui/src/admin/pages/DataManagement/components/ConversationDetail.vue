<template>
  <Transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="visible"
      class="fixed inset-0 z-50 bg-gray-900/50"
      aria-hidden="true"
      @click="$emit('close')"
    />
  </Transition>
  <Transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transition-transform duration-250 ease-in"
    leave-from-class="translate-x-0"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="visible"
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-5xl flex-col bg-white shadow-xl"
      role="region"
      :aria-label="t('dataManagement.conversations.detailTitle')"
    >
      <div
        class="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4"
      >
        <div>
          <h2 class="text-lg font-semibold text-gray-900">
            {{ t('dataManagement.conversations.detailTitle') }}
          </h2>
          <p class="break-all font-mono text-xs text-gray-500">
            {{ conversation?.uuid || '-' }}
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

      <div class="flex-1 overflow-y-auto p-6">
        <BaseLoading v-if="loading" />

        <template v-else-if="conversation">
          <div class="space-y-6">
            <div class="border-b border-gray-200">
              <div
                class="flex gap-6 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
                role="tablist"
                :aria-label="t('dataManagement.conversations.detailTitle')"
              >
                <button
                  v-for="tab in tabs"
                  :key="tab.key"
                  type="button"
                  class="flex-shrink-0 border-b-2 px-1 py-3 text-xs font-medium transition-colors sm:text-sm"
                  role="tab"
                  :aria-selected="detailTab === tab.key"
                  :class="
                    detailTab === tab.key
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  "
                  @click="$emit('update:detailTab', tab.key)"
                >
                  {{ tab.label }}
                </button>
              </div>
            </div>

            <div v-if="detailTab === 'ai'" class="space-y-6">
              <section class="space-y-4">
                <div class="flex items-center justify-between gap-3">
                  <h3 class="text-sm font-semibold text-gray-900">
                    {{ t('dataManagement.conversations.aiSectionTitle') }}
                  </h3>
                  <StatusBadge
                    :status="mapConversationStatus(conversation.status)"
                  />
                </div>

                <div
                  class="space-y-4 rounded-lg border border-gray-200 bg-white p-4"
                >
                  <div class="space-y-2">
                    <div
                      class="text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {{ t('dataManagement.conversations.summaryTitle') }}
                    </div>
                    <h4
                      v-if="getConversationDisplayTitle(conversation)"
                      class="text-lg font-medium text-gray-900"
                    >
                      {{ getConversationDisplayTitle(conversation) }}
                    </h4>
                  </div>

                  <div v-if="conversation.summary_content">
                    <MarkdownRenderer :content="conversation.summary_content" />
                  </div>
                </div>

                <div
                  v-if="conversation.llm_content"
                  class="space-y-3 rounded-lg border border-gray-200 bg-white p-4"
                >
                  <div
                    class="text-xs font-semibold uppercase tracking-wider text-gray-500"
                  >
                    {{ t('dataManagement.conversations.aiLlmContent') }}
                  </div>
                  <MarkdownRenderer :content="conversation.llm_content" />
                </div>

                <section
                  v-if="
                    conversation.metadata &&
                    Object.keys(conversation.metadata).length
                  "
                  class="space-y-3"
                >
                  <h3 class="text-sm font-semibold text-gray-900">
                    {{ t('dataManagement.conversations.metadataTitle') }}
                  </h3>
                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <pre
                      class="whitespace-pre-wrap break-words font-mono text-xs text-gray-800"
                      >{{ formatJson(conversation.metadata) }}</pre
                    >
                  </div>
                </section>
              </section>

              <section class="space-y-4">
                <h3 class="text-sm font-semibold text-gray-900">
                  {{ t('dataManagement.conversations.todosTitle') }}
                </h3>
                <div v-if="conversationTodos.length" class="space-y-3">
                  <article
                    v-for="(todo, index) in conversationTodos"
                    :key="todo.id || `${todo.content}-${index}`"
                    class="rounded-lg border border-gray-200 bg-white p-4"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0">
                        <div
                          class="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500"
                        >
                          {{ index + 1 }} /
                          {{ t('dataManagement.conversations.todoLabel') }}
                        </div>
                        <div
                          class="whitespace-pre-wrap text-sm font-medium text-gray-900"
                        >
                          {{ todo.content || '-' }}
                        </div>
                      </div>
                      <span
                        class="shrink-0 rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700"
                      >
                        {{ todo.priority || '-' }}
                      </span>
                    </div>
                    <div
                      class="mt-3 grid grid-cols-1 gap-3 text-xs text-gray-500 md:grid-cols-3"
                    >
                      <div>owner: {{ todo.owner || '-' }}</div>
                      <div>deadline: {{ formatDateTime(todo.deadline) }}</div>
                      <div>location: {{ todo.location || '-' }}</div>
                    </div>
                  </article>
                </div>
                <div
                  v-else
                  class="rounded-lg border border-gray-200 bg-gray-50 py-8 text-center text-sm text-gray-500"
                >
                  {{ t('dataManagement.conversations.noTodos') }}
                </div>
              </section>
            </div>

            <div v-else-if="detailTab === 'relay'" class="space-y-4">
              <section class="space-y-4">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('dataManagement.conversations.relayDetailTitle') }}
                    </h3>
                    <p class="mt-1 text-xs text-gray-500">
                      {{ t('dataManagement.conversations.relayDetailHint') }}
                    </p>
                  </div>
                  <span class="text-sm text-gray-500">
                    {{
                      t('dataManagement.conversations.relayCount', {
                        count: relayDeliveries.length
                      })
                    }}
                  </span>
                </div>

                <div v-if="relayDeliveries.length" class="space-y-3">
                  <article
                    v-for="delivery in relayDeliveries"
                    :key="delivery.id"
                    class="grid grid-cols-[1.5fr_2fr_1fr_auto] items-center gap-4 rounded-lg border border-gray-200 bg-white px-4 py-3"
                  >
                    <span class="text-sm font-medium text-gray-900">
                      {{
                        delivery.subscription_name ||
                        delivery.target_type ||
                        '-'
                      }}
                    </span>
                    <a
                      v-if="delivery.external_url"
                      :href="delivery.external_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      :title="delivery.external_url"
                      class="block truncate text-xs text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {{ delivery.external_url }}
                    </a>
                    <span
                      v-else-if="delivery.external_id"
                      class="truncate text-xs text-gray-600"
                      :title="delivery.external_id"
                    >
                      {{ delivery.external_id }}
                    </span>
                    <span v-else class="text-xs text-gray-400">-</span>
                    <span class="text-xs text-gray-500">
                      {{ formatDateTime(delivery.created_at) }}
                    </span>
                    <StatusBadge
                      :status="normalizeRelayStatus(delivery.status)"
                    />
                  </article>
                </div>
                <div
                  v-else
                  class="rounded-lg border border-gray-200 bg-gray-50 py-8 text-center text-sm text-gray-500"
                >
                  {{ t('dataManagement.conversations.relayNone') }}
                </div>
              </section>
            </div>

            <div v-else-if="detailTab === 'raw'" class="space-y-6">
              <section class="space-y-4">
                <h3 class="text-sm font-semibold text-gray-900">
                  {{ t('dataManagement.conversations.rawInfoTitle') }}
                </h3>
                <dl class="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div class="rounded-lg border border-gray-200 bg-white p-4">
                    <dt
                      class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {{ t('dataManagement.conversations.subject') }}
                    </dt>
                    <dd class="break-words text-sm font-medium text-gray-900">
                      {{ conversation.subject || '-' }}
                    </dd>
                  </div>
                  <div class="rounded-lg border border-gray-200 bg-white p-4">
                    <dt
                      class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {{ t('dataManagement.conversations.messageId') }}
                    </dt>
                    <dd
                      class="break-all font-mono text-sm font-medium text-gray-900"
                    >
                      {{ conversation.message_id || '-' }}
                    </dd>
                  </div>
                  <div class="rounded-lg border border-gray-200 bg-white p-4">
                    <dt
                      class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {{ t('dataManagement.conversations.sender') }}
                    </dt>
                    <dd class="break-words text-sm font-medium text-gray-900">
                      {{ conversation.sender || '-' }}
                    </dd>
                  </div>
                  <div class="rounded-lg border border-gray-200 bg-white p-4">
                    <dt
                      class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {{ t('dataManagement.conversations.recipients') }}
                    </dt>
                    <dd class="break-words text-sm font-medium text-gray-900">
                      {{ conversation.recipients || '-' }}
                    </dd>
                  </div>
                  <div class="rounded-lg border border-gray-200 bg-white p-4">
                    <dt
                      class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {{ t('taskManagement.list.status') }}
                    </dt>
                    <dd>
                      <StatusBadge
                        :status="mapConversationStatus(conversation.status)"
                      />
                    </dd>
                  </div>
                  <div class="rounded-lg border border-gray-200 bg-white p-4">
                    <dt
                      class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {{ t('dataManagement.conversations.receivedAt') }}
                    </dt>
                    <dd class="text-sm font-medium text-gray-900">
                      {{ formatDateTime(conversation.received_at) }}
                    </dd>
                  </div>
                </dl>
              </section>

              <section class="space-y-3">
                <h3 class="text-sm font-semibold text-gray-900">
                  {{ t('dataManagement.conversations.rawTextTitle') }}
                </h3>
                <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <pre
                    class="whitespace-pre-wrap break-words font-mono text-xs text-gray-800"
                    >{{ conversation.text_content || '-' }}</pre
                  >
                </div>
              </section>
            </div>

            <div v-else-if="detailTab === 'attachments'" class="space-y-4">
              <div class="flex items-center justify-between gap-3">
                <h3 class="text-sm font-semibold text-gray-900">
                  {{ t('dataManagement.conversations.attachmentsTitle') }}
                </h3>
                <span class="text-xs text-gray-500">
                  {{ t('dataManagement.conversations.imagesAlreadyShown') }}
                </span>
              </div>

              <div
                v-if="nonImageAttachments.length"
                class="overflow-x-auto rounded-lg border border-gray-200"
              >
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                      >
                        {{ t('dataManagement.conversations.attachmentName') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                      >
                        {{ t('dataManagement.conversations.attachmentType') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                      >
                        {{ t('dataManagement.conversations.attachmentSize') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                      >
                        {{
                          t('dataManagement.conversations.attachmentSafeName')
                        }}
                      </th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100 bg-white">
                    <tr
                      v-for="attachment in nonImageAttachments"
                      :key="attachment.id"
                    >
                      <td
                        class="px-4 py-3 break-all text-sm font-medium text-gray-900"
                      >
                        {{ attachment.filename || '-' }}
                      </td>
                      <td class="px-4 py-3 break-all text-sm text-gray-500">
                        {{ attachment.content_type || '-' }}
                      </td>
                      <td class="px-4 py-3 text-sm text-gray-500">
                        {{ formatBytes(attachment.file_size) }}
                      </td>
                      <td
                        class="px-4 py-3 break-all font-mono text-sm text-gray-500"
                      >
                        {{ attachment.safe_filename || '-' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div
                v-else
                class="rounded-lg border border-gray-200 bg-gray-50 py-12 text-center text-sm text-gray-500"
              >
                {{ t('dataManagement.conversations.noAttachments') }}
              </div>
            </div>

            <div v-else class="space-y-4">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h3 class="text-sm font-semibold text-gray-900">
                    {{ t('dataManagement.conversations.tabTaskManagement') }}
                  </h3>
                  <p class="mt-1 text-xs text-gray-500">
                    {{ t('dataManagement.conversations.taskHint') }}
                  </p>
                </div>
                <span class="text-sm text-gray-500">
                  {{ t('common.pagination.showing', taskPaginationShowing) }}
                </span>
              </div>

              <BaseLoading v-if="relatedTasksLoading" />

              <div
                v-else-if="!relatedTasks.length"
                class="rounded-lg border border-gray-200 bg-gray-50 py-12 text-center"
              >
                <p class="text-sm font-medium text-gray-600">
                  {{ t('taskManagement.list.noTasks') }}
                </p>
              </div>

              <template v-else>
                <div class="overflow-x-auto rounded-lg border border-gray-200">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th
                          class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                        >
                          {{ t('dataManagement.conversations.taskStage') }}
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                        >
                          {{ t('taskManagement.list.taskName') }}
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                        >
                          {{ t('taskManagement.list.module') }}
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                        >
                          {{ t('taskManagement.list.status') }}
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                        >
                          {{ t('taskManagement.list.taskId') }}
                        </th>
                        <th
                          class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
                        >
                          {{ t('taskManagement.list.createdAt') }}
                        </th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100 bg-white">
                      <tr
                        v-for="(task, index) in relatedTasks"
                        :key="task.id"
                        class="cursor-pointer transition-colors hover:bg-gray-50"
                        :class="
                          selectedTaskExecution?.id === task.id
                            ? 'bg-primary-50'
                            : ''
                        "
                        @click="$emit('open-task', task)"
                      >
                        <td
                          class="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900"
                        >
                          {{ taskStageLabel(index) }}
                        </td>
                        <td
                          class="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900"
                        >
                          {{ task.task_name || '-' }}
                        </td>
                        <td
                          class="whitespace-nowrap px-4 py-3 text-sm text-gray-500"
                        >
                          {{ task.module || '-' }}
                        </td>
                        <td class="whitespace-nowrap px-4 py-3">
                          <StatusBadge :status="mapTaskStatus(task.status)" />
                        </td>
                        <td
                          class="break-all px-4 py-3 font-mono text-sm text-gray-500"
                        >
                          {{ task.task_id || '-' }}
                        </td>
                        <td
                          class="whitespace-nowrap px-4 py-3 text-sm text-gray-500"
                        >
                          {{ formatDate(task.created_at) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div
                  v-if="taskTotalCount > taskPageSize"
                  class="flex flex-wrap items-center justify-between gap-2 border-t border-gray-200 pt-4"
                >
                  <p class="text-sm text-gray-600">
                    {{ t('common.pagination.showing', taskPaginationShowing) }}
                  </p>
                  <div class="flex items-center gap-2">
                    <select
                      :value="taskPageSize"
                      class="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                      @change="
                        $emit(
                          'change-task-page-size',
                          Number($event.target.value)
                        )
                      "
                    >
                      <option :value="10">10</option>
                      <option :value="20">20</option>
                      <option :value="50">50</option>
                    </select>
                    <BaseButton
                      variant="outline"
                      size="sm"
                      :disabled="taskPage <= 1"
                      @click="$emit('previous-task-page')"
                    >
                      {{ t('common.pagination.previous') }}
                    </BaseButton>
                    <BaseButton
                      variant="outline"
                      size="sm"
                      :disabled="taskPage >= taskTotalPages"
                      @click="$emit('next-task-page')"
                    >
                      {{ t('common.pagination.next') }}
                    </BaseButton>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <Transition
            enter-active-class="transition-opacity duration-200 ease-out"
            enter-from-class="opacity-0"
            enter-to-class="opacity-100"
            leave-active-class="transition-opacity duration-150 ease-in"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
          >
            <div
              v-if="showTaskDetail && selectedTaskExecution"
              class="fixed inset-0 z-[60]"
              role="presentation"
            >
              <div
                class="absolute inset-0 bg-gray-900/20"
                @click="$emit('close-task-detail')"
              />

              <aside
                class="absolute right-0 top-0 flex h-full w-full max-w-4xl flex-col bg-white shadow-2xl"
                role="region"
                :aria-label="t('taskManagement.list.details')"
              >
                <div
                  class="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4"
                >
                  <div>
                    <h2 class="text-lg font-semibold text-gray-900">
                      {{ t('taskManagement.list.details') }}
                    </h2>
                    <p class="break-all font-mono text-xs text-gray-500">
                      {{ selectedTaskExecution.task_id || '-' }}
                    </p>
                  </div>
                  <button
                    type="button"
                    class="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                    :aria-label="t('common.close')"
                    @click="$emit('close-task-detail')"
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

                <div class="flex-1 overflow-y-auto p-6">
                  <dl class="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <dt
                        class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                      >
                        {{ t('taskManagement.list.taskName') }}
                      </dt>
                      <dd class="break-all text-sm font-medium text-gray-900">
                        {{ selectedTaskExecution.task_name || '-' }}
                      </dd>
                    </div>
                    <div>
                      <dt
                        class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                      >
                        {{ t('taskManagement.list.module') }}
                      </dt>
                      <dd class="break-all text-sm font-medium text-gray-900">
                        {{ selectedTaskExecution.module || '-' }}
                      </dd>
                    </div>
                    <div>
                      <dt
                        class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                      >
                        {{ t('taskManagement.list.status') }}
                      </dt>
                      <dd>
                        <StatusBadge
                          :status="mapTaskStatus(selectedTaskExecution.status)"
                        />
                      </dd>
                    </div>
                    <div>
                      <dt
                        class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                      >
                        {{ t('taskManagement.list.taskId') }}
                      </dt>
                      <dd
                        class="break-all font-mono text-sm font-medium text-gray-900"
                      >
                        {{ selectedTaskExecution.task_id || '-' }}
                      </dd>
                    </div>
                    <div>
                      <dt
                        class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                      >
                        {{ t('taskManagement.list.createdBy') }}
                      </dt>
                      <dd class="text-sm font-medium text-gray-900">
                        {{ selectedTaskExecution.created_by_username || '-' }}
                      </dd>
                    </div>
                    <div>
                      <dt
                        class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500"
                      >
                        {{ t('taskManagement.list.duration') }}
                      </dt>
                      <dd class="text-sm font-medium text-gray-900">
                        {{ formatDuration(selectedTaskExecution.duration) }}
                      </dd>
                    </div>
                  </dl>

                  <div
                    v-if="currentProgressText"
                    class="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800"
                  >
                    <span class="font-medium"
                      >{{ t('taskManagement.list.currentProgress') }}:</span
                    >
                    {{ currentProgressText }}
                  </div>

                  <div
                    v-if="detailSteps.length"
                    class="rounded-lg border border-gray-200 bg-white"
                  >
                    <div class="divide-y divide-gray-200">
                      <div
                        v-for="(item, index) in detailSteps"
                        :key="index"
                        class="bg-white p-4 hover:bg-gray-50"
                        :class="
                          item.level === 'ERROR'
                            ? 'border-l-4 border-l-red-500'
                            : item.level === 'WARNING'
                              ? 'border-l-4 border-l-amber-500'
                              : ''
                        "
                      >
                        <div class="flex items-start gap-3">
                          <span
                            class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gray-200 text-xs font-semibold text-gray-600"
                          >
                            {{ index + 1 }}
                          </span>
                          <div class="min-w-0 flex-1">
                            <div class="mb-1 flex flex-wrap items-center gap-2">
                              <span
                                v-if="item.level"
                                class="inline-flex rounded px-2 py-0.5 text-xs font-medium"
                                :class="logLevelClass(item.level)"
                              >
                                {{ item.level }}
                              </span>
                              <span
                                v-if="item.title"
                                class="text-xs font-semibold text-gray-700"
                              >
                                {{ item.title }}
                              </span>
                              <span
                                v-if="item.progressSummary"
                                class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
                              >
                                {{ item.progressSummary }}
                              </span>
                              <span
                                v-if="item.timestamp"
                                class="text-xs text-gray-500"
                              >
                                {{ formatStepTime(item.timestamp) }}
                              </span>
                            </div>
                            <p
                              v-if="item.message"
                              class="whitespace-pre-wrap break-words text-sm text-gray-800"
                            >
                              {{ item.message }}
                            </p>
                            <div
                              v-if="item.contextLabels.length"
                              class="mt-2 flex flex-wrap gap-2"
                            >
                              <span
                                v-for="label in item.contextLabels"
                                :key="label"
                                class="inline-flex items-center rounded-full bg-gray-50 px-2 py-0.5 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-200"
                              >
                                {{ label }}
                              </span>
                            </div>
                            <pre
                              v-if="item.exception"
                              class="mt-2 rounded border border-red-100 bg-red-50 p-2 whitespace-pre-wrap break-words font-mono text-xs text-red-700"
                              >{{ item.exception }}</pre
                            >
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    v-if="
                      selectedTaskExecution.result !== undefined &&
                      selectedTaskExecution.result !== null
                    "
                    class="rounded-lg border border-gray-200 bg-white p-4"
                  >
                    <h5 class="mb-3 text-sm font-semibold text-gray-900">
                      {{ t('taskManagement.list.result') }}
                    </h5>
                    <pre
                      class="whitespace-pre-wrap break-words font-mono text-xs text-gray-800"
                      >{{ formatJson(selectedTaskExecution.result) }}</pre
                    >
                  </div>

                  <div
                    v-if="selectedTaskExecution.error"
                    class="rounded-lg border border-red-200 bg-red-50 p-4"
                  >
                    <h5 class="mb-3 text-sm font-semibold text-red-900">
                      {{ t('taskManagement.list.error') }}
                    </h5>
                    <pre
                      class="whitespace-pre-wrap break-words font-mono text-xs text-red-800"
                      >{{ selectedTaskExecution.error }}</pre
                    >
                  </div>

                  <div
                    v-if="selectedTaskExecution.traceback"
                    class="rounded-lg border border-red-200 bg-red-50 p-4"
                  >
                    <h5 class="mb-3 text-sm font-semibold text-red-900">
                      {{ t('taskManagement.list.traceback') }}
                    </h5>
                    <pre
                      class="whitespace-pre-wrap break-words font-mono text-xs text-red-800"
                      >{{ selectedTaskExecution.traceback }}</pre
                    >
                  </div>
                </div>
              </aside>
            </div>
          </Transition>
        </template>
      </div>
    </aside>
  </Transition>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { formatDuration } from '@/utils/formatting'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import MarkdownRenderer from '@/components/ui/MarkdownRenderer.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  conversation: {
    type: Object,
    default: null
  },
  detailTab: {
    type: String,
    default: 'ai'
  },
  tabs: {
    type: Array,
    default: () => []
  },
  conversationTodos: {
    type: Array,
    default: () => []
  },
  nonImageAttachments: {
    type: Array,
    default: () => []
  },
  relayDeliveries: {
    type: Array,
    default: () => []
  },
  relatedTasksLoading: {
    type: Boolean,
    default: false
  },
  relatedTasks: {
    type: Array,
    default: () => []
  },
  selectedTaskExecution: {
    type: Object,
    default: null
  },
  showTaskDetail: {
    type: Boolean,
    default: false
  },
  detailSteps: {
    type: Array,
    default: () => []
  },
  currentProgressText: {
    type: String,
    default: ''
  },
  taskPaginationShowing: {
    type: Object,
    required: true
  },
  taskPage: {
    type: Number,
    required: true
  },
  taskPageSize: {
    type: Number,
    required: true
  },
  taskTotalCount: {
    type: Number,
    required: true
  },
  taskTotalPages: {
    type: Number,
    required: true
  }
})

defineEmits([
  'close',
  'update:detailTab',
  'open-task',
  'close-task-detail',
  'change-task-page-size',
  'previous-task-page',
  'next-task-page'
])

const { t } = useI18n()

function formatJson(value) {
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function formatDate(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}

function formatDateTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}

function formatBytes(value) {
  const size = Number(value)
  if (!Number.isFinite(size) || size < 0) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  if (size < 1024 * 1024 * 1024)
    return `${(size / (1024 * 1024)).toFixed(1)} MB`
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatStepTime(value) {
  if (value == null) return ''
  try {
    const date =
      typeof value === 'number' ? new Date(value * 1000) : new Date(value)
    if (Number.isNaN(date.getTime())) return String(value)
    return date.toLocaleString()
  } catch {
    return String(value)
  }
}

function logLevelClass(level) {
  const map = {
    ERROR: 'bg-red-100 text-red-800',
    WARNING: 'bg-amber-100 text-amber-800',
    INFO: 'bg-blue-100 text-blue-800',
    DEBUG: 'bg-gray-100 text-gray-600',
    CRITICAL: 'bg-red-200 text-red-900'
  }
  return map[level] || 'bg-gray-100 text-gray-700'
}

function mapConversationStatus(status) {
  const normalized = String(status || '').toLowerCase()
  const map = {
    fetched: 'pending',
    processing: 'processing',
    success: 'success',
    failed: 'failed'
  }
  return map[normalized] || normalized || 'pending'
}

function mapTaskStatus(status) {
  const map = {
    PENDING: 'pending',
    STARTED: 'processing',
    SUCCESS: 'success',
    FAILURE: 'failed',
    RETRY: 'processing',
    REVOKED: 'failed'
  }
  return map[status] || (status && status.toLowerCase()) || 'pending'
}

function normalizeRelayStatus(status) {
  const value = String(status || '').toLowerCase()
  if (!value) return 'pending'
  if (value.includes('success') || value.includes('sent')) return 'success'
  if (value.includes('fail') || value.includes('error')) return 'failed'
  if (value.includes('retry') || value.includes('send')) return 'processing'
  return 'pending'
}

function taskStageLabel(index) {
  return t('dataManagement.conversations.taskStage', {
    index: index + 1
  })
}

function getConversationDisplayTitle(conversation) {
  if (!conversation) return '-'
  return (
    conversation.summary_title ||
    conversation.subject ||
    conversation.text_content ||
    '-'
  )
}
</script>
