<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('taskManagement.stats.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('taskManagement.stats.subtitle') }}
        </p>
      </div>

      <section
        class="w-full bg-white rounded-2xl border border-gray-200 shadow-sm p-4 sm:p-5 flex flex-wrap items-end justify-between gap-6 mb-6"
        aria-label="Filters"
      >
        <div class="flex flex-wrap items-end gap-6 flex-1 min-w-0">
          <div class="flex flex-col gap-1.5">
            <label
              class="text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-1"
            >
              {{ t('taskManagement.stats.userScope') }}
            </label>
            <select
              v-model="userScope"
              class="rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 min-w-[140px] hover:border-gray-300 transition-colors"
              @change="fetchStats"
            >
              <option value="">
                {{ t('taskManagement.stats.allUsers') }}
              </option>
              <option
                v-for="u in userOptions"
                :key="u.user_id"
                :value="String(u.user_id)"
              >
                {{ u.display }}
              </option>
            </select>
          </div>
          <div class="flex flex-col gap-1.5">
            <label
              class="text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-1"
            >
              {{ t('taskManagement.stats.granularity') }}
            </label>
            <div class="flex rounded-lg bg-gray-100 p-1">
              <button
                v-for="opt in granularityOptions"
                :key="opt.value"
                type="button"
                :class="[
                  'px-4 py-1.5 text-xs font-semibold rounded-md transition-colors',
                  granularity === opt.value
                    ? 'bg-white text-primary-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                ]"
                @click="selectGranularity(opt.value)"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>
          <div class="flex flex-col gap-1.5">
            <label
              class="text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-1"
            >
              {{
                granularity === 'day'
                  ? t('taskManagement.stats.selectDay')
                  : granularity === 'month'
                    ? t('taskManagement.stats.selectYearMonth')
                    : t('taskManagement.stats.selectYear')
              }}
            </label>
            <div v-if="granularity === 'day'" class="flex items-center gap-2">
              <input
                v-model="selectedDay"
                type="date"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onDayChange"
              />
            </div>
            <div
              v-else-if="granularity === 'month'"
              class="flex items-center gap-2"
            >
              <select
                v-model="selectedYear"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onMonthYearChange"
              >
                <option v-for="y in yearOptions" :key="y" :value="y">
                  {{ y }}
                </option>
              </select>
              <select
                v-model="selectedMonth"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onMonthYearChange"
              >
                <option v-for="m in 12" :key="m" :value="m">
                  {{ String(m).padStart(2, '0') }}
                </option>
              </select>
            </div>
            <div v-else class="flex items-center gap-2">
              <select
                v-model="selectedYear"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onYearChange"
              >
                <option v-for="y in yearOptions" :key="y" :value="y">
                  {{ y }}
                </option>
              </select>
            </div>
          </div>
        </div>
        <div class="flex items-end shrink-0">
          <BaseButton
            variant="outline"
            size="sm"
            :loading="loading"
            class="flex items-center gap-2 px-4 py-2 bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200 rounded-lg text-sm font-medium"
            @click="fetchStats"
          >
            <svg
              v-if="!loading"
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
            {{ t('taskManagement.stats.refreshData') }}
          </BaseButton>
        </div>
      </section>

      <div class="w-full">
        <BaseLoading v-if="loading && !stats" />

        <div
          v-if="!loading && !stats"
          class="py-16 text-center rounded-2xl border border-gray-200 bg-white shadow-sm"
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
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p class="text-sm font-medium text-gray-600">
            {{ t('taskManagement.stats.noData') }}
          </p>
        </div>

        <template v-else-if="stats">
          <div
            class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
          >
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-gray-100 text-gray-600 shrink-0"
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
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-gray-600">{{
                  t('taskManagement.stats.total')
                }}</span>
              </div>
              <div class="text-2xl font-semibold text-gray-900">
                {{ formatNum(stats.total) }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-green-100 text-green-600 shrink-0"
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
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-green-600">{{
                  t('taskManagement.stats.success')
                }}</span>
              </div>
              <div class="text-2xl font-semibold text-green-600">
                {{ formatNum(stats.success) }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-red-100 text-red-600 shrink-0"
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
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-red-600">{{
                  t('taskManagement.stats.failure')
                }}</span>
              </div>
              <div class="text-2xl font-semibold text-red-600">
                {{ formatNum(stats.failure) }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-amber-100 text-amber-600 shrink-0"
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
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-amber-600">{{
                  t('taskManagement.stats.pending')
                }}</span>
              </div>
              <div class="text-2xl font-semibold text-amber-600">
                {{ formatNum(stats.pending) }}
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-blue-100 text-blue-600 shrink-0"
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
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-blue-600">{{
                  t('taskManagement.stats.started')
                }}</span>
              </div>
              <div class="text-2xl font-semibold text-blue-600">
                {{ formatNum(stats.started) }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-purple-100 text-purple-600 shrink-0"
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
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-purple-600">{{
                  t('taskManagement.stats.retry')
                }}</span>
              </div>
              <div class="text-2xl font-semibold text-purple-600">
                {{ formatNum(stats.retry) }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-slate-100 text-slate-600 shrink-0"
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
                      d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-slate-600">{{
                  t('taskManagement.stats.revoked')
                }}</span>
              </div>
              <div class="text-2xl font-semibold text-slate-600">
                {{ formatNum(stats.revoked) }}
              </div>
            </div>
          </div>

          <div
            class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 flex flex-col min-h-[360px] mb-6"
          >
            <h3 class="text-base font-semibold text-gray-900 mb-1">
              {{ t('taskManagement.stats.seriesTitle') }}
            </h3>
            <p class="text-sm text-gray-500 mb-4">
              {{ t('taskManagement.stats.seriesSubtitle') }}
            </p>
            <div class="flex-1 min-h-0 flex flex-col">
              <div
                v-if="seriesChartData && seriesChartData.labels.length > 0"
                class="flex-1 min-h-[280px]"
              >
                <Bar :data="seriesChartData" :options="seriesChartOptions" />
              </div>
              <div
                v-else
                class="flex-1 min-h-[280px] flex items-center justify-center text-gray-400 text-sm"
              >
                {{ t('taskManagement.stats.noData') }}
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6 items-stretch">
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 flex flex-col min-h-[320px]"
            >
              <h3 class="text-base font-semibold text-gray-900 mb-1">
                {{ t('taskManagement.stats.chartStatusDistribution') }}
              </h3>
              <p class="text-sm text-gray-500 mb-3">
                {{ t('taskManagement.stats.chartStatusSubtitle') }}
              </p>
              <div
                v-if="statusChartData && statusChartData.labels.length > 0"
                class="flex-1 min-h-[260px]"
              >
                <Doughnut
                  :data="statusChartData"
                  :options="statusChartOptions"
                />
              </div>
              <div
                v-else
                class="flex-1 min-h-[260px] flex items-center justify-center text-gray-500 text-sm rounded-lg border border-gray-200 bg-gray-50"
              >
                {{ t('taskManagement.stats.noData') }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 flex flex-col min-h-[320px]"
            >
              <h3 class="text-base font-semibold text-gray-900 mb-1">
                {{ t('taskManagement.stats.chartByModule') }}
              </h3>
              <p class="text-sm text-gray-500 mb-3">
                {{ t('taskManagement.stats.chartByModuleSubtitle') }}
              </p>
              <div
                v-if="byModuleChartData && byModuleChartData.labels.length > 0"
                class="flex-1 min-h-[260px]"
              >
                <Bar
                  :data="byModuleChartData"
                  :options="byModuleChartOptions"
                />
              </div>
              <div
                v-else
                class="flex-1 min-h-[260px] flex items-center justify-center text-gray-500 text-sm rounded-lg border border-gray-200 bg-gray-50"
              >
                {{ t('taskManagement.stats.noData') }}
              </div>
            </div>
          </div>

          <div
            v-if="byTaskNameChartData && byTaskNameChartData.labels.length > 0"
            class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 flex flex-col min-h-[320px] mb-6"
          >
            <h3 class="text-base font-semibold text-gray-900 mb-1">
              {{ t('taskManagement.stats.chartByTaskName') }}
            </h3>
            <p class="text-sm text-gray-500 mb-4">
              {{ t('taskManagement.stats.chartByTaskNameSubtitle') }}
            </p>
            <div class="flex-1 min-h-[280px]">
              <Bar
                :data="byTaskNameChartData"
                :options="byTaskNameChartOptions"
              />
            </div>
          </div>

          <div
            v-if="byModuleKeys.length > 0"
            class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 mb-6"
          >
            <h3 class="text-base font-semibold text-gray-900 mb-3">
              {{ t('taskManagement.stats.byModule') }}
            </h3>
            <div
              class="overflow-x-auto relative rounded-lg border border-gray-200"
            >
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
                  <tr>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.moduleColumn') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.total') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.pending') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.started') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.success') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.failure') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                  <tr
                    v-for="key in byModuleKeys"
                    :key="key"
                    class="transition-colors duration-150 hover:bg-gray-50"
                  >
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900"
                    >
                      {{ key || '-' }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_module[key]?.total ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_module[key]?.pending ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_module[key]?.started ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_module[key]?.success ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_module[key]?.failure ?? 0 }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div
            v-if="byTaskNameKeys.length > 0"
            class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
          >
            <h3 class="text-base font-semibold text-gray-900 mb-3">
              {{ t('taskManagement.stats.byTaskName') }}
            </h3>
            <div
              class="overflow-x-auto relative rounded-lg border border-gray-200"
            >
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
                  <tr>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.taskColumn') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.total') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.pending') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.started') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.success') }}
                    </th>
                    <th
                      class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('taskManagement.stats.failure') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                  <tr
                    v-for="key in byTaskNameKeys"
                    :key="key"
                    class="transition-colors duration-150 hover:bg-gray-50"
                  >
                    <td
                      class="px-4 py-3 text-sm font-medium text-gray-900 break-all"
                    >
                      {{ key || '-' }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_task_name[key]?.total ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_task_name[key]?.pending ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_task_name[key]?.started ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_task_name[key]?.success ?? 0 }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600"
                    >
                      {{ stats.by_task_name[key]?.failure ?? 0 }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { extractResponseData, extractErrorMessage } from '@/utils/api'
import {
  taskManagementApi,
  notificationsAdminApi,
  llmAdminApi
} from '@/admin/api'
import { Doughnut, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const { t } = useI18n()
const { showError } = useToast()

function formatNum(value) {
  if (value == null || value === '') return '0'
  const n = Number(value)
  return Number.isFinite(n) ? n.toLocaleString() : '0'
}

const loading = ref(false)
const stats = ref(null)
const granularity = ref('day')
const userScope = ref('')
const userOptions = ref([])
const startDate = ref('')
const endDate = ref('')
const selectedDay = ref('')
const selectedYear = ref(new Date().getFullYear())
const selectedMonth = ref(new Date().getMonth() + 1)

const currentYear = new Date().getFullYear()
const yearOptions = computed(() => {
  const arr = []
  for (let y = currentYear; y >= currentYear - 10; y--) arr.push(y)
  return arr
})

const granularityOptions = computed(() => [
  { value: 'day', label: t('taskManagement.stats.granularityDay') },
  { value: 'month', label: t('taskManagement.stats.granularityMonth') },
  { value: 'year', label: t('taskManagement.stats.granularityYear') }
])

function formatDate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function setDefaultDates() {
  const now = new Date()
  const g = granularity.value
  if (g === 'day') {
    selectedDay.value = formatDate(now)
    startDate.value = selectedDay.value
    endDate.value = selectedDay.value
  } else if (g === 'month') {
    selectedYear.value = now.getFullYear()
    selectedMonth.value = now.getMonth() + 1
    startDate.value = `${selectedYear.value}-${String(selectedMonth.value).padStart(2, '0')}-01`
    const last = new Date(selectedYear.value, selectedMonth.value, 0)
    endDate.value = formatDate(last)
  } else {
    selectedYear.value = now.getFullYear()
    startDate.value = `${selectedYear.value}-01-01`
    endDate.value = `${selectedYear.value}-12-31`
  }
}

function onDayChange() {
  if (!selectedDay.value) return
  startDate.value = selectedDay.value
  endDate.value = selectedDay.value
  fetchStats()
}

function onMonthYearChange() {
  const y = selectedYear.value
  const m = selectedMonth.value
  if (!y || !m) return
  startDate.value = `${y}-${String(m).padStart(2, '0')}-01`
  const last = new Date(y, m, 0)
  endDate.value = formatDate(last)
  fetchStats()
}

function onYearChange() {
  const y = selectedYear.value
  if (!y) return
  startDate.value = `${y}-01-01`
  endDate.value = `${y}-12-31`
  fetchStats()
}

function selectGranularity(g) {
  granularity.value = g
  setDefaultDates()
  fetchStats()
}

const seriesItems = computed(() => {
  const list = stats.value?.series
  return Array.isArray(list) ? list : []
})

const seriesChartData = computed(() => {
  const list = seriesItems.value
  if (list.length === 0) return null
  return {
    labels: list.map((r) => r.bucket || '-'),
    datasets: [
      {
        label: t('taskManagement.stats.total'),
        data: list.map((r) => r.count ?? 0),
        backgroundColor: 'rgba(99, 102, 241, 0.7)',
        borderColor: 'rgb(99, 102, 241)',
        borderWidth: 1
      }
    ]
  }
})

const seriesChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      align: 'end',
      labels: { usePointStyle: true, padding: 12 }
    },
    tooltip: {
      callbacks: {
        label(ctx) {
          return `${t('taskManagement.stats.total')}: ${ctx.raw}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        maxTicksLimit: 12,
        maxRotation: 45,
        minRotation: 0,
        font: { size: 11 }
      }
    },
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(0,0,0,0.06)' },
      ticks: { precision: 0 }
    }
  }
}))

const byModuleKeys = computed(() => {
  if (!stats.value?.by_module) return []
  return Object.keys(stats.value.by_module)
})

const byTaskNameKeys = computed(() => {
  if (!stats.value?.by_task_name) return []
  return Object.keys(stats.value.by_task_name)
})

const statusChartData = computed(() => {
  if (!stats.value) return null
  const s = stats.value
  const statusKeys = [
    'pending',
    'started',
    'success',
    'failure',
    'retry',
    'revoked'
  ]
  const labels = statusKeys.map((k) => t(`taskManagement.stats.${k}`))
  const data = statusKeys.map((k) => s[k] ?? 0)
  if (data.every((v) => v === 0)) return null
  const colors = [
    '#f59e0b',
    '#3b82f6',
    '#10b981',
    '#ef4444',
    '#8b5cf6',
    '#6b7280'
  ]
  return {
    labels,
    datasets: [
      {
        data,
        backgroundColor: colors,
        borderColor: '#fff',
        borderWidth: 2
      }
    ]
  }
})

const statusChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right',
      labels: { usePointStyle: true, padding: 10, font: { size: 11 } }
    },
    tooltip: {
      callbacks: {
        label(ctx) {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0)
          const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0
          return `${ctx.label}: ${ctx.raw} (${pct}%)`
        }
      }
    }
  }
}))

const byModuleChartData = computed(() => {
  if (!stats.value?.by_module || byModuleKeys.value.length === 0) return null
  const keys = byModuleKeys.value
  return {
    labels: keys.map((k) => k || '-'),
    datasets: [
      {
        label: t('taskManagement.stats.total'),
        data: keys.map((k) => stats.value.by_module[k]?.total ?? 0),
        backgroundColor: 'rgba(99, 102, 241, 0.7)',
        borderColor: 'rgb(99, 102, 241)',
        borderWidth: 1
      }
    ]
  }
})

const byModuleChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${t('taskManagement.stats.total')}: ${ctx.raw}`
      }
    }
  },
  scales: {
    x: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.06)' } },
    y: { grid: { display: false }, ticks: { maxRotation: 0 } }
  }
}))

