<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-gray-900">
          {{ t('todos.title') }}
        </h1>
        <!-- View Toggle (Web only) -->
        <div class="hidden md:flex items-center gap-2">
          <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              @click="viewMode = 'list'"
              :class="[
                'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                viewMode === 'list'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              {{ t('todos.view.list') }}
            </button>
            <button
              @click="viewMode = 'calendar'"
              :class="[
                'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                viewMode === 'calendar'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              {{ t('todos.view.calendar') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <div
        v-if="errorMessage"
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
            <p class="text-sm font-medium text-red-800">{{ errorMessage }}</p>
          </div>
          <button
            @click="errorMessage = ''"
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

      <!-- Success Message -->
      <div
        v-if="successMessage"
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
              {{ successMessage }}
            </p>
          </div>
          <button
            @click="successMessage = ''"
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

      <!-- Stats Chart -->
      <TodoStatsChart :stats="stats" />

      <!-- Filters and Time Range -->
      <BaseCard>
        <div class="p-4 space-y-4 relative">
          <!-- Loading Overlay -->
          <div
            v-if="loading"
            class="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10 rounded-lg"
          >
            <div class="flex items-center gap-2 text-sm text-gray-600">
              <svg
                class="animate-spin h-4 w-4 text-primary-600"
                xmlns="http://www.w3.org/2000/svg"
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
              <span>{{ t('common.loading') }}</span>
            </div>
          </div>

          <!-- Time Range Filter (Separate Row) -->
          <!-- List View: Time Range Selector -->
          <div
            v-if="viewMode === 'list'"
            class="flex flex-col sm:flex-row items-start sm:items-end gap-3"
            :class="{ 'opacity-50': loading }"
          >
            <div class="flex-1 w-full sm:w-auto">
              <label class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('todos.timeRange.title') }}
              </label>
              <select
                v-model="timeRange"
                @change="selectTimeRange(timeRange)"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              >
                <option
                  v-for="range in timeRanges"
                  :key="range.value"
                  :value="range.value"
                >
                  {{ range.label }}
                </option>
                <option value="custom">
                  {{ t('todos.timeRange.custom') }}
                </option>
              </select>
            </div>
            <!-- Date Range (Always visible, readonly when not custom) -->
            <div
              class="flex-1 w-full sm:w-auto flex flex-col sm:flex-row items-stretch sm:items-end gap-3 sm:gap-2 min-w-0"
            >
              <div class="flex-1 w-full sm:w-auto min-w-0">
                <label class="block text-xs text-gray-500 mb-1">{{
                  t('todos.timeRange.startDate')
                }}</label>
                <input
                  type="date"
                  v-model="displayStartDate"
                  @change="handleCustomDateChange"
                  :readonly="timeRange !== 'custom'"
                  :class="[
                    'w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500',
                    timeRange !== 'custom'
                      ? 'bg-gray-50 cursor-not-allowed'
                      : ''
                  ]"
                />
              </div>
              <div class="flex-shrink-0 hidden sm:block sm:pt-6">
                <span class="text-sm text-gray-500">-</span>
              </div>
              <div class="flex-1 w-full sm:w-auto min-w-0">
                <label class="block text-xs text-gray-500 mb-1">{{
                  t('todos.timeRange.endDate')
                }}</label>
                <input
                  type="date"
                  v-model="displayEndDate"
                  @change="handleCustomDateChange"
                  :readonly="timeRange !== 'custom'"
                  :class="[
                    'w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500',
                    timeRange !== 'custom'
                      ? 'bg-gray-50 cursor-not-allowed'
                      : ''
                  ]"
                />
              </div>
            </div>
          </div>

          <!-- Calendar View: Calendar View Mode Selector (Month/Week) -->
          <div
            v-if="viewMode === 'calendar'"
            class="flex flex-col sm:flex-row items-start sm:items-end gap-3"
            :class="{ 'opacity-50': loading }"
          >
            <div class="flex-1 w-full sm:w-auto">
              <label class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('todos.calendar.viewMode') }}
              </label>
              <select
                v-model="calendarViewMode"
                @change="handleCalendarViewModeChange"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="month">
                  {{ t('todos.calendar.monthView') }}
                </option>
                <option value="week">{{ t('todos.calendar.weekView') }}</option>
              </select>
            </div>
          </div>

          <!-- Filter Inputs -->
          <div
            class="grid grid-cols-1 md:grid-cols-4 gap-4"
            :class="{ 'opacity-50': loading }"
          >
            <!-- Status Filter -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('todos.filters.status') }}
              </label>
              <select
                v-model="filters.is_completed"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              >
                <option :value="null">{{ t('todos.filters.all') }}</option>
                <option :value="false">
                  {{ t('todos.filters.incomplete') }}
                </option>
                <option :value="true">
                  {{ t('todos.filters.completed') }}
                </option>
              </select>
            </div>

            <!-- Priority Filter -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('todos.filters.priority') }}
              </label>
              <select
                v-model="filters.priority"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              >
                <option :value="null">{{ t('todos.filters.all') }}</option>
                <option value="high">{{ t('todos.priority.high') }}</option>
                <option value="medium">
                  {{ t('todos.priority.medium') }}
                </option>
                <option value="low">{{ t('todos.priority.low') }}</option>
              </select>
            </div>

            <!-- Owner Filter -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('todos.filters.owner') }}
              </label>
              <input
                v-model="filters.owner"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                :placeholder="t('todos.filters.owner')"
              />
            </div>

            <!-- Search -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('common.search') }}
              </label>
              <input
                v-model="filters.search"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                :placeholder="t('todos.filters.search')"
              />
            </div>
          </div>

          <!-- Active Filters Display -->
          <div
            v-if="hasActiveFilters"
            class="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-200"
          >
            <span class="text-xs font-medium text-gray-500">
              {{ t('todos.filters.activeFilters') }}:
            </span>
            <span
              v-for="(filter, key) in activeFilters"
              :key="key"
              class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded-md text-xs font-medium cursor-pointer hover:bg-primary-200 transition-colors"
              @click="removeFilter(key)"
            >
              {{ filter.label }}: {{ filter.value }}
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </span>
            <button
              v-if="hasActiveFilters"
              @click="clearFilters"
              class="text-xs text-gray-500 hover:text-gray-700 underline"
            >
              {{ t('todos.filters.clearAll') }}
            </button>
          </div>
        </div>
      </BaseCard>

      <!-- Calendar View (Hidden on mobile, only show when viewMode is calendar) -->
      <BaseCard v-if="viewMode === 'calendar'" class="hidden md:block">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <button
                @click="previousPeriod"
                class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </button>
              <h2 class="text-lg font-semibold text-gray-900">
                {{
                  calendarViewMode === 'week'
                    ? currentWeekLabel
                    : currentMonthLabel
                }}
              </h2>
              <button
                @click="nextPeriod"
                class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
              >
                <svg
                  class="w-5 h-5"
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
        </template>

        <div class="p-4">
          <!-- Calendar Grid -->
          <div class="grid grid-cols-7 gap-2 mb-4">
            <div
              v-for="day in weekDays"
              :key="day"
              class="text-center text-sm font-medium text-gray-700 py-2"
            >
              {{ day }}
            </div>
          </div>

          <div class="grid grid-cols-7 gap-2">
            <div
              v-for="(date, index) in calendarDays"
              :key="index"
              :class="[
                'min-h-[80px] p-2 border rounded cursor-pointer transition-colors',
                date.isCurrentMonth
                  ? 'bg-white border-gray-200 hover:border-primary-500 hover:bg-primary-50'
                  : 'bg-gray-50 border-gray-100 text-gray-400',
                date.isToday ? 'ring-2 ring-primary-500' : '',
                selectedDate && isSameDay(date.date, selectedDate)
                  ? 'bg-primary-100 border-primary-500'
                  : ''
              ]"
              @click="selectDate(date.date)"
            >
              <div class="text-sm font-medium mb-1">
                {{ date.day }}
              </div>
              <div class="space-y-1 max-h-[60px] overflow-hidden">
                <template
                  v-for="(todo, todoIndex) in getTodosForDate(date.date).slice(
                    0,
                    3
                  )"
                  :key="todo.id"
                >
                  <div
                    :class="[
                      'text-xs px-1 py-0.5 rounded truncate',
                      todo.is_completed
                        ? 'bg-gray-200 text-gray-600 line-through'
                        : todo.priority === 'high'
                          ? 'bg-red-100 text-red-700'
                          : todo.priority === 'medium'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-blue-100 text-blue-700'
                    ]"
                    @click.stop="handleCalendarTodoClick(todo, date.date)"
                  >
                    {{ todo.content }}
                  </div>
                </template>
                <div
                  v-if="getTodosForDate(date.date).length > 3"
                  class="text-xs px-1 py-0.5 rounded bg-gray-100 text-gray-600 cursor-pointer hover:bg-gray-200"
                  @click.stop="selectDate(date.date)"
                >
                  {{
                    t('todos.calendar.moreTodos', {
                      count: getTodosForDate(date.date).length - 3
                    })
                  }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </BaseCard>

      <!-- Todos List (Always show, default to all todos in current month) -->
      <BaseCard
        v-if="todos.length > 0 || tempNewTodo"
        ref="selectedDateCard"
        class="relative"
      >
        <!-- Loading overlay -->
        <Transition name="fade">
          <div
            v-if="calendarClickLoading"
            class="absolute inset-0 bg-white bg-opacity-75 z-10 flex items-center justify-center rounded-lg"
          >
            <div class="flex flex-col items-center gap-2">
              <svg
                class="animate-spin h-6 w-6 text-primary-600"
                xmlns="http://www.w3.org/2000/svg"
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
              <span class="text-sm text-gray-600">{{
                t('common.loading') || 'Loading...'
              }}</span>
            </div>
          </div>
        </Transition>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold">
              {{
                selectedDate
                  ? formatSelectedDate(selectedDate)
                  : t('todos.allTodos')
              }}
            </h3>
            <div class="flex items-center gap-2">
              <!-- Group By Selector -->
              <select
                v-model="groupBy"
                class="text-xs px-2 py-1 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="date">{{ t('todos.groupBy.date') }}</option>
                <option value="email">{{ t('todos.groupBy.subject') }}</option>
                <option value="owner">{{ t('todos.groupBy.owner') }}</option>
                <option value="priority">
                  {{ t('todos.groupBy.priority') }}
                </option>
                <option value="category">
                  {{ t('todos.groupBy.category') }}
                </option>
                <option value="location">
                  {{ t('todos.groupBy.location') }}
                </option>
              </select>
              <BaseButton
                v-if="selectedDate"
                @click="selectedDate = null"
                variant="secondary"
                size="sm"
              >
                {{ t('common.close') }}
              </BaseButton>
            </div>
          </div>
        </template>

        <div class="p-4">
          <div
            v-for="(group, key) in groupedTodos"
            :key="key"
            class="mb-6 last:mb-0"
          >
            <!-- Group Header -->
            <div
              class="flex items-center gap-2 mb-3 pb-2 border-b border-gray-200"
            >
              <!-- Date Icon -->
              <svg
                v-if="groupBy === 'date'"
                class="w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <!-- Owner Icon -->
              <svg
                v-else-if="groupBy === 'owner'"
                class="w-4 h-4 text-gray-500"
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
              <!-- Priority Icon -->
              <svg
                v-else-if="groupBy === 'priority'"
                class="w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <!-- Category Icon -->
              <svg
                v-else-if="groupBy === 'category'"
                class="w-4 h-4 text-gray-500"
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
              <!-- Location Icon -->
              <svg
                v-else-if="groupBy === 'location'"
                class="w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              <!-- Email Icon -->
              <svg
                v-else-if="groupBy === 'email'"
                class="w-4 h-4 text-gray-500"
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
              <h4 class="text-sm font-semibold text-gray-700">
                {{ getGroupLabel(key, groupBy) }}
              </h4>
              <span class="text-xs text-gray-500">({{ group.length }})</span>
            </div>

            <!-- Timeline Container -->
            <div class="relative pl-4 sm:pl-6 border-l-2 border-gray-200">
              <TransitionGroup
                name="todo-list"
                tag="div"
                class="space-y-4 sm:space-y-3"
              >
                <div
                  v-for="(todo, index) in group"
                  :key="todo.id"
                  class="relative"
                >
                  <!-- Timeline Content -->
                  <div class="pb-4 sm:pb-3 last:pb-0">
                    <TodoItem
                      :todo="todo"
                      :loading="todoLoading[todo.id]"
                      :is-new="todo.id === tempNewTodo?.id"
                      @toggle="handleToggleTodo"
                      @save="handleSaveTodoInline"
                      @delete="handleDeleteTodo"
                      @cancel-new="handleCancelNewTodo"
                    />
                  </div>
                </div>
              </TransitionGroup>
            </div>
          </div>

          <div
            v-if="selectedDateTodos.length === 0 && !tempNewTodo"
            class="text-gray-500 italic text-center py-8"
          >
            <p>
              {{
                selectedDate ? t('todos.noTodosForDate') : t('todos.noTodos')
              }}
            </p>
          </div>
        </div>
      </BaseCard>

      <!-- Todo Editor Modal -->
      <div
        v-if="showTodoEditor"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
        @click.self="closeTodoEditor"
      >
        <div
          class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        >
          <div class="p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-900">
                {{ editingTodo ? t('todos.editTodo') : t('todos.addTodo') }}
              </h3>
              <button
                @click="closeTodoEditor"
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
            <TodoEditor
              :todo="editingTodo"
              :email-message-id="null"
              :loading="savingTodo"
              @save="handleSaveTodo"
              @cancel="closeTodoEditor"
            />
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreferencesStore } from '@/store/preferences'
import { formatDate as formatDateUtil } from '@/utils/timezone'
import { extractErrorMessage } from '@/utils/api'
import { todosApi } from '@/api/todos'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TodoItem from '@/components/TodoItem.vue'
import TodoEditor from '@/components/TodoEditor.vue'
import TodoStatsChart from '@/components/todos/TodoStatsChart.vue'

