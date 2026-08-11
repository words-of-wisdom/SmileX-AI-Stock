<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { NCard, NSelect, NSpace, NTag } from 'naive-ui';
import { fetchGetMarketIndexHistory, fetchGetMarketIndexOptions } from '@/service/api';
import { useEcharts } from '@/hooks/common/echarts';
import type { ECOption } from '@/hooks/common/echarts';
import { $t } from '@/locales';

const UP = '#f5222d';
const DOWN = '#52c41a';

const indexOptions = ref<Api.StockMarket.MarketIndexOption[]>([]);
const selectedIndex = ref<string>('000001');
const historyData = ref<Api.StockMarket.MarketIndexHistoryItem[]>([]);
const loading = ref(false);

const latestItem = computed(() =>
  historyData.value.length ? historyData.value[historyData.value.length - 1] : null
);
const latestColor = computed(() => {
  const v = latestItem.value?.change_pct;
  if (v === null || v === undefined) return '#8c8c8c';
  return v >= 0 ? UP : DOWN;
});

const { domRef, updateOptions } = useEcharts<ECOption>(() => ({
  tooltip: { trigger: 'axis' as const },
  grid: { left: 12, right: 16, top: 30, bottom: 30, containLabel: true },
  xAxis: { type: 'category' as const, data: [] },
  yAxis: { type: 'value' as const, scale: true },
  series: [
    {
      name: $t('page.aStock.marketOverview.closePrice'),
      type: 'line' as const,
      data: [],
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: '#5470c6' },
      areaStyle: { opacity: 0.08, color: '#5470c6' }
    }
  ]
}));

async function loadOptions() {
  const { data, error } = await fetchGetMarketIndexOptions();
  if (!error) {
    indexOptions.value = data || [];
    if (indexOptions.value.length && !indexOptions.value.find(o => o.index_code === selectedIndex.value)) {
      selectedIndex.value = indexOptions.value[0].index_code;
    }
  }
}

async function loadHistory() {
  if (!selectedIndex.value) return;
  loading.value = true;
  try {
    const { data, error } = await fetchGetMarketIndexHistory(selectedIndex.value, 90);
    if (!error) {
      historyData.value = data || [];
      const dates = historyData.value.map(d => d.record_date);
      const prices = historyData.value.map(d => d.latest_price);
      await updateOptions(() => ({
        xAxis: { type: 'category' as const, data: dates },
        series: [
          {
            name: $t('page.aStock.marketOverview.closePrice'),
            type: 'line' as const,
            data: prices,
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: '#5470c6' },
            areaStyle: { opacity: 0.08, color: '#5470c6' }
          }
        ]
      }));
    }
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await loadOptions();
  await loadHistory();
});
</script>

<template>
  <NCard :bordered="false" size="small" class="card-wrapper" :loading="loading">
    <template #header>
      <NSpace align="center" :size="16">
        <span class="font-600">{{ $t('page.aStock.marketOverview.historyMarket') }}</span>
        <NSelect
          v-model:value="selectedIndex"
          :options="indexOptions.map(o => ({ label: `${o.index_name} (${o.index_code})`, value: o.index_code }))"
          size="small"
          class="w-240px"
          @update:value="loadHistory"
        />
        <template v-if="latestItem">
          <NTag :style="{ color: latestColor }" size="small" :bordered="false">
            {{ latestItem.latest_price !== null ? latestItem.latest_price.toFixed(2) : '-' }}
          </NTag>
          <span class="text-13px" :style="{ color: latestColor }">
            {{ latestItem.change_pct !== null ? `${latestItem.change_pct > 0 ? '+' : ''}${latestItem.change_pct.toFixed(2)}%` : '-' }}
          </span>
        </template>
      </NSpace>
    </template>
    <div ref="domRef" class="h-420px w-full" />
  </NCard>
</template>
