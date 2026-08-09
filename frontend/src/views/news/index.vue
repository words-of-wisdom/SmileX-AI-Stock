<script setup lang="tsx">
import { computed, onMounted, reactive, ref } from 'vue';
import { NButton, NCard, NDataTable, NEmpty, NSpace, NSpin, NTag } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { fetchGetNewsList, fetchGetNewsSources } from '@/service/api';
import { useAppStore } from '@/store/modules/app';
import { $t } from '@/locales';
import NewsDetailDrawer from './modules/news-detail-drawer.vue';
import NewsSearch from './modules/news-search.vue';

defineOptions({
  name: 'News'
});

const appStore = useAppStore();

/** 来源 -> 颜色映射，保证多源视觉区分 */
const SOURCE_COLOR_MAP: Record<string, NaiveUI.ThemeColor> = {
  eastmoney: 'success',
  eastmoney_global: 'info',
  cls: 'error',
  cls_red: 'error',
  cls_announcement: 'warning',
  cls_watch: 'info',
  cls_hk_us: 'success',
  cls_fund: 'default',
  cls_remind: 'warning',
  tonghuashun: 'info',
  sina: 'success',
  wallstreetcn: 'error',
  yicai: 'warning',
  futu: 'default',
  xueqiu: 'success',
  jrj: 'info'
};

function sourceColor(source: string): NaiveUI.ThemeColor {
  return SOURCE_COLOR_MAP[source] ?? 'default';
}

/** 搜索参数 */
const searchParams = reactive<Api.News.NewsSearchParams>({
  page: 1,
  page_size: 10,
  keyword: null,
  source: null,
  start_time: null,
  end_time: null
});

/** 选中的新闻源 key，null 表示全部 */
const selectedSource = ref<string | null>(null);

/** 新闻源统计 */
const sources = ref<Api.News.NewsSourceItem[]>([]);
const sourcesLoading = ref(false);

const totalCount = computed(() => sources.value.reduce((acc, s) => acc + s.count, 0));

async function loadSources() {
  sourcesLoading.value = true;
  try {
    const { data, error } = await fetchGetNewsSources();
    if (!error) {
      sources.value = data || [];
    }
  } finally {
    sourcesLoading.value = false;
  }
}

/** 选中某个源（null=全部） */
function selectSource(key: string | null) {
  selectedSource.value = key;
  searchParams.source = key;
  searchParams.page = 1;
  getNewsData();
}

/** 列表数据 */
const newsData = ref<Api.News.News[]>([]);
const loading = ref(false);

async function getNewsData() {
  loading.value = true;
  try {
    const { data: resp, error } = await fetchGetNewsList(searchParams);
    if (!error && resp) {
      newsData.value = resp.records || [];
    }
  } finally {
    loading.value = false;
  }
}

function handlePageChange(page: number) {
  searchParams.page = page;
  getNewsData();
}

function handlePageSizeChange(pageSize: number) {
  searchParams.page_size = pageSize;
  searchParams.page = 1;
  getNewsData();
}

function onSearch() {
  searchParams.page = 1;
  getNewsData();
  loadSources();
}

/** 详情抽屉 */
const drawerVisible = ref(false);
const currentNewsId = ref<number | null>(null);

function openDetail(id: number) {
  currentNewsId.value = id;
  drawerVisible.value = true;
}

/** 表格列 */
const columns = computed<DataTableColumns<Api.News.News>>(() => [
  {
    key: 'title',
    title: $t('common.title'),
    ellipsis: { tooltip: true },
    render: row => (
      <NButton text type="primary" class="font-500" onClick={() => openDetail(row.id)}>
        {row.title}
      </NButton>
    )
  },
  {
    key: 'source_name',
    title: $t('page.news.source'),
    width: 130,
    render: row => (
      <NTag type={sourceColor(row.source) as 'success'} size="small">
        {row.source_name}
      </NTag>
    )
  },
  {
    key: 'summary',
    title: $t('page.news.summary'),
    minWidth: 240,
    ellipsis: { tooltip: true },
    render: row => <span class="text-secondary">{row.summary || '-'}</span>
  },
  {
    key: 'published_at',
    title: $t('page.news.publishedAt'),
    width: 170,
    render: row => <span class="text-secondary">{row.published_at || row.created_at || '-'}</span>
  }
]);

