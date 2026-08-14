<script setup lang="tsx">
import { computed, onMounted, ref, watch } from 'vue';
import {
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NProgress,
  NRadioButton,
  NRadioGroup,
  NSpace,
  NTabPane,
  NTabs,
  NText
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import dayjs from 'dayjs';
import {
  fetchGetBlockTradeActiveList,
  fetchGetBlockTradeDates,
  fetchGetBlockTradeDailyList,
  fetchSyncBlockTrade
} from '@/service/api';
import { useAppStore } from '@/store/modules/app';
import { useAutoRefresh } from '@/hooks/common/auto-refresh';
import { $t } from '@/locales';
import { fmtFixed, fmtMoney, isStockAutoRefreshTime, stockChangeColor } from '../utils';

defineOptions({
  name: 'BlockTrade'
});

const appStore = useAppStore();

/** 当前视图：daily / active */
const activeTab = ref<'daily' | 'active'>('daily');
/** 活跃榜窗口 */
const activeWindow = ref<Api.BlockTrade.StatWindow>('近一月');
/** 日期选择（仅 daily 用），null = 最新 */
const selectedDate = ref<number | null>(null);
/** 可回看日期列表 */
const availableDates = ref<string[]>([]);

/** 每日统计 / 活跃榜数据 */
const dailyData = ref<Api.BlockTrade.BlockTradeDailyItem[]>([]);
const activeData = ref<Api.BlockTrade.BlockTradeActiveItem[]>([]);
const loading = ref(false);
const syncing = ref(false);

// ---- daily 全局最大占流通市值比（用于进度条归一化） ----
const maxAmountRatio = computed(() => {
  let mx = 0;
  for (const r of dailyData.value) {
    if (r.amount_ratio && r.amount_ratio > mx) mx = r.amount_ratio;
  }
  return mx || 1;
});

// ---- active 全局最大上榜次数（用于进度条归一化） ----
const maxListCount = computed(() => {
  let mx = 0;
  for (const r of activeData.value) {
    if (r.list_count_total && r.list_count_total > mx) mx = r.list_count_total;
  }
  return mx || 1;
});

async function loadDaily(silent = false) {
  if (!silent) loading.value = true;
  try {
    const { data, error } = await fetchGetBlockTradeDailyList(
      selectedDate.value ? dayjs(selectedDate.value).format('YYYY-MM-DD') : null
    );
    if (!error) dailyData.value = data || [];
  } finally {
    if (!silent) loading.value = false;
  }
}

async function loadActive(silent = false) {
  if (!silent) loading.value = true;
  try {
    const { data, error } = await fetchGetBlockTradeActiveList(activeWindow.value);
    if (!error) activeData.value = data || [];
  } finally {
    if (!silent) loading.value = false;
  }
}

async function loadDates() {
  const { data, error } = await fetchGetBlockTradeDates();
  if (!error) availableDates.value = data || [];
}

async function loadData(silent = false) {
  if (activeTab.value === 'daily') {
    await loadDaily(silent);
  } else {
    await loadActive(silent);
  }
}

/** 最后刷新时间 + 定时自动刷新 */
const { lastRefreshTime, refresh } = useAutoRefresh(
  async (silent: boolean) => {
    await Promise.all([loadData(silent), loadDates()]);
  },
  { shouldRefresh: isStockAutoRefreshTime }
);

async function syncData() {
  syncing.value = true;
  try {
    const { error } = await fetchSyncBlockTrade();
    if (!error) {
      window.$message?.success($t('page.aStock.blockTrade.syncSuccess'));
      await refresh();
    }
  } finally {
    syncing.value = false;
  }
}

function onDateChange() {
  loadDaily();
}

function onWindowChange() {
  loadActive();
}

function onTabChange() {
  refresh();
}

watch(activeTab, () => {
  refresh();
});

// ---- 颜色 / 渲染 ----
function renderPct(val: number | null, withSign = true) {
  if (val === null || val === undefined) return <NText depth={3}>-</NText>;
  const color = stockChangeColor(val);
  const text = withSign && val > 0 ? `+${val.toFixed(2)}%` : `${val.toFixed(2)}%`;
  return <span style={{ color, fontWeight: '500' }}>{text}</span>;
}

/** 排名变化渲染：箭头 + 数字 */
function renderRankChange(change: number | null) {
  if (change === null || change === undefined) {
    return <NText depth={3} style={{ fontSize: '11px' }}>NEW</NText>;
  }
  if (change === 0) {
    return <span style={{ color: '#8c8c8c', fontSize: '13px' }}>-</span>;
  }
  const isUp = change > 0;
  const color = isUp ? '#f5222d' : '#52c41a';
  const icon = isUp ? 'icon-mdi-arrow-up-thin' : 'icon-mdi-arrow-down-thin';
  return (
    <span class="inline-flex items-center gap-1px" style={{ color, fontSize: '12px', fontWeight: '500' }}>
      <i class={`${icon} text-12px`} />
      {Math.abs(change)}
    </span>
  );
}

/** 前三名排名徽章配色 */
const RANK_BADGE: Record<number, string> = {
  1: 'linear-gradient(135deg, #ff4d4f, #cf1322)',
  2: 'linear-gradient(135deg, #ff7a45, #d4380d)',
  3: 'linear-gradient(135deg, #ffa940, #d48806)'
};

function renderRank(rank: number, change: number | null) {
  const bg = RANK_BADGE[rank];
  const badge = bg ? (
    <span
      class="inline-flex-center"
      style={{ width: '26px', height: '26px', borderRadius: '6px', background: bg, color: '#fff', fontSize: '13px', fontWeight: '700' }}
    >
      {rank}
    </span>
  ) : (
    <span style={{ fontSize: '15px', fontWeight: '600', color: '#595959', minWidth: '26px' }}>{rank}</span>
  );
  return (
    <div class="flex items-center justify-center gap-8px">
      {badge}
      {renderRankChange(change)}
    </div>
  );
}

/** 跳转外部行情页 */
function openStockPage(code: string) {
  const pure = code.replace(/^(SH|SZ|BJ)/i, '').replace(/\.(SH|SZ|BJ)$/i, '');
  let prefix: string;
  if (pure.startsWith('6')) {
    prefix = 'SH';
  } else if (pure.startsWith('8') || pure.startsWith('4')) {
    prefix = 'BJ';
  } else {
    prefix = 'SZ';
  }
  window.open(`https://xueqiu.com/S/${prefix}${pure}`, '_blank');
}

function renderStockName(code: string, name: string) {
  return (
    <div class="flex items-center gap-8px">
      <NButton text type="primary" class="font-500" onClick={() => openStockPage(code)}>
        {name}
      </NButton>
      <NText depth={3} style={{ fontSize: '12px', fontFamily: 'monospace' }}>
        {code}
      </NText>
    </div>
  );
}

// ================================================================
// 每日统计列定义
// ================================================================
const dailyColumns = computed<DataTableColumns<Api.BlockTrade.BlockTradeDailyItem>>(() => [
  {
    key: 'rank',
    title: $t('page.aStock.blockTrade.rank'),
    width: 100,
    align: 'center',
    sorter: (a, b) => a.rank - b.rank,
    render: row => renderRank(row.rank, row.rank_change)
  },
  {
    key: 'stock_name',
    title: $t('page.aStock.blockTrade.stockName'),
    width: 200,
    render: row => renderStockName(row.stock_code, row.stock_name)
  },
  {
    key: 'close_price',
    title: $t('page.aStock.blockTrade.closePrice'),
    width: 90,
    align: 'right',
    render: row => <span style={{ fontWeight: '500' }}>{fmtFixed(row.close_price)}</span>
  },
  {
    key: 'trade_price',
    title: $t('page.aStock.blockTrade.tradePrice'),
    width: 90,
    align: 'right',
    render: row => <span>{fmtFixed(row.trade_price)}</span>
  },
  {
    key: 'premium_rate',
    title: $t('page.aStock.blockTrade.premiumRate'),
    width: 100,
    align: 'right',
    sorter: (a, b) => (a.premium_rate ?? -999) - (b.premium_rate ?? -999),
    render: row => {
      if (row.premium_rate === null || row.premium_rate === undefined) return <NText depth={3}>-</NText>;
      const color = stockChangeColor(row.premium_rate);
      const sign = row.premium_rate > 0 ? '+' : '';
      return <span style={{ color, fontWeight: '500' }}>{sign}{row.premium_rate.toFixed(2)}%</span>;
    }
  },
  {
    key: 'change_pct',
    title: $t('page.aStock.blockTrade.changePct'),
    width: 100,
    align: 'right',
    sorter: (a, b) => (a.change_pct ?? -999) - (b.change_pct ?? -999),
    render: row => renderPct(row.change_pct)
  },
  {
    key: 'trade_count',
    title: $t('page.aStock.blockTrade.tradeCount'),
    width: 90,
    align: 'right',
    sorter: (a, b) => (a.trade_count ?? 0) - (b.trade_count ?? 0),
    render: row => <span>{row.trade_count ?? '-'}</span>
  },
  {
    key: 'trade_amount',
    title: $t('page.aStock.blockTrade.tradeAmount'),
    width: 120,
    align: 'right',
    sorter: (a, b) => (a.trade_amount ?? -1) - (b.trade_amount ?? -1),
    render: row => <span>{fmtMoney(row.trade_amount)}</span>
  },
  {
    key: 'amount_ratio',
    title: $t('page.aStock.blockTrade.amountRatio'),
    minWidth: 160,
    align: 'right',
    sorter: (a, b) => (a.amount_ratio ?? -1) - (b.amount_ratio ?? -1),
    render: row => {
      if (row.amount_ratio === null || row.amount_ratio === undefined) return <NText depth={3}>-</NText>;
      const pct = Math.min(100, Math.round((row.amount_ratio / maxAmountRatio.value) * 100));
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
          <span style={{ fontSize: '13px', color: '#595959', minWidth: '50px', textAlign: 'right' }}>
            {row.amount_ratio.toFixed(2)}%
          </span>
        </div>
      );
    }
  }
]);

