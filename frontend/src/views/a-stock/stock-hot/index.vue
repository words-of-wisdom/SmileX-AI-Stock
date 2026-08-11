<script setup lang="tsx">
import dayjs from 'dayjs';
import { computed, onMounted, ref } from 'vue';
import { NButton, NCard, NDataTable, NDatePicker, NProgress, NSpace, NText } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import {
  fetchGetStockHotList,
  fetchGetStockHotSources,
  fetchGetStockHotDates,
  fetchSyncStockHot
} from '@/service/api';
import { useAppStore } from '@/store/modules/app';
import { useAutoRefresh } from '@/hooks/common/auto-refresh';
import { $t } from '@/locales';
import { isStockAutoRefreshTime } from '../utils';
import StockHotSourceTabs from './modules/stock-hot-source-tabs.vue';

defineOptions({
  name: 'StockHot'
});

const appStore = useAppStore();

/** 当前选中的源 */
const activeSource = ref<string>('em_rank');
/** 日期选择（回看历史快照），null = 最新 */
const selectedDate = ref<number | null>(null);
/** 可回看日期列表 */
const availableDates = ref<string[]>([]);

/** 源列表 */
const sources = ref<Api.StockHot.StockHotSourceItem[]>([]);

async function loadSources() {
  try {
    const { data, error } = await fetchGetStockHotSources();
    if (!error) {
      sources.value = data || [];
    }
  } catch {
    // ignore
  }
}

async function loadDates() {
  if (!activeSource.value) return;
  try {
    const { data, error } = await fetchGetStockHotDates(activeSource.value);
    if (!error) {
      availableDates.value = data || [];
    }
  } catch {
    // ignore
  }
}

/** 列表数据 */
const rankData = ref<Api.StockHot.StockHotRankItem[]>([]);
const loading = ref(false);

/** 全局最大热度（用于进度条归一化） */
const maxHot = computed(() => {
  let mx = 0;
  for (const r of rankData.value) {
    if (r.hot_value && r.hot_value > mx) mx = r.hot_value;
  }
  return mx || 1;
});

async function getRankData(silent = false) {
  if (!activeSource.value) return;
  if (!silent) loading.value = true;
  try {
    const { data, error } = await fetchGetStockHotList(
      activeSource.value,
      selectedDate.value ? dayjs(selectedDate.value).format('YYYY-MM-DD') : null
    );
    if (!error) {
      rankData.value = data || [];
    }
  } finally {
    if (!silent) loading.value = false;
  }
}

function onSelectSource(source: string) {
  activeSource.value = source;
  selectedDate.value = null;
  getRankData();
  loadDates();
}

function onDateChange() {
  getRankData();
}

/** 最后刷新时间 + 定时自动刷新（退出页面自动停止计时器） */
const { lastRefreshTime, refresh } = useAutoRefresh(async (silent: boolean) => {
  await Promise.all([getRankData(silent), loadSources(), loadDates()]);
}, { shouldRefresh: isStockAutoRefreshTime });

/** 手动触发同步 */
const syncing = ref(false);
async function syncData() {
  syncing.value = true;
  try {
    const { error } = await fetchSyncStockHot();
    if (!error) {
      window.$message?.success('热榜同步完成');
      await refresh();
    }
  } finally {
    syncing.value = false;
  }
}

// ---- 颜色：中国股市惯例 红涨绿跌 ----
const UP = '#f5222d';
const DOWN = '#52c41a';
const FLAT = '#8c8c8c';

/** 排名变化渲染：箭头 + 数字 */
function renderRankChange(change: number | null) {
  if (change === null) {
    return <NText depth={3} style={{ fontSize: '11px' }}>NEW</NText>;
  }
  if (change === 0) {
    return <span style={{ color: FLAT, fontSize: '13px' }}>-</span>;
  }
  const isUp = change > 0;
  const color = isUp ? UP : DOWN;
  const icon = isUp ? 'icon-mdi-arrow-up-thin' : 'icon-mdi-arrow-down-thin';
  return (
    <span class="inline-flex items-center gap-1px" style={{ color, fontSize: '12px', fontWeight: '500' }}>
      <i class={`${icon} text-12px`} />
      {Math.abs(change)}
    </span>
  );
}

/** 涨跌幅着色 */
function renderChangePct(val: number | null) {
  if (val === null || val === undefined) return <NText depth={3}>-</NText>;
  const isUp = val >= 0;
  const color = val === 0 ? FLAT : isUp ? UP : DOWN;
  return <span style={{ color, fontWeight: '500' }}>{val > 0 ? '+' : ''}{val.toFixed(2)}%</span>;
}

