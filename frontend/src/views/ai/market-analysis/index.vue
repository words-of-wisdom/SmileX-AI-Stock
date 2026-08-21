<script setup lang="tsx">
/**
 * 大盘分析页：指数快照 + 大盘资金流摘要 + AI 大盘点评（异步生成/历史回看）
 */
import { computed, onMounted, ref } from 'vue';
import { NCard, NGrid, NGridItem, NSpace, NStatistic, NTab, NTabs, NTag, NText } from 'naive-ui';
import dayjs from 'dayjs';
import { fetchGetMarketDates, fetchGetMarketFundFlow, fetchGetMarketIndices } from '@/service/api';
import { $t } from '@/locales';
import { fmtAmountCn } from '../utils';
import AnalysisReportPanel from '../components/analysis-report-panel.vue';

defineOptions({ name: 'AiMarketAnalysis' });

const UP = '#f5222d';
const DOWN = '#52c41a';
const FLAT = '#8c8c8c';

const indices = ref<Api.StockMarket.MarketIndexItem[]>([]);
const fundFlows = ref<Api.StockMarket.MarketFundFlowItem[]>([]);
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

function fmtNum(val: number | null, digits = 2) {
  if (val === null || val === undefined) return '-';
  return val.toFixed(digits);
}

/** 最新一日大盘资金流（指数快照日的资金流入流出） */
const latestFundFlow = computed(() => fundFlows.value[fundFlows.value.length - 1] ?? null);

/** 上一交易日大盘资金流 */
const prevFundFlow = computed(() =>
  fundFlows.value.length >= 2 ? fundFlows.value[fundFlows.value.length - 2] : null
);

const totalTurnover = computed(() => indices.value.reduce((sum, it) => sum + (it.turnover || 0), 0));

// ================================================================
// 同上一交易日比较（成交额环比 + 主力净流入环比）
// ================================================================
const prevIndices = ref<Api.StockMarket.MarketIndexItem[]>([]);
const prevTotalTurnover = computed(() => prevIndices.value.reduce((sum, it) => sum + (it.turnover || 0), 0));

const prevDateLabel = computed(() => {
  const d = prevIndices.value[0]?.record_date ?? prevFundFlow.value?.record_date;
  return d ? dayjs(d).format('YYYY-MM-DD') : '';
});

/** 成交额环比：今日两市总成交额 - 上一交易日总成交额 */
const turnoverDelta = computed(() => {
  if (!prevIndices.value.length || !indices.value.length) return null;
  const delta = totalTurnover.value - prevTotalTurnover.value;
  const pct = prevTotalTurnover.value > 0 ? (delta / prevTotalTurnover.value) * 100 : null;
  return { delta, pct };
});

/** 主力净流入环比：今日 - 上一交易日 */
const fundFlowDelta = computed(() => {
  const cur = latestFundFlow.value?.main_net_inflow;
  const prev = prevFundFlow.value?.main_net_inflow;
  if (cur === null || cur === undefined || prev === null || prev === undefined) return null;
  return { delta: cur - prev };
});

function fmtSignedAmount(val: number) {
  return `${val >= 0 ? '+' : ''}${fmtAmountCn(val)}`;
}

function fmtDeltaPct(pct: number | null) {
  if (pct === null || pct === undefined) return '';
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
}