// ================================================================
// 活跃A股列定义
// ================================================================
const activeColumns = computed<DataTableColumns<Api.BlockTrade.BlockTradeActiveItem>>(() => [
  {
    key: 'rank',
    title: $t('page.aStock.blockTrade.rank'),
    width: 80,
    align: 'center',
    sorter: (a, b) => a.rank - b.rank,
    render: row => renderRank(row.rank, null)
  },
  {
    key: 'stock_name',
    title: $t('page.aStock.blockTrade.stockName'),
    width: 200,
    render: row => renderStockName(row.stock_code, row.stock_name)
  },
  {
    key: 'latest_price',
    title: $t('page.aStock.blockTrade.latestPrice'),
    width: 90,
    align: 'right',
    render: row => (
      <span style={{ color: stockChangeColor(row.change_pct), fontWeight: '500' }}>{fmtFixed(row.latest_price)}</span>
    )
  },
  {
    key: 'change_pct',
    title: $t('page.aStock.blockTrade.changePct'),
    width: 100,
    align: 'right',
    sorter: (a, b) => (a.change_pct ?? -999) - (b.change_pct ?? -999),
    render: row => renderPct(row.change_pct)
  },
  {
    key: 'list_count_total',
    title: $t('page.aStock.blockTrade.listCountTotal'),
    width: 120,
    align: 'right',
    sorter: (a, b) => (a.list_count_total ?? 0) - (b.list_count_total ?? 0),
    render: row => {
      if (!row.list_count_total) return <NText depth={3}>-</NText>;
      const pct = Math.min(100, Math.round((row.list_count_total / maxListCount.value) * 100));
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
          <span style={{ fontSize: '13px', fontWeight: '600', minWidth: '30px', textAlign: 'right' }}>
            {row.list_count_total}
          </span>
        </div>
      );
    }
  },
  {
    key: 'list_count_premium',
    title: $t('page.aStock.blockTrade.listCountPremium'),
    width: 100,
    align: 'right',
    render: row => <span style={{ color: '#f5222d' }}>{row.list_count_premium ?? '-'}</span>
  },
  {
    key: 'list_count_discount',
    title: $t('page.aStock.blockTrade.listCountDiscount'),
    width: 100,
    align: 'right',
    render: row => <span style={{ color: '#52c41a' }}>{row.list_count_discount ?? '-'}</span>
  },
  {
    key: 'total_amount',
    title: $t('page.aStock.blockTrade.totalAmount'),
    width: 120,
    align: 'right',
    sorter: (a, b) => (a.total_amount ?? -1) - (b.total_amount ?? -1),
    render: row => <span>{fmtMoney(row.total_amount)}</span>
  },
  {
    key: 'premium_rate',
    title: $t('page.aStock.blockTrade.premiumRate'),
    width: 100,
    align: 'right',
    render: row => {
      if (row.premium_rate === null || row.premium_rate === undefined) return <NText depth={3}>-</NText>;
      const color = stockChangeColor(row.premium_rate);
      const sign = row.premium_rate > 0 ? '+' : '';
      return <span style={{ color, fontWeight: '500' }}>{sign}{row.premium_rate.toFixed(2)}%</span>;
    }
  },
  {
    key: 'last_list_date',
    title: $t('page.aStock.blockTrade.lastListDate'),
    width: 110,
    align: 'center',
    render: row => <span class="text-12px">{row.last_list_date || '-'}</span>
  },
  {
    key: 'avg_change_1d',
    title: $t('page.aStock.blockTrade.avgChange1d'),
    width: 100,
    align: 'right',
    render: row => renderPct(row.avg_change_1d)
  },
  {
    key: 'avg_change_5d',
    title: $t('page.aStock.blockTrade.avgChange5d'),
    width: 100,
    align: 'right',
    render: row => renderPct(row.avg_change_5d)
  },
  {
    key: 'avg_change_20d',
    title: $t('page.aStock.blockTrade.avgChange20d'),
    width: 100,
    align: 'right',
    render: row => renderPct(row.avg_change_20d)
  }
]);