const { t, locale } = useI18n()
const preferencesStore = usePreferencesStore()

const todos = ref([])
const stats = ref(null)
const loading = ref(false)
const calendarClickLoading = ref(false)
const currentMonth = ref(new Date())
const selectedDate = ref(null)
const viewMode = ref('list') // 'list' or 'calendar', default to 'list'
const timeRange = ref('month') // 'week', 'month', 'quarter', 'custom'
const calendarViewMode = ref('month') // 'month' or 'week' for calendar view
const customStartDate = ref('')
const customEndDate = ref('')

const filters = ref({
  is_completed: null,
  priority: null,
  owner: '',
  search: ''
})

// Active filters for display
const activeFilters = computed(() => {
  const active = {}
  if (filters.value.is_completed !== null) {
    active.is_completed = {
      label: t('todos.filters.status'),
      value: filters.value.is_completed
        ? t('todos.filters.completed')
        : t('todos.filters.incomplete')
    }
  }
  if (filters.value.priority) {
    active.priority = {
      label: t('todos.filters.priority'),
      value: t(`todos.priority.${filters.value.priority}`)
    }
  }
  if (filters.value.owner) {
    active.owner = {
      label: t('todos.filters.owner'),
      value: filters.value.owner
    }
  }
  if (filters.value.search) {
    active.search = {
      label: t('common.search'),
      value: filters.value.search
    }
  }
  return active
})

