<script setup lang="tsx">
/**
 * 研报中心页：券商研报采集概览（统计卡片 + 评级分布 + 热门 TOP）+ 研报列表筛选
 */
import { computed, h, onMounted, reactive, ref, watch } from 'vue';
import {
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NGrid,
  NGridItem,
  NInput,
  NSelect,
  NSpace,
  NStatistic,
  NTabPane,
  NTabs,
  NTag,
  NText
} from 'naive-ui';
import type { DataTableColumns, PaginationProps } from 'naive-ui';
import {
  fetchGetResearchReports,
  fetchGetResearchStats,
  fetchGetResearchStockStats,
  fetchSyncResearchReports
} from '@/service/api';
import { useAuth } from '@/hooks/business/auth';
import { $t } from '@/locales';

defineOptions({ name: 'AiResearchReport' });

const { hasAuth } = useAuth();
const canSync = hasAuth('research:sync');

const loading = ref(false);
const syncing = ref(false);
const records = ref<Api.Research.ResearchReportItem[]>([]);
const stats = ref<Api.Research.ResearchStats | null>(null);

const query = reactive({
  page: 1,
  pageSize: 20,
  stockCode: '',
  keyword: '',
  orgName: '',
  rating: null as string | null,
  dateRange: null as [number, number] | null
});

// ==================== Tab 切换 ====================
const TAB_STATS = 'stats';
const TAB_LIST = 'list';
const activeTab = ref(TAB_STATS);

/** 跳到列表 Tab 并按条件筛选（热门标签/统计行「查看研报」联动） */
function gotoListWithFilter(code?: string, org?: string) {
  if (code !== undefined) query.stockCode = code;
  if (org !== undefined) query.orgName = org;
  activeTab.value = TAB_LIST;
  onSearch();
}

// ==================== 研报统计（按股票分组） ====================
const RANGE_OPTIONS = [
  { label: $t('page.research.range7d'), value: 7 },
  { label: $t('page.research.range1m'), value: 30 },
  { label: $t('page.research.range3m'), value: 90 },
  { label: $t('page.research.range6m'), value: 180 },
  { label: $t('page.research.range1y'), value: 365 }
] as const;

const statDays = ref(30);
const statLoading = ref(false);
const stockStats = ref<Api.Research.ResearchStockStatItem[]>([]);

const statColumns: DataTableColumns<Api.Research.ResearchStockStatItem> = [
  {
    title: $t('page.research.stockCol'),
    key: 'stock_code',
    width: 130,
    render: row => h('span', { class: 'font-500' }, `${row.stock_code} ${row.stock_name ?? ''}`)
  },
  {
    title: $t('page.research.statReportCount'),
    key: 'report_count',
    width: 100,
    sorter: 'default',
    render: row => h('span', { class: 'text-primary font-600' }, String(row.report_count))
  },
  {
    title: $t('page.research.statPositiveCount'),
    key: 'positive_count',
    width: 110,
    sorter: 'default',
    render: row =>
      h('span', null, `${row.positive_count}（${reportCount(row) > 0 ? Math.round((row.positive_count / reportCount(row)) * 100) : 0}%）`)
  },
  {
    title: $t('page.research.statOrgCount'),
    key: 'org_count',
    width: 100,
    sorter: 'default'
  },
  {
    title: $t('page.research.statLatestDate'),
    key: 'latest_date',
    width: 120,
    sorter: 'default',
    render: row => row.latest_date ?? '-'
  },
  {
    title: $t('common.action'),
    key: 'actions',
    width: 80,
    align: 'center',
    render: row =>
      h(
        NButton,
        {
          size: 'tiny',
          tertiary: true,
          onClick: () => {
            query.stockCode = row.stock_code;
            gotoListWithFilter(row.stock_code);
          }
        },
        { default: () => $t('page.research.viewReports') }
      )
  }
];

function reportCount(row: Api.Research.ResearchStockStatItem) {
  return row.report_count || 0;
}

async function loadStockStats() {
  statLoading.value = true;
  try {
    const { data, error } = await fetchGetResearchStockStats(statDays.value);
    if (!error) stockStats.value = data ?? [];
  } finally {
    statLoading.value = false;
  }
}

const pagination = reactive<PaginationProps>({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  onChange: (page: number) => {
    pagination.page = page;
    query.page = page;
    loadData();
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize;
    query.pageSize = pageSize;
    query.page = 1;
    pagination.page = 1;
    loadData();
  }
});

const ratingOptions = computed(() =>
  (stats.value?.rating_distribution ?? []).map(r => ({ label: `${r.rating} (${r.count})`, value: r.rating }))
);

const ratingTagType = (rating: string | null) => {
  if (!rating) return 'default' as const;
  if (rating.includes('买入') || rating.includes('强烈')) return 'error' as const;
  if (rating.includes('增持') || rating.includes('推荐')) return 'warning' as const;
  if (rating.includes('中性') || rating.includes('持有')) return 'info' as const;
  return 'default' as const;
};

