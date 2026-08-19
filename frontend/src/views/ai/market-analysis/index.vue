<script setup lang="tsx">
/**
 * 大盘分析页：指数快照 + 大盘资金流摘要 + AI 大盘点评（异步生成/历史回看）
 */
import { computed, onMounted, ref } from 'vue';
import { NCard, NGrid, NGridItem, NSpace, NStatistic, NText } from 'naive-ui';
import { fetchGetMarketFundFlow, fetchGetMarketIndices } from '@/service/api';
import { $t } from '@/locales';
import AnalysisReportPanel from '../components/analysis-report-panel.vue';

defineOptions({ name: 'AiMarketAnalysis' });

const UP = '#f5222d';
const DOWN = '#52c41a';
const FLAT = '#8c8c8c';

const indices = ref<Api.StockMarket.MarketIndexItem[]>([]);
const fundFlows = ref<Api.StockMarket.MarketFundFlowItem[]>([]);
const loading = ref(false);

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

function fmtMoney(val: number | null) {
  if (val === null || val === undefined) return '-';
  if (val >= 100000000) return `${(val / 100000000).toFixed(0)}亿`;
  if (val >= 10000) return `${(val / 10000).toFixed(1)}万`;
  return val.toFixed(0);
}

/** 最新一日大盘资金流（指数快照日的资金流入流出） */
const latestFundFlow = computed(() => fundFlows.value[fundFlows.value.length - 1] ?? null);

const totalTurnover = computed(() => indices.value.reduce((sum, it) => sum + (it.turnover || 0), 0));

async function loadData() {
  loading.value = true;
  try {
    const [indicesRes, fundFlowRes] = await Promise.all([
      fetchGetMarketIndices(),
      fetchGetMarketFundFlow(5)
    ]);
    if (!indicesRes.error) indices.value = indicesRes.data ?? [];
    if (!fundFlowRes.error) fundFlows.value = fundFlowRes.data ?? [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <!-- 指数快照 + 资金流摘要 -->
    <NCard :bordered="false" size="small" class="card-wrapper" :loading="loading">
      <template #header>
        <div class="flex-y-center gap-8px">
          <span class="text-16px font-500">{{ $t('page.aiAnalysis.market.indicesTitle') }}</span>
          <NText depth="3" class="text-12px">
            {{ indices.length > 0 ? indices[0].record_date : '' }}
          </NText>
        </div>
      </template>
      <template #header-extra>
        <NSpace align="center" :size="24">
          <NStatistic :label="$t('page.aiAnalysis.market.totalTurnover')" :value="fmtMoney(totalTurnover)" />
          <NStatistic
            v-if="latestFundFlow"
            :label="$t('page.aiAnalysis.market.mainInflowLabel')"
            tabular-nums
          >
            <span :style="{ color: pctColor(latestFundFlow.main_net_inflow), fontWeight: '600' }">
              {{ fmtMoney(latestFundFlow.main_net_inflow) }}
            </span>
          </NStatistic>
        </NSpace>
      </template>

      <NGrid :x-gap="12" :y-gap="12" :cols="2" s:cols="3" l:cols="4" xl:cols="7" responsive="screen">
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
                {{ $t('page.aiAnalysis.market.turnover') }} {{ fmtMoney(item.turnover) }}
              </NText>
            </div>
          </div>
        </NGridItem>
      </NGrid>
    </NCard>

    <!-- AI 大盘点评 -->
    <AnalysisReportPanel analysis-type="market" class="sm:flex-1-hidden" />
  </div>
</template>

<style scoped></style>