const hasActiveFilters = computed(() => {
  return Object.keys(activeFilters.value).length > 0
})

const showTodoEditor = ref(false)
const editingTodo = ref(null)
const savingTodo = ref(false)
const todoLoading = ref({})
const errorMessage = ref('')
const successMessage = ref('')
const tempNewTodo = ref(null)
const groupBy = ref('email') // 'date', 'owner', 'priority', 'category', 'location', 'email'

// Time range options (no more than 1 year)
const timeRanges = computed(() => [
  { value: 'week', label: t('todos.timeRange.week') },
  { value: 'month', label: t('todos.timeRange.month') },
  { value: 'quarter', label: t('todos.timeRange.quarter') }
])

// Get time range dates for display (helper function)
const getTimeRangeDates = () => {
  const now = new Date()
  let start, end

  switch (timeRange.value) {
    case 'week':
      // Current week (Monday to Sunday)
      const weekRange = getWeekRangeForDate(now)
      start = weekRange.start
      end = weekRange.end
      break
    case 'month':
      // Current month (use actual current date, not calendar month)
      const year = now.getFullYear()
      const month = now.getMonth()
      start = new Date(year, month, 1)
      end = new Date(year, month + 1, 0, 23, 59, 59, 999)
      break
    case 'quarter':
      // Current quarter
      const quarterMonth = Math.floor(now.getMonth() / 3) * 3
      start = new Date(now.getFullYear(), quarterMonth, 1)
      end = new Date(now.getFullYear(), quarterMonth + 3, 0, 23, 59, 59, 999)
      break
    default:
      // Fallback to current month (use actual current date)
      const defaultYear = now.getFullYear()
      const defaultMonth = now.getMonth()
      start = new Date(defaultYear, defaultMonth, 1)
      end = new Date(defaultYear, defaultMonth + 1, 0, 23, 59, 59, 999)
  }

  // Format dates as YYYY-MM-DD using local timezone (avoid timezone offset issues)
  const formatDateLocal = (date) => {
    if (!date) return ''
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  return {
    start: formatDateLocal(start),
    end: formatDateLocal(end)
  }
}

// Display dates (computed based on time range)
const displayStartDate = computed({
  get() {
    if (timeRange.value === 'custom') {
      return customStartDate.value
    }
    return getTimeRangeDates().start
  },
  set(value) {
    if (timeRange.value === 'custom') {
      customStartDate.value = value
    }
  }
})

const displayEndDate = computed({
  get() {
    if (timeRange.value === 'custom') {
      return customEndDate.value
    }
    return getTimeRangeDates().end
  },
  set(value) {
    if (timeRange.value === 'custom') {
      customEndDate.value = value
    }
  }
})

// Time range label for display
const timeRangeLabel = computed(() => {
  if (timeRange.value === 'custom') {
    if (customStartDate.value && customEndDate.value) {
      return `${customStartDate.value} - ${customEndDate.value}`
    }
    return t('todos.timeRange.custom')
  }
  return timeRanges.value.find((r) => r.value === timeRange.value)?.label || ''
})

const weekDays = computed(() => {
  const days =
    locale.value === 'zh-CN'
      ? ['日', '一', '二', '三', '四', '五', '六']
      : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  return days
})

const currentMonthLabel = computed(() => {
  const year = currentMonth.value.getFullYear()
  const month = currentMonth.value.getMonth()
  const date = new Date(year, month, 1)
  return formatDateUtil(
    date.toISOString(),
    preferencesStore.currentTimezone,
    locale.value === 'zh-CN' ? 'yyyy年MM月' : 'MMMM yyyy',
    locale.value
  )
})

const currentWeekLabel = computed(() => {
  const weekRange = getWeekRangeForDate(currentMonth.value)
  const monday = weekRange.start
  const sunday = weekRange.end

  const startStr = formatDateUtil(
    monday.toISOString(),
    preferencesStore.currentTimezone,
    locale.value === 'zh-CN' ? 'MM月dd日' : 'MMM dd',
    locale.value
  )
  const endStr = formatDateUtil(
    sunday.toISOString(),
    preferencesStore.currentTimezone,
    locale.value === 'zh-CN' ? 'MM月dd日' : 'MMM dd',
    locale.value
  )

  return locale.value === 'zh-CN'
    ? `${startStr} - ${endStr}`
    : `${startStr} - ${endStr}`
})

const completionRate = computed(() => {
  if (!stats.value || stats.value.total === 0) return 0
  return Math.round((stats.value.completed / stats.value.total) * 100)
})

const calendarDays = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const days = []

  if (calendarViewMode.value === 'week') {
    // Week view: show only 7 days of the current week
    const monday = getMondayOfWeek(currentMonth.value)

    for (let i = 0; i < 7; i++) {
      const date = new Date(monday)
      date.setDate(monday.getDate() + i)
      const dateCopy = new Date(date)
      dateCopy.setHours(0, 0, 0, 0)

      days.push({
        date: dateCopy,
        day: date.getDate(),
        isCurrentMonth: true, // In week view, all days are considered current
        isToday: dateCopy.getTime() === today.getTime()
      })
    }
  } else {
    // Month view: show full month (42 days, 6 weeks)
    const year = currentMonth.value.getFullYear()
    const month = currentMonth.value.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const startDate = new Date(firstDay)
    startDate.setDate(startDate.getDate() - startDate.getDay())

    for (let i = 0; i < 42; i++) {
      const date = new Date(startDate)
      date.setDate(startDate.getDate() + i)
      const dateCopy = new Date(date)
      dateCopy.setHours(0, 0, 0, 0)

      days.push({
        date: dateCopy,
        day: date.getDate(),
        isCurrentMonth: date.getMonth() === month,
        isToday: dateCopy.getTime() === today.getTime()
      })
    }
  }

  return days
})