function fmtForecast(forecast: Api.Research.ResearchReportItem['forecast']) {
  if (!forecast) return '-';
  return Object.entries(forecast)
    .map(([year, v]) => `${year}: EPS ${v.eps ?? '-'} / PE ${v.pe ?? '-'}`)
    .join('；');
}

const columns: DataTableColumns<Api.Research.ResearchReportItem> = [
  {
    title: $t('page.research.stockCol'),
    key: 'stock_code',
    width: 110,
    render: row =>
      h('span', { class: 'font-500' }, `${row.stock_code} ${row.stock_name ?? ''}`)
  },
  {
    title: $t('page.research.titleCol'),
    key: 'title',
    ellipsis: { tooltip: true },
    render: row =>
      h(
        'a',
        {
          href: row.url,
          target: '_blank',
          rel: 'noopener',
          class: 'text-primary hover:underline'
        },
        row.title
      )
  },
  {
    title: $t('page.research.orgCol'),
    key: 'org_name',
    width: 130,
    ellipsis: { tooltip: true }
  },
  {
    title: $t('page.research.ratingCol'),
    key: 'rating',
    width: 90,
    render: row => h(NTag, { size: 'small', type: ratingTagType(row.rating), bordered: false }, { default: () => row.rating ?? '-' })
  },
  {
    title: $t('page.research.industryCol'),
    key: 'industry',
    width: 110,
    ellipsis: { tooltip: true },
    render: row => row.industry ?? '-'
  },
  {
    title: $t('page.research.forecastCol'),
    key: 'forecast',
    width: 260,
    ellipsis: { tooltip: true },
    render: row => fmtForecast(row.forecast)
  },
  {
    title: $t('page.research.dateCol'),
    key: 'published_date',
    width: 110,
    render: row => row.published_date ?? '-'
  }
];

async function loadData() {
  loading.value = true;
  try {
    const { data, error } = await fetchGetResearchReports({
      page: query.page,
      pageSize: query.pageSize,
      stockCode: query.stockCode.trim() || undefined,
      keyword: query.keyword.trim() || undefined,
      orgName: query.orgName.trim() || undefined,
      rating: query.rating ?? undefined,
      startDate: query.dateRange ? new Date(query.dateRange[0]).toISOString().slice(0, 10) : undefined,
      endDate: query.dateRange ? new Date(query.dateRange[1]).toISOString().slice(0, 10) : undefined
    });
    if (!error && data) {
      records.value = data.records;
      pagination.itemCount = data.total;
    }
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  const { data, error } = await fetchGetResearchStats(30);
  if (!error) stats.value = data ?? null;
}

async function onSearch() {
  query.page = 1;
  pagination.page = 1;
  await loadData();
}

async function onSync() {
  syncing.value = true;
  try {
    const codes = query.stockCode.trim() ? [query.stockCode.trim()] : [];
    const { data, error } = await fetchSyncResearchReports(codes);
    if (!error) {
      window.$message?.success(
        $t('page.research.syncDone', { saved: data?.saved ?? 0, failed: data?.failed ?? 0 })
      );
      await Promise.all([loadStats(), onSearch()]);
    }
  } finally {
    syncing.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadStats(), loadStockStats(), loadData()]);
});

watch(statDays, () => loadStockStats());
</script>

