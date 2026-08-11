<script setup lang="tsx">
import dayjs from 'dayjs';
import { computed, onMounted, ref } from 'vue';
import { NButton, NCard, NDatePicker, NGrid, NGridItem, NSpace, NStatistic, NText } from 'naive-ui';
import { fetchGetMarketDates, fetchGetMarketIndices, fetchSyncMarket } from '@/service/api';
import { useAutoRefresh } from '@/hooks/common/auto-refresh';
import { $t } from '@/locales';
import { isStockAutoRefreshTime } from '../../utils';

const UP = '#f5222d';
const DOWN = '#52c41a';
const FLAT = '#8c8c8c';

const indices = ref<Api.StockMarket.MarketIndexItem[]>([]);
const availableDates = ref<string[]>([]);
const selectedDate = ref<number | null>(null);
const loading = ref(false);
const syncing = ref(false);

function renderChangeColor(val: number | null) {
  if (val === null || val === undefined) return { color: FLAT };
  return { color: val > 0 ? UP : val < 0 ? DOWN : FLAT };
}

function fmtPct(val: number | null) {
  if (val === null || val === undefined) return '-';
  return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
}

function fmtNum(val: number | null, digits = 2) {
  if (val === null || val === undefined) return '-';
  return val.toFixed(digits);
}

function fmtTurnover(val: number | null) {
  if (val === null || val === undefined) return '-';
  if (val >= 100000000000) return `${(val / 100000000000).toFixed(2)}千亿`;
  if (val >= 100000000) return `${(val / 100000000).toFixed(1)}亿`;
  if (val >= 10000) return `${(val / 10000).toFixed(1)}万`;
  return val.toFixed(0);
}

const totalTurnover = computed(() => {
  let sum = 0;
  for (const it of indices.value) sum += it.turnover || 0;
  return sum;
});

async function loadData(silent = false) {
  if (!silent) loading.value = true;
  try {
    const { data, error } = await fetchGetMarketIndices(
      selectedDate.value ? dayjs(selectedDate.value).format('YYYY-MM-DD') : null
    );
    if (!error) indices.value = data || [];
  } finally {
    if (!silent) loading.value = false;
  }
}

async function loadDates() {
  const { data, error } = await fetchGetMarketDates();
  if (!error) availableDates.value = data || [];
}

async function syncData() {
  syncing.value = true;
  try {
    const { error } = await fetchSyncMarket();
    if (!error) {
      window.$message?.success($t('page.aStock.marketOverview.syncSuccess'));
      await refresh();
    }
  } finally {
    syncing.value = false;
  }
}

/** 最后刷新时间 + 定时自动刷新（退出页面自动停止计时器） */
const { lastRefreshTime, refresh } = useAutoRefresh(async (silent: boolean) => {
  await Promise.all([loadData(silent), loadDates()]);
}, { shouldRefresh: isStockAutoRefreshTime });

function onDateChange() {
  loadData();
}

onMounted(() => {
  refresh();
});
</script>

<template>
  <div class="flex-col-stretch gap-16px">
    <NCard :bordered="false" size="small" class="card-wrapper">
      <div class="flex-y-center justify-between flex-wrap gap-12px">
        <NSpace align="center" :size="24">
          <NStatistic :label="$t('page.aStock.marketOverview.totalTurnover')" :value="fmtTurnover(totalTurnover)" />
          <NStatistic :label="$t('page.aStock.marketOverview.indexCount')" :value="indices.length" />
        </NSpace>
        <NSpace align="center" :size="12">
          <NText depth="3" class="flex-y-center gap-4px text-12px whitespace-nowrap">
            <icon-mdi-clock-outline class="text-14px" />
            {{ $t('page.aStock.marketOverview.lastRefresh') }} {{ lastRefreshTime ? lastRefreshTime.format('HH:mm:ss') : '-' }}
          </NText>
          <NDatePicker
            v-model:value="selectedDate"
            type="date"
                        :placeholder="$t('page.aStock.marketOverview.datePlaceholder')"
            :is-date-disabled="(ts: number) => !availableDates.includes(dayjs(ts).format('YYYY-MM-DD'))"
            clearable
            size="small"
            class="w-180px"
            @update:value="onDateChange"
          />
          <NButton size="small" type="primary" ghost :loading="syncing" @click="syncData">
            <template #icon><icon-mdi-cloud-download-outline class="text-icon" /></template>
            {{ $t('page.aStock.marketOverview.sync') }}
          </NButton>
          <NButton size="small" :loading="loading" @click="() => refresh()">
            <template #icon><icon-ic-round-refresh class="text-icon" /></template>
            {{ $t('common.refresh') }}
          </NButton>
        </NSpace>
      </div>
    </NCard>

    <NGrid responsive="screen" cols="1 s:2 m:3 l:4" :x-gap="16" :y-gap="16">
      <NGridItem v-for="item in indices" :key="item.index_code">
        <NCard :bordered="false" size="small" class="index-card" :loading="loading">
          <div class="flex-col gap-8px">
            <div class="flex-y-center justify-between">
              <span class="font-600 text-15px">{{ item.index_name }}</span>
              <NText depth="3" class="text-12px">{{ item.index_code }}</NText>
            </div>
            <div class="flex-y-end justify-between">
              <span class="text-24px font-700" :style="renderChangeColor(item.change_pct)">
                {{ fmtNum(item.latest_price) }}
              </span>
              <div class="flex-col items-end gap-2px">
                <span :style="renderChangeColor(item.change_pct)" class="text-14px font-600">
                  {{ fmtPct(item.change_pct) }}
                </span>
                <span :style="renderChangeColor(item.change_pct)" class="text-12px">
                  {{ item.change_amount !== null ? `${item.change_amount > 0 ? '+' : ''}${item.change_amount.toFixed(2)}` : '-' }}
                </span>
              </div>
            </div>
            <div class="grid grid-cols-3 gap-4px pt-8px" style="border-top: 1px solid rgba(128,128,128,0.15)">
              <div class="flex-col gap-2px">
                <NText depth="3" class="text-11px">{{ $t('page.aStock.marketOverview.turnover') }}</NText>
                <span class="text-12px">{{ fmtTurnover(item.turnover) }}</span>
              </div>
              <div class="flex-col gap-2px">
                <NText depth="3" class="text-11px">{{ $t('page.aStock.marketOverview.amplitude') }}</NText>
                <span class="text-12px">{{ fmtPct(item.amplitude) }}</span>
              </div>
              <div class="flex-col gap-2px">
                <NText depth="3" class="text-11px">{{ $t('page.aStock.marketOverview.highLow') }}</NText>
                <span class="text-12px">{{ fmtNum(item.high, 0) }}/{{ fmtNum(item.low, 0) }}</span>
              </div>
            </div>
          </div>
        </NCard>
      </NGridItem>
    </NGrid>

    <div v-if="!loading && indices.length === 0" class="py-40px text-center">
      <NText depth="3">{{ $t('page.aStock.marketOverview.noData') }}</NText>
    </div>
  </div>
</template>

<style scoped>
.index-card :deep(.n-card__content) {
  padding: 16px;
}
</style>