const selectedDateTodos = computed(() => {
  let dateTodos = []

  if (selectedDate.value) {
    // Show todos for selected date
    dateTodos = getTodosForDate(selectedDate.value)
  } else {
    // Show todos based on calendar view mode and current month/week
    if (viewMode.value === 'calendar') {
      if (calendarViewMode.value === 'week') {
        // Week view: show todos for current week
        const weekRange = getWeekRangeForDate(currentMonth.value)
        dateTodos = todos.value.filter((todo) => {
          if (!todo.deadline) return false
          const todoDate = new Date(todo.deadline)
          return todoDate >= weekRange.start && todoDate <= weekRange.end
        })
      } else {
        // Month view: show todos for current month
        dateTodos = todos.value.filter((todo) => {
          if (!todo.deadline) return false
          const todoDate = new Date(todo.deadline)
          const year = todoDate.getFullYear()
          const month = todoDate.getMonth()
          const currentYear = currentMonth.value.getFullYear()
          const currentMonthIndex = currentMonth.value.getMonth()
          return year === currentYear && month === currentMonthIndex
        })
      }
    } else {
      // List view: show all todos for current month (default view)
      dateTodos = todos.value.filter((todo) => {
        if (!todo.deadline) return false
        const todoDate = new Date(todo.deadline)
        const year = todoDate.getFullYear()
        const month = todoDate.getMonth()
        const currentYear = currentMonth.value.getFullYear()
        const currentMonthIndex = currentMonth.value.getMonth()
        return year === currentYear && month === currentMonthIndex
      })
    }
  }

  // Add temporary new todo if exists
  const allTodos = tempNewTodo.value
    ? [tempNewTodo.value, ...dateTodos]
    : dateTodos

  // Sort by created_at (timeline order - oldest first)
  return allTodos.sort((a, b) => {
    // Temp todos go to the end
    if (a.id && a.id.toString().startsWith('temp-')) return 1
    if (b.id && b.id.toString().startsWith('temp-')) return 1

    // Sort by created_at from oldest to newest (timeline order)
    if (a.created_at && b.created_at) {
      return new Date(a.created_at) - new Date(b.created_at)
    }
    if (a.created_at && !b.created_at) return -1
    if (!a.created_at && b.created_at) return 1
    return 0
  })
})

