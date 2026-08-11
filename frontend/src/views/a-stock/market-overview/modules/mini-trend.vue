<script setup lang="ts">
import { watch } from 'vue';
import { useEcharts } from '@/hooks/common/echarts';
import type { ECOption } from '@/hooks/common/echarts';
import { $t } from '@/locales';
import { STOCK_DOWN_COLOR, STOCK_UP_COLOR } from '../../utils';

interface Props {
  /** 历史数据（按日期升序），渲染为迷你收盘走势 */
  data: Api.StockMarket.MarketIndexHistoryItem[];
}

const props = defineProps<Props>();

const { domRef, updateOptions } = useEcharts<ECOption>(
  () => ({
    grid: { left: 0, right: 0, top: 2, bottom: 2 },
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, show: false, boundaryGap: false, data: [] },
    yAxis: { type: 'value' as const, show: false, scale: true },
    series: [
      {
        name: $t('page.aStock.marketOverview.closePrice'),
        type: 'line' as const,
        data: [],
        showSymbol: false,
        smooth: true,
        lineStyle: { width: 1.5 },
        areaStyle: { opacity: 0.12 }
      }
    ]
  }),
  // 迷你图不展示加载遮罩，避免 7 张卡片同时闪烁
  { onRender: () => {}, onUpdated: () => {} }
);

async function renderData() {
  const items = props.data;
  if (!items.length) return;
  const dates = items.map(d => d.record_date);
  const prices = items.map(d => d.latest_price);
  const first = prices.find(p => p !== null && p !== undefined) ?? null;
  const last = [...prices].reverse().find(p => p !== null && p !== undefined) ?? null;
  // 区间首尾收盘价定涨跌色，与卡片红涨绿跌一致
  const color = first !== null && last !== null && last < first ? STOCK_DOWN_COLOR : STOCK_UP_COLOR;
  await updateOptions(() => ({
    xAxis: { type: 'category' as const, show: false, boundaryGap: false, data: dates },
    series: [
      {
        name: $t('page.aStock.marketOverview.closePrice'),
        type: 'line' as const,
        data: prices,
        showSymbol: false,
        smooth: true,
        lineStyle: { width: 1.5, color },
        areaStyle: { opacity: 0.12, color }
      }
    ]
  }));
}

watch(() => props.data, renderData, { immediate: true });
</script>

<template>
  <div ref="domRef" class="h-40px w-full" :title="$t('page.aStock.marketOverview.miniTrend')" />
</template>
