<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { NCard, NSelect, NSpace, NTag } from 'naive-ui';
import { fetchGetMarketIndexHistory, fetchGetMarketIndexOptions } from '@/service/api';
import { useEcharts } from '@/hooks/common/echarts';
import type { ECOption } from '@/hooks/common/echarts';
import { $t } from '@/locales';
import { fmtFixed, fmtMoney, fmtVolume, stockChangeColor, STOCK_DOWN_COLOR, STOCK_UP_COLOR } from '../../utils';

interface Props {
  /** 卡片标题，默认“走势图” */
  title?: string;
}

const props = withDefaults(defineProps<Props>(), {
  title: ''
});

const FLAT = '#8c8c8c';

const indexOptions = ref<Api.StockMarket.MarketIndexOption[]>([]);
const selectedIndex = ref<string>('000001');
const historyData = ref<Api.StockMarket.MarketIndexHistoryItem[]>([]);
/** 实际参与绘图的行（过滤了 OHLC 不完整的行），供 tooltip 按 dataIndex 回查 */
const chartRows = ref<Api.StockMarket.MarketIndexHistoryItem[]>([]);
const loading = ref(false);

const latestItem = computed(() =>
  historyData.value.length ? historyData.value[historyData.value.length - 1] : null
);
const latestColor = computed(() => stockChangeColor(latestItem.value?.change_pct));

interface AxisTooltipParam {
  dataIndex: number;
}

function fmtPctText(val: number | null) {
  if (val === null || val === undefined) return '-';
  return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
}

function formatTooltip(params: AxisTooltipParam | AxisTooltipParam[]) {
  const list = Array.isArray(params) ? params : [params];
  const idx = list[0]?.dataIndex ?? 0;
  const row = chartRows.value[idx];
  if (!row) return '';
  const pctColor = row.change_pct === null || row.change_pct === undefined ? FLAT : stockChangeColor(row.change_pct);
  const lines = [
    `<div style="font-weight:600;margin-bottom:4px">${row.record_date}</div>`,
    `${$t('page.aStock.marketOverview.open')}：${fmtFixed(row.open)}`,
    `${$t('page.aStock.marketOverview.closePrice')}：${fmtFixed(row.latest_price)}`,
    `${$t('page.aStock.marketOverview.high')}：${fmtFixed(row.high)}`,
    `${$t('page.aStock.marketOverview.low')}：${fmtFixed(row.low)}`,
    `<span style="color:${pctColor}">${$t('page.aStock.marketOverview.changePct')}：${fmtPctText(row.change_pct)}</span>`,
    `${$t('page.aStock.marketOverview.volume')}：${fmtVolume(row.volume)}`,
    `${$t('page.aStock.marketOverview.turnover')}：${fmtMoney(row.turnover)}`
  ];
  return lines.join('<br/>');
}

const { domRef, updateOptions } = useEcharts<ECOption>(() => ({
  tooltip: {
    trigger: 'axis' as const,
    axisPointer: { type: 'cross' as const },
    formatter: formatTooltip
  },
  grid: [
    { left: 12, right: 16, top: 16, height: '58%', containLabel: true },
    { left: 12, right: 16, top: '74%', height: '12%', containLabel: true }
  ],
  xAxis: [
    {
      type: 'category' as const,
      gridIndex: 0,
      data: [],
      axisLabel: { show: false },
      axisTick: { show: false }
    },
    {
      type: 'category' as const,
      gridIndex: 1,
      data: [],
      axisLabel: { fontSize: 10 },
      axisTick: { show: false }
    }
  ],
  yAxis: [
    { type: 'value' as const, gridIndex: 0, scale: true, splitNumber: 4 },
    {
      type: 'value' as const,
      gridIndex: 1,
      scale: true,
      splitNumber: 2,
      axisLabel: { show: false },
      splitLine: { show: false }
    }
  ],
  dataZoom: [
    { type: 'inside' as const, xAxisIndex: [0, 1], start: 50, end: 100 },
    { type: 'slider' as const, xAxisIndex: [0, 1], start: 50, end: 100, height: 18, bottom: 6 }
  ],
  series: [
    {
      name: $t('page.aStock.marketOverview.trend'),
      type: 'candlestick' as const,
      data: [],
      itemStyle: {
        color: STOCK_UP_COLOR,
        color0: STOCK_DOWN_COLOR,
        borderColor: STOCK_UP_COLOR,
        borderColor0: STOCK_DOWN_COLOR
      }
    },
    {
      name: $t('page.aStock.marketOverview.volume'),
      type: 'bar' as const,
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: []
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
      // K 线需要完整 OHLC，个别兜底源缺开盘价/最高最低的行直接跳过
      const rows = historyData.value.filter(
        d => d.open !== null && d.latest_price !== null && d.high !== null && d.low !== null
      );
      chartRows.value = rows;
      const dates = rows.map(d => d.record_date);
      const kData = rows.map(d => [d.open, d.latest_price, d.low, d.high]);
      const volData = rows.map(d => ({
        value: d.volume ?? 0,
        itemStyle: { color: (d.change_pct ?? 0) >= 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR }
      }));
      await updateOptions(() => ({
        xAxis: [
          { type: 'category' as const, gridIndex: 0, data: dates, axisLabel: { show: false }, axisTick: { show: false } },
          { type: 'category' as const, gridIndex: 1, data: dates, axisLabel: { fontSize: 10 }, axisTick: { show: false } }
        ],
        series: [
          {
            name: $t('page.aStock.marketOverview.trend'),
            type: 'candlestick' as const,
            data: kData,
            itemStyle: {
              color: STOCK_UP_COLOR,
              color0: STOCK_DOWN_COLOR,
              borderColor: STOCK_UP_COLOR,
              borderColor0: STOCK_DOWN_COLOR
            }
          },
          {
            name: $t('page.aStock.marketOverview.volume'),
            type: 'bar' as const,
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: volData
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
        <span class="font-600">{{ props.title || $t('page.aStock.marketOverview.trend') }}</span>
        <NSelect
          v-model:value="selectedIndex"
          :options="indexOptions.map(o => ({ label: `${o.index_name} (${o.index_code})`, value: o.index_code }))"
          size="small"
          class="w-240px"
          @update:value="loadHistory"
        />
        <template v-if="latestItem">
          <NTag :style="{ color: latestColor }" size="small" :bordered="false">
            {{ fmtFixed(latestItem.latest_price) }}
          </NTag>
          <span class="text-13px" :style="{ color: latestColor }">
            {{ fmtPctText(latestItem.change_pct) }}
          </span>
        </template>
      </NSpace>
    </template>
    <div ref="domRef" class="h-480px w-full" />
  </NCard>
</template>
