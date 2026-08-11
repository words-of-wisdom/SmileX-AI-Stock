<script setup lang="tsx">
import dayjs from 'dayjs';
import { computed, onMounted, ref } from 'vue';
import { NButton, NCard, NDataTable, NDatePicker, NRadioButton, NRadioGroup, NSpace, NTag, NText } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { fetchGetBoardDates, fetchGetBoardList, fetchSyncBoard } from '@/service/api';
import { $t } from '@/locales';

defineOptions({
  name: 'IndustryBoard'
});

const UP = '#f5222d';
const DOWN = '#52c41a';
const FLAT = '#8c8c8c';

const boardType = ref<Api.StockBoard.BoardType>('industry');
const sortBy = ref<Api.StockBoard.SortBy>('change_pct');
const sortOrder = ref<'asc' | 'desc'>('desc');
const selectedDate = ref<number | null>(null);
const availableDates = ref<string[]>([]);
const data = ref<Api.StockBoard.BoardDailyItem[]>([]);
const loading = ref(false);
const syncing = ref(false);

function fmtPct(val: number | null) {
  if (val === null || val === undefined) return '-';
  return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
}

function fmtMoney(val: number | null) {
  if (val === null || val === undefined) return '-';
  if (val >= 100000000) return `${(val / 100000000).toFixed(2)}亿`;
  if (val >= 10000) return `${(val / 10000).toFixed(1)}万`;
  return val.toFixed(0);
}

function pctColor(val: number | null) {
  if (val === null || val === undefined) return FLAT;
  return val > 0 ? UP : val < 0 ? DOWN : FLAT;
}

function renderPct(val: number | null) {
  if (val === null || val === undefined) return <NText depth={3}>-</NText>;
  return <span style={{ color: pctColor(val), fontWeight: '500' }}>{fmtPct(val)}</span>;
}

async function loadData() {
  loading.value = true;
  try {
    const { data: rows, error } = await fetchGetBoardList({
      board_type: boardType.value,
      date: selectedDate.value ? dayjs(selectedDate.value).format('YYYY-MM-DD') : null,
      sort_by: sortBy.value,
      sort_order: sortOrder.value
    });
    if (!error) data.value = rows || [];
  } finally {
    loading.value = false;
  }
}

async function loadDates() {
  const { data: dates, error } = await fetchGetBoardDates(boardType.value);
  if (!error) availableDates.value = dates || [];
}

async function syncData() {
  syncing.value = true;
  try {
    const { error } = await fetchSyncBoard(boardType.value);
    if (!error) {
      window.$message?.success($t('page.aStock.industryBoard.syncSuccess'));
      await Promise.all([loadData(), loadDates()]);
    }
  } finally {
    syncing.value = false;
  }
}

function onBoardTypeChange() {
  selectedDate.value = null;
  loadData();
  loadDates();
}