<template>
  <div class="min-h-500px h-full flex flex-col gap-12px overflow-hidden">
    <!-- 顶部标题 + 同步 -->
    <NCard :bordered="false" size="small" class="card-wrapper">
      <template #header>
        <div class="flex-y-center gap-8px">
          <span class="text-16px font-500">{{ $t('page.research.title') }}</span>
          <NText depth="3" class="text-12px">{{ $t('page.research.subtitle') }}</NText>
        </div>
      </template>
      <template #header-extra>
        <NButton v-if="canSync" size="small" tertiary :loading="syncing" @click="onSync">
          <template #icon><icon-mdi-refresh class="text-icon" /></template>
          {{ $t('page.research.syncBtn') }}
        </NButton>
      </template>

      <NTabs v-model:value="activeTab" type="line" size="small" animated>
        <!-- ==================== 统计 Tab ==================== -->
        <NTabPane :name="TAB_STATS" :tab="$t('page.research.tabStats')">
          <div class="flex flex-col gap-12px">
            <!-- 概览统计卡片 -->
            <NGrid :x-gap="12" :y-gap="12" :cols="2" s:cols="4" responsive="screen">
              <NGridItem>
                <NStatistic :label="$t('page.research.statTotal')" :value="stats?.total ?? 0">
                  <template #suffix>
                    <NText depth="3" class="text-12px">{{ $t('page.research.statTotalSuffix') }}</NText>
                  </template>
                </NStatistic>
              </NGridItem>
              <NGridItem>
                <NStatistic :label="$t('page.research.statStocks')" :value="stats?.stock_count ?? 0" />
              </NGridItem>
              <NGridItem>
                <NStatistic :label="$t('page.research.statOrgs')" :value="stats?.org_count ?? 0" />
              </NGridItem>
              <NGridItem>
                <div class="flex flex-wrap gap-6px pt-8px">
                  <NTag
                    v-for="r in stats?.rating_distribution ?? []"
                    :key="r.rating"
                    size="small"
                    :type="ratingTagType(r.rating)"
                    :bordered="false"
                  >
                    {{ r.rating }} {{ r.count }}
                  </NTag>
                </div>
              </NGridItem>
            </NGrid>

            <!-- 热门 TOP -->
            <div class="flex flex-wrap gap-24px">
              <div class="flex-1 min-w-300px">
                <NText depth="3" class="text-12px">{{ $t('page.research.hotStocks') }}</NText>
                <div class="mt-4px flex flex-wrap gap-6px">
                  <NTag
                    v-for="(s, i) in stats?.hot_stocks ?? []"
                    :key="s.name ?? i"
                    size="small"
                    class="cursor-pointer"
                    @click="gotoListWithFilter(s.name ?? '')"
                  >
                    {{ s.name }} ({{ s.count }})
                  </NTag>
                </div>
              </div>
              <div class="flex-1 min-w-300px">
                <NText depth="3" class="text-12px">{{ $t('page.research.hotOrgs') }}</NText>
                <div class="mt-4px flex flex-wrap gap-6px">
                  <NTag
                    v-for="(o, i) in stats?.hot_orgs ?? []"
                    :key="o.name ?? i"
                    size="small"
                    class="cursor-pointer"
                    @click="gotoListWithFilter(undefined, o.name ?? '')"
                  >
                    {{ o.name }} ({{ o.count }})
                  </NTag>
                </div>
              </div>
            </div>

            <!-- 按股票分组统计 -->
            <NCard :bordered="true" size="small">
              <template #header>
                <div class="flex-y-center gap-8px">
                  <span class="text-14px font-500">{{ $t('page.research.statTitle') }}</span>
                  <NText depth="3" class="text-12px">{{ $t('page.research.statSubtitle') }}</NText>
                </div>
              </template>
              <template #header-extra>
                <NSpace :size="4" align="center">
                  <NButton
                    v-for="opt in RANGE_OPTIONS"
                    :key="opt.value"
                    size="tiny"
                    :type="statDays === opt.value ? 'primary' : 'default'"
                    secondary
                    @click="statDays = opt.value"
                  >
                    {{ opt.label }}
                  </NButton>
                </NSpace>
              </template>
              <NDataTable
                :loading="statLoading"
                :columns="statColumns"
                :data="stockStats"
                size="small"
                :max-height="360"
                :row-key="(row: Api.Research.ResearchStockStatItem) => row.stock_code"
              />
            </NCard>
          </div>
        </NTabPane>

        <!-- ==================== 列表 Tab ==================== -->
        <NTabPane :name="TAB_LIST" :tab="$t('page.research.tabList')">
          <NSpace class="mb-12px" :size="12" align="center" :wrap="true">
            <NInput
              v-model:value="query.stockCode"
              size="small"
              clearable
              :placeholder="$t('page.research.stockPlaceholder')"
              style="width: 160px"
              @keyup.enter="onSearch"
            />
            <NInput
              v-model:value="query.keyword"
              size="small"
              clearable
              :placeholder="$t('page.research.keywordPlaceholder')"
              style="width: 200px"
              @keyup.enter="onSearch"
            />
            <NInput
              v-model:value="query.orgName"
              size="small"
              clearable
              :placeholder="$t('page.research.orgPlaceholder')"
              style="width: 160px"
              @keyup.enter="onSearch"
            />
            <NSelect
              v-model:value="query.rating"
              size="small"
              clearable
              :placeholder="$t('page.research.ratingPlaceholder')"
              :options="ratingOptions"
              style="width: 140px"
            />
            <NDatePicker
              v-model:value="query.dateRange"
              type="daterange"
              size="small"
              clearable
              :placeholder="$t('page.research.datePlaceholder')"
            />
            <NButton size="small" type="primary" :loading="loading" @click="onSearch">
              {{ $t('page.research.searchBtn') }}
            </NButton>
          </NSpace>
          <NDataTable
            remote
            flex-height
            class="h-560px"
            :loading="loading"
            :columns="columns"
            :data="records"
            :pagination="pagination"
            :row-key="(row: Api.Research.ResearchReportItem) => row.id"
          />
        </NTabPane>
      </NTabs>
    </NCard>
  </div>
</template>

<style scoped></style>