// Group todos by selected method
const groupedTodos = computed(() => {
  if (!selectedDateTodos.value.length) return {}

  const grouped = {}

  selectedDateTodos.value.forEach((todo) => {
    let key = ''

    switch (groupBy.value) {
      case 'date':
        // Group by deadline date
        if (todo.deadline) {
          const date = new Date(todo.deadline)
          date.setHours(0, 0, 0, 0)
          key = date.getTime().toString()
        } else {
          key = 'no-deadline'
        }
        break
      case 'owner':
        key = todo.owner || ''
        break
      case 'priority':
        key = todo.priority || 'none'
        break
      case 'category':
        // Use email_message metadata.category, or 'no-category'
        if (
          todo.email_message &&
          todo.email_message.metadata &&
          todo.email_message.metadata.category
        ) {
          const categories = Array.isArray(todo.email_message.metadata.category)
            ? todo.email_message.metadata.category
            : [todo.email_message.metadata.category]
          key = categories.length > 0 ? categories[0] : 'no-category'
        } else {
          key = 'no-category'
        }
        break
      case 'location':
        key = todo.location || ''
        break
      case 'email':
        // Use email_message summary_title or subject, or 'no-email'
        if (todo.email_message) {
          key =
            todo.email_message.summary_title ||
            todo.email_message.subject ||
            'no-title'
        } else {
          key = 'no-email'
        }
        break
      default:
        key = todo.owner || ''
    }

    if (!grouped[key]) {
      grouped[key] = []
    }
    grouped[key].push(todo)
  })

  // Sort groups based on group type
  const sortedGroups = {}
  const keys = Object.keys(grouped)

  let sortedKeys = []
  switch (groupBy.value) {
    case 'date':
      // Sort by date (timestamp), no-deadline last
      sortedKeys = keys.sort((a, b) => {
        if (a === 'no-deadline' && b !== 'no-deadline') return 1
        if (a !== 'no-deadline' && b === 'no-deadline') return -1
        return parseInt(a) - parseInt(b)
      })
      break
    case 'priority':
      // Sort: high, medium, low, none
      const priorityOrder = { high: 1, medium: 2, low: 3, none: 4 }
      sortedKeys = keys.sort((a, b) => {
        return (priorityOrder[a] || 99) - (priorityOrder[b] || 99)
      })
      break
    case 'owner':
    case 'location':
    case 'category':
      // Sort: non-empty first, then alphabetically
      sortedKeys = keys.sort((a, b) => {
        if (
          (a === '' || a === 'no-category') &&
          b !== '' &&
          b !== 'no-category'
        )
          return 1
        if (
          a !== '' &&
          a !== 'no-category' &&
          (b === '' || b === 'no-category')
        )
          return -1
        return a.localeCompare(b)
      })
      break
    case 'email':
      // Sort: no-email last, then alphabetically
      sortedKeys = keys.sort((a, b) => {
        if (a === 'no-email' && b !== 'no-email') return 1
        if (a !== 'no-email' && b === 'no-email') return -1
        return a.localeCompare(b)
      })
      break
    default:
      sortedKeys = keys
  }

  sortedKeys.forEach((key) => {
    sortedGroups[key] = grouped[key]
  })

  return sortedGroups
})