const columns = computed<DataTableColumns<Api.StockBoard.BoardDailyItem>>(() => [
  {
    key: 'board_name',
    title: $t('page.aStock.industryBoard.boardName'),
    minWidth: 140,
    render: row => (
      <div class="flex items-center gap-8px">
        <span class="font-500">{row.board_name}</span>
        <NText depth={3} style={{ fontSize: '12px', fontFamily: 'monospace' }}>{row.board_code}</NText>
      </div>
    )
  },
  {
    key: 'change_pct',
    title: $t('page.aStock.industryBoard.changePct'),
    width: 110,
    align: 'right',
    sorter: (a, b) => (a.change_pct ?? -999) - (b.change_pct ?? -999),
    render: row => renderPct(row.change_pct)
  },
  {
    key: 'turnover',
    title: $t('page.aStock.industryBoard.turnover'),
    width: 120,
    align: 'right',
    render: row => <span>{fmtMoney(row.turnover)}</span>
  },
  {
    key: 'turnover_rate',
    title: $t('page.aStock.industryBoard.turnoverRate'),
    width: 100,
    align: 'right',
    render: row => renderPct(row.turnover_rate)
  },
  {
    key: 'net_inflow',
    title: $t('page.aStock.industryBoard.netInflow'),
    width: 130,
    align: 'right',
    sorter: (a, b) => (a.net_inflow ?? -999) - (b.net_inflow ?? -999),
    render: row => {
      if (row.net_inflow === null || row.net_inflow === undefined) return <NText depth={3}>-</NText>;
      const color = row.net_inflow >= 0 ? UP : DOWN;
      return <span style={{ color, fontWeight: '500' }}>{fmtMoney(row.net_inflow)}</span>;
    }
  },
  {
    key: 'breadth',
    title: $t('page.aStock.industryBoard.breadth'),
    width: 110,
    align: 'center',
    render: row => (
      <span class="text-12px">
        <span style={{ color: UP }}>{row.rising_count ?? '-'}</span>
        {' / '}
        <span style={{ color: DOWN }}>{row.falling_count ?? '-'}</span>
      </span>
    )
  },
  {
    key: 'leading_stock',
    title: $t('page.aStock.industryBoard.leadingStock'),
    minWidth: 150,
    render: row => {
      if (!row.leading_stock_name) return <NText depth={3}>-</NText>;
      return (
        <div class="flex items-center gap-8px">
          <span>{row.leading_stock_name}</span>
          <NTag size="small" bordered={false} style={{ color: pctColor(row.leading_stock_change_pct) }}>
            {fmtPct(row.leading_stock_change_pct)}
          </NTag>
        </div>
      );
    }
  }
]);

onMounted(() => {
  loadData();
  loadDates();
});
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <NCard :bordered="false" size="small" class="card-wrapper">
      <div class="flex-y-center justify-between flex-wrap gap-12px">
        <NSpace align="center" :size="16">
          <NRadioGroup v-model:value="boardType" size="small" @update:value="onBoardTypeChange">
            <NRadioButton value="industry">{{ $t('page.aStock.industryBoard.industry') }}</NRadioButton>
            <NRadioButton value="concept">{{ $t('page.aStock.industryBoard.concept') }}</NRadioButton>
          </NRadioGroup>
          <NRadioGroup v-model:value="sortBy" size="small" @update:value="loadData">
            <NRadioButton value="change_pct">{{ $t('page.aStock.industryBoard.sortByChangePct') }}</NRadioButton>
            <NRadioButton value="net_inflow">{{ $t('page.aStock.industryBoard.sortByNetInflow') }}</NRadioButton>
          </NRadioGroup>
          <NRadioGroup v-model:value="sortOrder" size="small" @update:value="loadData">
            <NRadioButton value="desc">{{ $t('page.aStock.industryBoard.desc') }}</NRadioButton>
            <NRadioButton value="asc">{{ $t('page.aStock.industryBoard.asc') }}</NRadioButton>
          </NRadioGroup>
        </NSpace>
        <NSpace align="center" :size="12">
          <NDatePicker
            v-model:value="selectedDate"
            type="date"
                        :placeholder="$t('page.aStock.industryBoard.datePlaceholder')"
            :is-date-disabled="(ts: number) => !availableDates.includes(dayjs(ts).format('YYYY-MM-DD'))"
            clearable
            size="small"
            class="w-180px"
            @update:value="loadData"
          />
          <NButton size="small" type="primary" ghost :loading="syncing" @click="syncData">
            <template #icon><icon-mdi-cloud-download-outline class="text-icon" /></template>
            {{ $t('page.aStock.industryBoard.sync') }}
          </NButton>
          <NButton size="small" :loading="loading" @click="loadData">
            <template #icon><icon-ic-round-refresh class="text-icon" /></template>
            {{ $t('common.refresh') }}
          </NButton>
        </NSpace>
      </div>
    </NCard>

    <NCard :bordered="false" size="small" class="card-wrapper sm:flex-1-hidden">
      <NDataTable
        :columns="columns"
        :data="data"
        size="small"
        :loading="loading"
        :scroll-x="900"
        :row-key="(row: Api.StockBoard.BoardDailyItem) => row.id"
      />
    </NCard>
  </div>
</template>