const TOP_TASK_NAMES = 12
const byTaskNameChartData = computed(() => {
  if (!stats.value?.by_task_name || byTaskNameKeys.value.length === 0)
    return null
  const keys = byTaskNameKeys.value
    .map((k) => ({ k, total: stats.value.by_task_name[k]?.total ?? 0 }))
    .sort((a, b) => b.total - a.total)
    .slice(0, TOP_TASK_NAMES)
    .map((x) => x.k)
  if (keys.length === 0) return null
  return {
    labels: keys.map((k) =>
      k && k.length > 20 ? k.slice(0, 18) + '…' : k || '-'
    ),
    datasets: [
      {
        label: t('taskManagement.stats.total'),
        data: keys.map((k) => stats.value.by_task_name[k]?.total ?? 0),
        backgroundColor: 'rgba(16, 185, 129, 0.7)',
        borderColor: 'rgb(16, 185, 129)',
        borderWidth: 1
      }
    ]
  }
})

const byTaskNameChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${t('taskManagement.stats.total')}: ${ctx.raw}`
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxRotation: 45, minRotation: 0, font: { size: 11 } }
    },
    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.06)' } }
  }
}))

async function fetchStats() {
  if (!startDate.value || !endDate.value) {
    setDefaultDates()
  }
  loading.value = true
  try {
    const params = { granularity: granularity.value }
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value
    if (userScope.value) params.created_by = userScope.value
    const res = await taskManagementApi.getStats(params)
    stats.value = extractResponseData(res)
  } catch (e) {
    showError(extractErrorMessage(e, t('common.error')))
    stats.value = null
  } finally {
    loading.value = false
  }
}

async function fetchUserOptions() {
  try {
    const list = await notificationsAdminApi.getUsers()
    if (Array.isArray(list) && list.length > 0) {
      userOptions.value = list.map((u) => ({
        user_id: u.user_id ?? u.id,
        display: (
          u.display ??
          u.username ??
          (u.user_id != null ? `#${u.user_id}` : u.id != null ? `#${u.id}` : '')
        ).toString()
      }))
      return
    }
  } catch {
    /* fallback to admin users list */
  }
  try {
    const data = await llmAdminApi.getUsers({ page_size: 200 })
    const raw = Array.isArray(data)
      ? data
      : Array.isArray(data?.results)
        ? data.results
        : []
    userOptions.value = raw.map((u) => ({
      user_id: u.id ?? u.user_id,
      display: (
        u.username ??
        u.display ??
        u.email ??
        (u.id != null ? `#${u.id}` : '')
      ).toString()
    }))
  } catch {
    userOptions.value = []
  }
}

onMounted(() => {
  fetchUserOptions()
  setDefaultDates()
  fetchStats()
})
</script>