// Helper function to get Monday of the week for a given date
const getMondayOfWeek = (date) => {
  const dateCopy = new Date(date)
  dateCopy.setHours(0, 0, 0, 0)
  const dayOfWeek = dateCopy.getDay()
  const monday = new Date(dateCopy)
  monday.setDate(dateCopy.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1))
  monday.setHours(0, 0, 0, 0)
  return monday
}

// Helper function to get week range (Monday to Sunday) for a given date
const getWeekRangeForDate = (date) => {
  const monday = getMondayOfWeek(date)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  sunday.setHours(23, 59, 59, 999)
  return { start: monday, end: sunday }
}

// Get group label
const getGroupLabel = (key, type) => {
  if (type === 'date') {
    if (key === 'no-deadline') return t('todos.groupBy.noDeadline')
    const date = new Date(parseInt(key))
    return formatSelectedDate(date)
  } else if (type === 'owner') {
    return key || t('todos.filters.owner') + ': ' + t('todos.notSet')
  } else if (type === 'priority') {
    if (key === 'none')
      return t('todos.priority.label') + ': ' + t('todos.notSet')
    return t('todos.priority.label') + ': ' + t(`todos.priority.${key}`)
  } else if (type === 'category') {
    if (key === 'no-category')
      return t('metadata.category.title') + ': ' + t('todos.notSet')
    return t('metadata.category.title') + ': ' + key
  } else if (type === 'location') {
    return key || t('todos.location') + ': ' + t('todos.notSet')
  } else if (type === 'email') {
    if (key === 'no-email') return t('todos.groupBy.noSubject')
    if (key === 'no-title') return t('todos.groupBy.noTitle')
    return key
  }
  return key
}

// Get time range based on selected range type
const getTimeRange = () => {
  const now = new Date()
  let start, end

  switch (timeRange.value) {
    case 'week':
      // Current week (Monday to Sunday)
      const weekRange = getWeekRangeForDate(now)
      start = weekRange.start
      end = weekRange.end
      break
    case 'month':
      // Current month (use actual current date, not calendar month)
      const year = now.getFullYear()
      const month = now.getMonth()
      start = new Date(year, month, 1)
      end = new Date(year, month + 1, 0, 23, 59, 59, 999)
      break
    case 'quarter':
      // Current quarter
      const quarterMonth = Math.floor(now.getMonth() / 3) * 3
      start = new Date(now.getFullYear(), quarterMonth, 1)
      end = new Date(now.getFullYear(), quarterMonth + 3, 0, 23, 59, 59, 999)
      break
    case 'custom':
      // Custom range
      if (customStartDate.value && customEndDate.value) {
        start = new Date(customStartDate.value)
        start.setHours(0, 0, 0, 0)
        end = new Date(customEndDate.value)
        end.setHours(23, 59, 59, 999)
      } else {
        // Fallback to current month (use actual current date)
        const year = now.getFullYear()
        const month = now.getMonth()
        start = new Date(year, month, 1)
        end = new Date(year, month + 1, 0, 23, 59, 59, 999)
      }
      break
    default:
      // Default to current month
      const defaultYear = currentMonth.value.getFullYear()
      const defaultMonth = currentMonth.value.getMonth()
      start = new Date(defaultYear, defaultMonth, 1)
      end = new Date(defaultYear, defaultMonth + 1, 0, 23, 59, 59, 999)
  }

  return {
    start: start.toISOString(),
    end: end.toISOString()
  }
}

// Get month range for current month (kept for calendar view)
const getMonthRange = () => {
  const year = currentMonth.value.getFullYear()
  const month = currentMonth.value.getMonth()
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0, 23, 59, 59, 999)

  return {
    start: firstDay.toISOString(),
    end: lastDay.toISOString()
  }
}

// Get week range for current week (for calendar week view)
const getWeekRange = () => {
  const weekRange = getWeekRangeForDate(currentMonth.value)
  return {
    start: weekRange.start.toISOString(),
    end: weekRange.end.toISOString()
  }
}

// Get calendar range based on view mode
const getCalendarRange = () => {
  if (calendarViewMode.value === 'week') {
    return getWeekRange()
  } else {
    return getMonthRange()
  }
}