async function loadData() {
  loading.value = true;
  try {
    const [indicesRes, fundFlowRes, datesRes] = await Promise.all([
      fetchGetMarketIndices(),
      fetchGetMarketFundFlow(5),
      fetchGetMarketDates()
    ]);
    if (!indicesRes.error) indices.value = indicesRes.data ?? [];
    if (!fundFlowRes.error) fundFlows.value = fundFlowRes.data ?? [];

    // 上一交易日指数快照（计算两市成交额环比；跳过周末/节假日取真实上一交易日）
    const today = indices.value[0]?.record_date;
    const prevDate = (datesRes.data ?? []).find(d => d < (today ?? ''));
    if (prevDate) {
      const prevRes = await fetchGetMarketIndices(prevDate);
      if (!prevRes.error) prevIndices.value = prevRes.data ?? [];
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="min-h-500px h-full flex gap-16px overflow-hidden lt-sm:flex-col lt-sm:overflow-auto">
    <!-- 左：指数快照 + 资金流摘要（内容区独立滚动，头部固定） -->
    <NCard
      :bordered="false"
      size="small"
      class="card-wrapper h-full w-2/5 flex-shrink-0 flex flex-col lt-sm:h-auto lt-sm:w-full"
      content-style="flex: 1 1 0%; overflow-y: auto;"
      :loading="loading"
    >
      <template #header>
        <div class="flex-y-center gap-8px">
          <span class="text-16px font-500">{{ $t('page.aiAnalysis.market.indicesTitle') }}</span>
          <NText depth="3" class="text-12px">
            {{ indices.length > 0 ? indices[0].record_date : '' }}
          </NText>
        </div>
      </template>
      <template #header-extra>
        <NSpace align="center" :size="16" wrap>
          <NStatistic :label="$t('page.aiAnalysis.market.totalTurnover')" :value="fmtAmountCn(totalTurnover)" />
          <NStatistic
            v-if="latestFundFlow"
            :label="$t('page.aiAnalysis.market.mainInflowLabel')"
            tabular-nums
          >
            <span :style="{ color: pctColor(latestFundFlow.main_net_inflow), fontWeight: '600' }">
              {{ fmtAmountCn(latestFundFlow.main_net_inflow) }}
            </span>
          </NStatistic>
        </NSpace>
      </template>

      <!-- 同上一交易日比较 -->
      <div
        v-if="turnoverDelta || fundFlowDelta"
        class="mb-12px flex flex-col gap-4px rounded-6px border border-gray-200 px-12px py-8px dark:border-gray-700"
      >
        <NText depth="3" class="text-12px">
          {{ $t('page.aiAnalysis.market.compareLabel') }}{{ prevDateLabel ? `（${prevDateLabel}）` : '' }}
        </NText>
        <div class="flex flex-col gap-2px text-13px sm:flex-row sm:flex-wrap sm:gap-x-24px">
          <span v-if="turnoverDelta" class="flex-y-center flex-wrap gap-4px">
            <NText depth="2">{{ $t('page.aiAnalysis.market.turnover') }}</NText>
            <span style="font-family: monospace">
              <NText depth="3">{{ fmtAmountCn(prevTotalTurnover) }}</NText>
              <span class="mx-4px">→</span>
              <span :style="{ color: pctColor(turnoverDelta.delta), fontWeight: '600' }">
                {{ fmtAmountCn(totalTurnover) }}
              </span>
            </span>
            <NTag size="tiny" :bordered="false" :type="turnoverDelta.delta >= 0 ? 'error' : 'success'">
              {{ turnoverDelta.delta >= 0 ? $t('page.aiAnalysis.market.volumeUp') : $t('page.aiAnalysis.market.volumeDown') }}
              {{ fmtDeltaPct(turnoverDelta.pct) }}
            </NTag>
          </span>
          <span v-if="fundFlowDelta" class="flex-y-center flex-wrap gap-4px">
            <NText depth="2">{{ $t('page.aiAnalysis.market.mainInflowLabel') }}</NText>
            <span style="font-family: monospace">
              <NText depth="3">{{ fmtAmountCn(prevFundFlow?.main_net_inflow ?? null) }}</NText>
              <span class="mx-4px">→</span>
              <span :style="{ color: pctColor(fundFlowDelta.delta), fontWeight: '600' }">
                {{ fmtAmountCn(latestFundFlow?.main_net_inflow ?? null) }}
              </span>
            </span>
            <span class="text-12px" style="font-family: monospace" :style="{ color: pctColor(fundFlowDelta.delta) }">
              {{ fmtSignedAmount(fundFlowDelta.delta) }}
            </span>
          </span>
        </div>
      </div>

      <NGrid :x-gap="12" :y-gap="12" :cols="2" l:cols="3" responsive="screen">
        <NGridItem v-for="item in indices" :key="item.index_code">
          <div class="rounded-6px border border-gray-200 px-12px py-10px dark:border-gray-700">
            <div class="flex items-center justify-between">
              <span class="text-13px font-500">{{ item.index_name }}</span>
              <span class="text-12px" style="font-family: monospace" :style="{ color: pctColor(item.change_pct) }">
                {{ fmtPct(item.change_pct) }}
              </span>
            </div>
            <div class="mt-4px flex items-baseline gap-8px">
              <span
                class="text-20px font-600"
                :style="{ color: pctColor(item.change_pct), fontFamily: 'monospace' }"
              >
                {{ fmtNum(item.latest_price) }}
              </span>
              <NText depth="3" class="text-12px">
                {{ $t('page.aiAnalysis.market.turnover') }} {{ fmtAmountCn(item.turnover) }}
              </NText>
            </div>
          </div>
        </NGridItem>
      </NGrid>
    </NCard>

    <!-- 右：AI 大盘点评（收盘/早盘时段切换；内容区独立滚动，生成/历史/策略按钮固定可见） -->
    <div class="flex h-full min-w-0 flex-1 flex-col gap-8px lt-sm:h-auto lt-sm:flex-none">
      <NTabs v-model:value="session" type="line" size="small">
        <NTab name="close">{{ $t('page.aiAnalysis.sessionClose') }}</NTab>
        <NTab name="morning">{{ $t('page.aiAnalysis.sessionMorning') }}</NTab>
      </NTabs>
      <AnalysisReportPanel
        :key="session"
        analysis-type="market"
        :session="session"
        class="min-w-0 flex-1 lt-sm:h-auto lt-sm:flex-none"
      />
    </div>
  </div>
</template>

<style scoped></style>