/** 分页配置 */
const pagination = reactive({
  page: 1,
  pageSize: 10,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 30, 50],
  prefix: ({ itemCount }: { itemCount: number }) => $t('datatable.itemCount', { total: itemCount }),
  onUpdatePage: (page: number) => handlePageChange(page),
  onUpdatePageSize: (pageSize: number) => handlePageSizeChange(pageSize)
});

onMounted(async () => {
  await Promise.all([getNewsData(), loadSources()]);
});
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <NewsSearch :model="searchParams" @search="onSearch" @reset="onSearch" />
    <div class="flex flex-1-hidden gap-16px overflow-hidden lt-sm:flex-col">
      <!-- 源侧栏 -->
      <NCard :bordered="false" size="small" class="news-source-sidebar lt-sm:w-full">
        <NSpin :show="sourcesLoading">
          <div class="flex-col-stretch gap-4px">
            <NButton
              :type="selectedSource === null ? 'primary' : 'default'"
              :ghost="selectedSource === null"
              size="small"
              class="justify-start"
              block
              @click="selectSource(null)"
            >
              <div class="flex w-full items-center justify-between">
                <span>{{ $t('page.news.allSources') }}</span>
                <NTag :bordered="false" size="tiny" round>{{ totalCount }}</NTag>
              </div>
            </NButton>
            <NButton
              v-for="s in sources"
              :key="s.source"
              :type="selectedSource === s.source ? 'primary' : 'default'"
              :ghost="selectedSource === s.source"
              size="small"
              class="justify-start"
              block
              @click="selectSource(s.source)"
            >
              <div class="flex w-full items-center justify-between">
                <NSpace align="center" :size="4">
                  <span class="news-dot" :class="`news-dot-${sourceColor(s.source)}`" />
                  <span>{{ s.source_name }}</span>
                </NSpace>
                <NTag :bordered="false" size="tiny" round>{{ s.count }}</NTag>
              </div>
            </NButton>
            <NEmpty v-if="sources.length === 0" :description="$t('common.noData')" class="py-24px" />
          </div>
        </NSpin>
      </NCard>
      <!-- 主列表 -->
      <NCard
        :title="$t('page.news.title')"
        :bordered="false"
        size="small"
        class="card-wrapper sm:flex-1-hidden"
      >
        <template #header-extra>
          <NButton size="small" :loading="loading" @click="getNewsData">
            <template #icon>
              <icon-ic-round-refresh class="text-icon" />
            </template>
            {{ $t('common.refresh') }}
          </NButton>
        </template>
        <NDataTable
          :columns="columns"
          :data="newsData"
          size="small"
          :flex-height="!appStore.isMobile"
          :scroll-x="900"
          :loading="loading"
          remote
          :row-key="(row: Api.News.News) => row.id"
          :pagination="pagination"
          class="sm:h-full"
        />
      </NCard>
    </div>
    <NewsDetailDrawer v-model:visible="drawerVisible" :news-id="currentNewsId" />
  </div>
</template>

<style scoped>
.news-source-sidebar {
  width: 220px;
  flex-shrink: 0;
}

.news-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.news-dot-success {
  background: var(--n-color-success, #18a058);
}

.news-dot-info {
  background: var(--n-color-info, #2080f0);
}

.news-dot-warning {
  background: var(--n-color-warning, #f0a020);
}

.news-dot-error {
  background: var(--n-color-error, #d03050);
}

.news-dot-default {
  background: var(--n-color-default, #909399);
}
</style>