const loadTodos = async () => {
  loading.value = true
  try {
    // Use time range for list view, calendar range for calendar view
    const range =
      viewMode.value === 'list' ? getTimeRange() : getCalendarRange()
    const params = {
      page_size: 1000,
      ordering: '-created_at',
      deadline_after: range.start,
      deadline_before: range.end
    }

    if (filters.value.is_completed !== null) {
      params.is_completed = filters.value.is_completed
    }

    if (filters.value.priority) {
      params.priority = filters.value.priority
    }

    if (filters.value.owner) {
      params.owner = filters.value.owner
    }

    if (filters.value.search) {
      params.search = filters.value.search
    }

    const response = await todosApi.getTodos(params)
    const responseData = response.data.data || response.data
    todos.value =
      responseData.list || responseData.results || responseData.data || []
  } catch (err) {
    console.error('Failed to load todos:', err)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const response = await todosApi.getTodoStats()
    stats.value = response.data.data || response.data
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

const getTodosForDate = (date) => {
  if (!date) return []
  const dateStr = formatDateForComparison(date)
  return todos.value.filter((todo) => {
    if (!todo.deadline) return false
    const todoDate = formatDateForComparison(new Date(todo.deadline))
    return todoDate === dateStr
  })
}

const formatDateForComparison = (date) => {
  if (!date) return ''
  const d = date instanceof Date ? date : new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const formatDate = (date, format) => {
  if (!date) return ''
  return formatDateUtil(
    date instanceof Date ? date.toISOString() : date,
    preferencesStore.currentTimezone,
    format,
    locale.value
  )
}

const formatSelectedDate = (date) => {
  const format = locale.value === 'zh-CN' ? 'yyyy年MM月dd日' : 'MMMM dd, yyyy'
  return formatDate(date, format)
}

const isSameDay = (date1, date2) => {
  if (!date1 || !date2) return false
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  )
}

const previousMonth = () => {
  const newDate = new Date(currentMonth.value)
  newDate.setMonth(newDate.getMonth() - 1)
  currentMonth.value = newDate
}

const nextMonth = () => {
  const newDate = new Date(currentMonth.value)
  newDate.setMonth(newDate.getMonth() + 1)
  currentMonth.value = newDate
}

const previousPeriod = () => {
  if (calendarViewMode.value === 'week') {
    // Previous week
    const newDate = new Date(currentMonth.value)
    newDate.setDate(newDate.getDate() - 7)
    currentMonth.value = newDate
  } else {
    // Previous month
    previousMonth()
  }
}

const nextPeriod = () => {
  if (calendarViewMode.value === 'week') {
    // Next week
    const newDate = new Date(currentMonth.value)
    newDate.setDate(newDate.getDate() + 7)
    currentMonth.value = newDate
  } else {
    // Next month
    nextMonth()
  }
}

const selectedDateCard = ref(null)

const selectDate = (date) => {
  if (isSameDay(date, selectedDate.value)) {
    selectedDate.value = null
  } else {
    selectedDate.value = date
    // Scroll to selected date card after DOM update
    nextTick(() => {
      const element = selectedDateCard.value?.$el || selectedDateCard.value
      if (element) {
        element.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        })
      }
    })
  }
}

let searchTimeout = null

const debounceLoadTodos = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    loadTodos()
  }, 300)
}

const clearFilters = () => {
  filters.value = {
    is_completed: null,
    priority: null,
    owner: '',
    search: ''
  }
  // Filters will be watched, so loadTodos will be called automatically
}

const removeFilter = (key) => {
  if (key === 'is_completed') {
    filters.value.is_completed = null
  } else if (key === 'priority') {
    filters.value.priority = null
  } else if (key === 'owner') {
    filters.value.owner = ''
  } else if (key === 'search') {
    filters.value.search = ''
  }
  // Filters will be watched, so loadTodos will be called automatically
}

const handleAddTodo = () => {
  // If no date selected, use today
  const targetDate = selectedDate.value || new Date()
  const d = targetDate instanceof Date ? targetDate : new Date(targetDate)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')

  // Create temporary todo for inline editing
  tempNewTodo.value = {
    id: `temp-${Date.now()}`,
    content: '',
    priority: null,
    owner: '',
    deadline: `${year}-${month}-${day}T${hours}:${minutes}`,
    location: '',
    is_completed: false,
    isNew: true // Flag to indicate this is a new todo
  }

  // Auto-select date if not selected
  if (!selectedDate.value) {
    selectedDate.value = targetDate
  }
}

// Handle todo click in calendar view - select date and scroll to detail area
const handleCalendarTodoClick = (todo, date) => {
  // Show loading effect
  calendarClickLoading.value = true

  // Select the date to show todos for that date
  selectedDate.value = date

  // Scroll to detail area after DOM update
  nextTick(() => {
    const element = selectedDateCard.value?.$el || selectedDateCard.value
    if (element) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      })

      // Hide loading after scroll animation completes (smooth scroll takes ~500ms)
      setTimeout(() => {
        calendarClickLoading.value = false
      }, 600)
    } else {
      // If element not found, hide loading immediately
      calendarClickLoading.value = false
    }
  })
}

const handleEditTodo = (todo) => {
  // Only show editor modal in list view, not in calendar view
  if (viewMode.value === 'calendar') {
    // In calendar view, select the date and scroll to detail area
    if (todo.deadline) {
      const todoDate = new Date(todo.deadline)
      todoDate.setHours(0, 0, 0, 0)
      handleCalendarTodoClick(todo, todoDate)
    }
  } else {
    // In list view, show editor modal
    editingTodo.value = todo
    showTodoEditor.value = true
  }
}

const closeTodoEditor = () => {
  showTodoEditor.value = false
  editingTodo.value = null
}