/** 热度值格式化 */
function formatHot(v: number): string {
  if (v >= 100000000) return `${(v / 100000000).toFixed(1)}亿`;
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万`;
  return v.toFixed(0);
}

/** 前三名排名徽章配色 */
const RANK_BADGE: Record<number, string> = {
  1: 'linear-gradient(135deg, #ff4d4f, #cf1322)',
  2: 'linear-gradient(135deg, #ff7a45, #d4380d)',
  3: 'linear-gradient(135deg, #ffa940, #d48806)'
};

const columns = computed<DataTableColumns<Api.StockHot.StockHotRankItem>>(() => [
  {
    key: 'rank',
    title: $t('page.aStock.stockHot.rank'),
    width: 90,
    align: 'center',
    sorter: (a, b) => a.rank - b.rank,
    render: row => {
      const bg = RANK_BADGE[row.rank];
      if (bg) {
        return (
          <div class="flex items-center justify-center gap-8px">
            <span
              class="inline-flex-center"
              style={{
                width: '26px',
                height: '26px',
                borderRadius: '6px',
                background: bg,
                color: '#fff',
                fontSize: '13px',
                fontWeight: '700'
              }}
            >
              {row.rank}
            </span>
            {renderRankChange(row.rank_change)}
          </div>
        );
      }
      return (
        <div class="flex items-center justify-center gap-8px">
          <span style={{ fontSize: '15px', fontWeight: '600', color: '#595959', minWidth: '26px' }}>
            {row.rank}
          </span>
          {renderRankChange(row.rank_change)}
        </div>
      );
    }
  },
  {
    key: 'stock_name',
    title: $t('page.aStock.stockHot.stockName'),
    minWidth: 160,
    render: row => (
      <div class="flex items-center gap-8px">
        <NButton
          text
          type="primary"
          class="font-500"
          onClick={() => openStockPage(row.stock_code)}
        >
          {row.stock_name}
        </NButton>
        <NText depth={3} style={{ fontSize: '12px', fontFamily: 'monospace' }}>
          {row.stock_code}
        </NText>
      </div>
    )
  },
  {
    key: 'latest_price',
    title: $t('page.aStock.stockHot.latestPrice'),
    width: 100,
    align: 'right',
    render: row => {
      if (row.latest_price === null || row.latest_price === undefined) return <NText depth={3}>-</NText>;
      const color = row.change_pct !== null && row.change_pct !== undefined
        ? (row.change_pct > 0 ? UP : row.change_pct < 0 ? DOWN : FLAT)
        : undefined;
      return <span style={{ color, fontWeight: '500' }}>{row.latest_price.toFixed(2)}</span>;
    }
  },
  {
    key: 'change_pct',
    title: $t('page.aStock.stockHot.changePct'),
    width: 100,
    align: 'right',
    sorter: (a, b) => (a.change_pct ?? -999) - (b.change_pct ?? -999),
    render: row => renderChangePct(row.change_pct)
  },
  {
    key: 'hot_value',
    title: $t('page.aStock.stockHot.hotValue'),
    width: 140,
    align: 'right',
    render: row => {
      if (row.hot_value === null || row.hot_value === undefined) return <NText depth={3}>-</NText>;
      const pct = Math.min(100, Math.round((row.hot_value / maxHot.value) * 100));
      return (
        <div class="flex items-center justify-end gap-8px">
          <NProgress
            type="line"
            percentage={pct}
            showIndicator={false}
            height={6}
            borderRadius={3}
            style={{ width: '70px' }}
            color="rgb(var(--primary-color))"
            rail-color="rgba(var(--primary-color), 0.12)"
          />
          <span style={{ fontSize: '13px', color: '#595959', minWidth: '40px', textAlign: 'right' }}>
            {formatHot(row.hot_value)}
          </span>
        </div>
      );
    }
  }
]);

/** 跳转外部行情页 */
function openStockPage(code: string) {
  // 兼容后端历史可能带 SH/SZ/BJ 前缀的旧数据，统一剥离后按交易所重新拼接
  const pure = code.replace(/^(SH|SZ|BJ)/i, '').replace(/\.(SH|SZ|BJ)$/i, '');
  let prefix: string;
  if (pure.startsWith('6')) {
    prefix = 'SH'; // 沪市主板 / 科创板
  } else if (pure.startsWith('8') || pure.startsWith('4')) {
    prefix = 'BJ'; // 北交所
  } else {
    prefix = 'SZ'; // 深市主板 / 创业板
  }
  window.open(`https://xueqiu.com/S/${prefix}${pure}`, '_blank');
}

onMounted(() => {
  refresh();
});
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <StockHotSourceTabs :sources="sources" :active="activeSource" @select="onSelectSource" />
    <NCard
      :title="$t('page.aStock.stockHot.title')"
      :bordered="false"
      size="small"
      class="card-wrapper sm:flex-1-hidden"
    >
      <template #header-extra>
        <NSpace align="center" :size="12">
          <NText depth="3" class="flex-y-center gap-4px text-12px whitespace-nowrap">
            <icon-mdi-clock-outline class="text-14px" />
            {{ $t('page.aStock.stockHot.lastRefresh') }} {{ lastRefreshTime ? lastRefreshTime.format('HH:mm:ss') : '-' }}
          </NText>
          <span class="text-13px text-secondary">{{ $t('page.aStock.stockHot.dateLabel') }}</span>
          <NDatePicker
            v-model:value="selectedDate"
            type="date"
                        :placeholder="$t('page.aStock.stockHot.datePlaceholder')"
            :is-date-disabled="(ts: number) => !availableDates.includes(dayjs(ts).format('YYYY-MM-DD'))"
            clearable
            size="small"
            class="w-180px"
            @update:value="onDateChange"
          />
          <NButton size="small" type="primary" ghost :loading="syncing" @click="syncData">
            <template #icon>
              <icon-mdi-cloud-download-outline class="text-icon" />
            </template>
            {{ $t('page.aStock.stockHot.sync') }}
          </NButton>
          <NButton size="small" :loading="loading" @click="() => refresh()">
            <template #icon>
              <icon-ic-round-refresh class="text-icon" />
            </template>
            {{ $t('common.refresh') }}
          </NButton>
        </NSpace>
      </template>
      <NDataTable
        :columns="columns"
        :data="rankData"
        size="small"
        :flex-height="!appStore.isMobile"
        :scroll-x="600"
        :loading="loading"
        :row-key="(row: Api.StockHot.StockHotRankItem) => row.id"
        class="sm:h-full"
      />
    </NCard>
  </div>
</template>

<style scoped></style>