onMounted(() => {
  refresh();
});
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <NCard :bordered="false" size="small" class="card-wrapper sm:flex-1-hidden">
      <template #header>
        <NTabs v-model:value="activeTab" type="line" animated size="large" @update:value="onTabChange">
          <NTabPane name="daily" :tab="$t('page.aStock.blockTrade.tabDaily')" />
          <NTabPane name="active" :tab="$t('page.aStock.blockTrade.tabActive')" />
        </NTabs>
      </template>
      <template #header-extra>
        <NSpace align="center" :size="12">
          <NRadioGroup
            v-if="activeTab === 'active'"
            v-model:value="activeWindow"
            size="small"
            @update:value="onWindowChange"
          >
            <NRadioButton value="近一月">{{ $t('page.aStock.blockTrade.window1m') }}</NRadioButton>
            <NRadioButton value="近三月">{{ $t('page.aStock.blockTrade.window3m') }}</NRadioButton>
            <NRadioButton value="近六月">{{ $t('page.aStock.blockTrade.window6m') }}</NRadioButton>
            <NRadioButton value="近一年">{{ $t('page.aStock.blockTrade.window1y') }}</NRadioButton>
          </NRadioGroup>
          <template v-else>
            <span class="text-13px text-secondary">{{ $t('page.aStock.blockTrade.dateLabel') }}</span>
            <NDatePicker
              v-model:value="selectedDate"
              type="date"
              :placeholder="$t('page.aStock.blockTrade.datePlaceholder')"
              :is-date-disabled="(ts: number) => !availableDates.includes(dayjs(ts).format('YYYY-MM-DD'))"
              clearable
              size="small"
              class="w-180px"
              @update:value="onDateChange"
            />
          </template>
          <NText depth="3" class="flex-y-center gap-4px text-12px whitespace-nowrap">
            <icon-mdi-clock-outline class="text-14px" />
            {{ $t('page.aStock.blockTrade.lastRefresh') }}
            {{ lastRefreshTime ? lastRefreshTime.format('HH:mm:ss') : '-' }}
          </NText>
          <NButton size="small" type="primary" ghost :loading="syncing" @click="syncData">
            <template #icon><icon-mdi-cloud-download-outline class="text-icon" /></template>
            {{ $t('page.aStock.blockTrade.sync') }}
          </NButton>
          <NButton size="small" :loading="loading" @click="() => refresh()">
            <template #icon><icon-ic-round-refresh class="text-icon" /></template>
            {{ $t('common.refresh') }}
          </NButton>
        </NSpace>
      </template>
      <NDataTable
        v-if="activeTab === 'daily'"
        :columns="dailyColumns"
        :data="dailyData"
        size="small"
        :flex-height="!appStore.isMobile"
        :scroll-x="1050"
        :loading="loading"
        :row-key="(row: Api.BlockTrade.BlockTradeDailyItem) => row.id"
        class="sm:h-full"
      />
      <NDataTable
        v-else
        :columns="activeColumns"
        :data="activeData"
        size="small"
        :flex-height="!appStore.isMobile"
        :scroll-x="1400"
        :loading="loading"
        :row-key="(row: Api.BlockTrade.BlockTradeActiveItem) => row.id"
        class="sm:h-full"
      />
    </NCard>
  </div>
</template>

<style scoped></style>