const handleSaveTodoInline = async (todoId, todoData) => {
  // Ensure todoId is a string for comparison
  const todoIdStr = String(todoId)
  todoLoading.value[todoIdStr] = true
  errorMessage.value = ''
  successMessage.value = ''

  // Check if this is a new todo (temp todo)
  const isNewTodo =
    todoIdStr.startsWith('temp-') ||
    (tempNewTodo.value && String(tempNewTodo.value.id) === todoIdStr)

  try {
    if (isNewTodo) {
      // Create new todo
      await todosApi.createTodo(todoData)
      successMessage.value =
        t('todos.createSuccess') || 'TODO created successfully'
      // Remove temp todo
      tempNewTodo.value = null
      await Promise.all([loadTodos(), loadStats()])
    } else {
      // Update existing todo
      await todosApi.updateTodo(todoIdStr, todoData)
      successMessage.value =
        t('todos.updateSuccess') || 'TODO updated successfully'
      await Promise.all([loadTodos(), loadStats()])
    }

    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (err) {
    console.error('Failed to save todo:', err)
    errorMessage.value = extractErrorMessage(
      err,
      t('common.error') + ': ' + t('todos.save')
    )
    throw err // Re-throw to let TodoItem handle the error
  } finally {
    todoLoading.value[todoIdStr] = false
  }
}

const handleCancelNewTodo = () => {
  tempNewTodo.value = null
}

const handleSaveTodo = async (todoData) => {
  savingTodo.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (editingTodo.value && editingTodo.value.id) {
      await todosApi.updateTodo(editingTodo.value.id, todoData)
      successMessage.value =
        t('todos.updateSuccess') || 'TODO updated successfully'
    } else {
      await todosApi.createTodo(todoData)
      successMessage.value =
        t('todos.createSuccess') || 'TODO created successfully'
    }
    await Promise.all([loadTodos(), loadStats()])
    closeTodoEditor()

    // Auto-hide success message after 3 seconds
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (err) {
    console.error('Failed to save todo:', err)
    errorMessage.value = extractErrorMessage(
      err,
      t('common.error') + ': ' + t('todos.save')
    )
  } finally {
    savingTodo.value = false
  }
}

const handleToggleTodo = async (todoId) => {
  todoLoading.value[todoId] = true
  errorMessage.value = ''
  try {
    const todo = todos.value.find((t) => t.id === todoId)
    if (!todo) return

    await todosApi.updateTodo(todoId, {
      is_completed: !todo.is_completed
    })
    await Promise.all([loadTodos(), loadStats()])
  } catch (err) {
    console.error('Failed to toggle todo:', err)
    errorMessage.value = extractErrorMessage(
      err,
      t('common.error') + ': ' + t('todos.markCompleted')
    )
  } finally {
    todoLoading.value[todoId] = false
  }
}

const handleDeleteTodo = async (todoId) => {
  todoLoading.value[todoId] = true
  errorMessage.value = ''
  try {
    await todosApi.deleteTodo(todoId)
    await Promise.all([loadTodos(), loadStats()])
    if (selectedDate.value) {
      const dateTodos = getTodosForDate(selectedDate.value)
      if (dateTodos.length === 0) {
        selectedDate.value = null
      }
    }
    successMessage.value =
      t('todos.deleteSuccess') || 'TODO deleted successfully'
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (err) {
    console.error('Failed to delete todo:', err)
    errorMessage.value = extractErrorMessage(
      err,
      t('common.error') + ': ' + t('todos.delete')
    )
  } finally {
    todoLoading.value[todoId] = false
  }
}

// Select time range
const selectTimeRange = (range) => {
  timeRange.value = range
  if (range === 'custom') {
    // Initialize custom dates if not set
    if (!customStartDate.value) {
      const today = new Date()
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
      customStartDate.value = firstDay.toISOString().split('T')[0]
    }
    if (!customEndDate.value) {
      const today = new Date()
      const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0)
      customEndDate.value = lastDay.toISOString().split('T')[0]
    }
  }
  loadTodos()
}

// Handle custom date change
const handleCustomDateChange = () => {
  if (timeRange.value === 'custom') {
    // Validate custom date range (max 1 month)
    if (customStartDate.value && customEndDate.value) {
      const start = new Date(customStartDate.value)
      const end = new Date(customEndDate.value)
      const diffTime = Math.abs(end - start)
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

      // Limit to 31 days (1 month)
      if (diffDays > 31) {
        // Adjust end date to be 31 days from start
        const maxEnd = new Date(start)
        maxEnd.setDate(maxEnd.getDate() + 31)
        const year = maxEnd.getFullYear()
        const month = String(maxEnd.getMonth() + 1).padStart(2, '0')
        const day = String(maxEnd.getDate()).padStart(2, '0')
        customEndDate.value = `${year}-${month}-${day}`
      }
    }
    selectTimeRange('custom')
  }
}

// Handle calendar view mode change
const handleCalendarViewModeChange = () => {
  // When switching to week view, show the week containing today
  if (calendarViewMode.value === 'week') {
    const now = new Date()
    const monday = getMondayOfWeek(now)
    // Set to Monday of the week (not the 1st of the month)
    currentMonth.value = new Date(
      monday.getFullYear(),
      monday.getMonth(),
      monday.getDate()
    )
  } else {
    // Month view: show current month
    const now = new Date()
    currentMonth.value = new Date(now.getFullYear(), now.getMonth(), 1)
  }
}

onMounted(() => {
  loadTodos()
  loadStats()
})

watch(
  () => currentMonth.value,
  () => {
    loadTodos()
  }
)

watch(
  () => viewMode.value,
  () => {
    loadTodos()
  }
)

watch(
  () => timeRange.value,
  () => {
    loadTodos()
  }
)

watch(
  () => calendarViewMode.value,
  () => {
    if (viewMode.value === 'calendar') {
      loadTodos()
    }
  }
)

// Watch filters for real-time filtering
watch(
  () => filters.value,
  () => {
    debounceLoadTodos()
  },
  { deep: true }
)
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

/* Fade transition for loading overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
