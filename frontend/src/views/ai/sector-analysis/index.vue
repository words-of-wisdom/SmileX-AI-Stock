<script setup lang="tsx">
/**
 * 板块分析页：行业/概念板块涨幅榜 + AI 板块轮动解读（异步生成/历史回看）
 */
import { computed, onMounted, ref } from 'vue';
import {
  NCard,
  NDataTable,
  NRadioButton,
  NRadioGroup,
  NSpace,
  NTab,
  NTabs,
  NTag,
  NText
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import dayjs from 'dayjs';
import { fetchGetBoardList } from '@/service/api';
import { $t } from '@/locales';
import { fmtAmountCn } from '../utils';
import AnalysisReportPanel from '../components/analysis-report-panel.vue';

defineOptions({ name: 'AiSectorAnalysis' });

const UP = '#f5222d';
const DOWN = '#52c41a';
const FLAT = '#8c8c8c';

/** 板块榜单展示条数（完整排行见 A股-行业板块页） */
const TOP_N = 20;

const boardType = ref<Api.StockBoard.BoardType>('industry');
const boards = ref<Api.StockBoard.BoardDailyItem[]>([]);
const loading = ref(false);

/** 分析时段：close-收盘分析（默认），morning-早盘分析（9:20 前瞻） */
const session = ref<Api.Analysis.SessionType>('close');

function pctColor(val: number | null) {
  if (val === null || val === undefined) return FLAT;
  return val > 0 ? UP : val < 0 ? DOWN : FLAT;
}

function fmtPct(val: number | null) {
  if (val === null || val === undefined) return '-';
  return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
}

async function loadBoards() {
  loading.value = true;
  try {
    const { data, error } = await fetchGetBoardList({
      board_type: boardType.value,
      sort_by: 'change_pct',
      sort_order: 'desc'
    });
    if (!error) boards.value = (data ?? []).slice(0, TOP_N);
  } finally {
    loading.value = false;
  }
}

function onBoardTypeChange() {
  loadBoards();
}

const snapshotDate = computed(() =>
  boards.value.length > 0 ? dayjs(boards.value[0].record_date).format('YYYY-MM-DD') : ''
);

const boardColumns = computed<DataTableColumns<Api.StockBoard.BoardDailyItem>>(() => [
  {
    key: 'rank',
    title: $t('page.aiAnalysis.sector.rankCol'),
    width: 56,
    align: 'center',
    render: row => {
      const rank = boards.value.indexOf(row) + 1;
      if (rank <= 3) {
        return (
          <NTag size="tiny" bordered={false} type={rank === 1 ? 'error' : rank === 2 ? 'warning' : 'info'}>
            {rank}
          </NTag>
        );
      }
      return <NText depth={3}>{rank}</NText>;
    }
  },
  {
    key: 'board_name',
    title: $t('page.aiAnalysis.sector.boardCol'),
    width: 140,
    render: row => <span class="font-500">{row.board_name}</span>
  },
  {
    key: 'change_pct',
    title: $t('page.aiAnalysis.sector.changePctCol'),
    width: 90,
    align: 'right',
    render: row => (
      <span style={{ color: pctColor(row.change_pct), fontWeight: '500' }}>{fmtPct(row.change_pct)}</span>
    )
  },
  {
    key: 'turnover',
    title: $t('page.aiAnalysis.sector.turnoverCol'),
    width: 100,
    align: 'right',
    render: row => <span>{fmtAmountCn(row.turnover)}</span>
  },
  {
    key: 'net_inflow',
    title: $t('page.aiAnalysis.sector.netInflowCol'),
    width: 110,
    align: 'right',
    render: row => (
      <span style={{ color: pctColor(row.net_inflow) }}>{fmtAmountCn(row.net_inflow)}</span>
    )
  },
  {
    key: 'rising_falling',
    title: $t('page.aiAnalysis.sector.risingFallingCol'),
    width: 110,
    align: 'center',
    render: row => (
      <span class="text-12px">
        <span style={{ color: UP }}>{row.rising_count ?? '-'}</span>
        <span style={{ color: FLAT }}> / </span>
        <span style={{ color: DOWN }}>{row.falling_count ?? '-'}</span>
      </span>
    )
  },
  {
    key: 'leading_stock',
    title: $t('page.aiAnalysis.sector.leadingStockCol'),
    minWidth: 160,
    render: row => (
      <NSpace size={4} align="center" wrap={false}>
        <span class="text-13px">{row.leading_stock_name ?? '-'}</span>
        {row.leading_stock_change_pct !== null && row.leading_stock_change_pct !== undefined ? (
          <span class="text-12px" style={{ color: pctColor(row.leading_stock_change_pct) }}>
            {fmtPct(row.leading_stock_change_pct)}
          </span>
        ) : null}
      </NSpace>
    )
  }
]);

onMounted(() => {
  loadBoards();
});
</script>

<template>
  <div class="min-h-500px h-full flex gap-16px overflow-hidden lt-sm:flex-col lt-sm:overflow-auto">
    <!-- 左：板块涨幅榜（内容区独立滚动，头部固定） -->
    <NCard
      :bordered="false"
      size="small"
      class="card-wrapper h-full w-1/2 flex-shrink-0 flex flex-col lt-sm:h-auto lt-sm:w-full"
      content-style="flex: 1 1 0%; overflow-y: auto;"
    >
      <template #header>
        <div class="flex-y-center gap-8px">
          <span class="text-16px font-500">{{ $t('page.aiAnalysis.sector.boardTitle') }}</span>
          <NText depth="3" class="text-12px">{{ snapshotDate }}</NText>
        </div>
      </template>
      <template #header-extra>
        <NSpace align="center" :size="12" wrap>
          <NText depth="3" class="text-12px">
            {{ $t('page.aiAnalysis.sector.topNTip', { n: TOP_N }) }}
          </NText>
          <NRadioGroup v-model:value="boardType" size="small" @update:value="onBoardTypeChange">
            <NRadioButton value="industry">{{ $t('page.aiAnalysis.sector.industryTab') }}</NRadioButton>
            <NRadioButton value="concept">{{ $t('page.aiAnalysis.sector.conceptTab') }}</NRadioButton>
          </NRadioGroup>
        </NSpace>
      </template>

      <NDataTable
        :columns="boardColumns"
        :data="boards"
        size="small"
        :loading="loading"
        :scroll-x="780"
        :row-key="(row: Api.StockBoard.BoardDailyItem) => row.id"
      />
    </NCard>

    <!-- 右：AI 板块轮动解读（收盘/早盘时段切换；内容区独立滚动，生成/历史/策略按钮固定可见） -->
    <div class="flex h-full min-w-0 flex-1 flex-col gap-8px lt-sm:h-auto lt-sm:flex-none">
      <NTabs v-model:value="session" type="line" size="small">
        <NTab name="close">{{ $t('page.aiAnalysis.sessionClose') }}</NTab>
        <NTab name="morning">{{ $t('page.aiAnalysis.sessionMorning') }}</NTab>
      </NTabs>
      <AnalysisReportPanel
        :key="session"
        analysis-type="sector"
        :session="session"
        class="min-w-0 flex-1 lt-sm:h-auto lt-sm:flex-none"
      />
    </div>
  </div>
</template>

<style scoped></style>
