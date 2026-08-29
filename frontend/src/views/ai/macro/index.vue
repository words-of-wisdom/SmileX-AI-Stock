<script setup lang="tsx">
/**
 * 宏观指数页：中美 CPI/PPI/M1/M2 等指标最新值卡片 + 历史走势图
 */
import { computed, onMounted, ref, watch } from 'vue';
import {
  NButton,
  NCard,
  NEmpty,
  NGrid,
  NGridItem,
  NSelect,
  NSpace,
  NTab,
  NTabs,
  NTag,
  NText
} from 'naive-ui';
import {
  fetchGetMacroLatest,
  fetchGetMacroSeries,
  fetchSyncMacro
} from '@/service/api';
import { useEcharts } from '@/hooks/common/echarts';
import type { ECOption } from '@/hooks/common/echarts';
import { useAuth } from '@/hooks/business/auth';
import { $t } from '@/locales';

defineOptions({ name: 'AiMacro' });

const UP = '#f5222d';
const DOWN = '#52c41a';
const FLAT = '#8c8c8c';

const { hasAuth } = useAuth();
const canSync = hasAuth('macro:sync');

const country = ref<Api.Macro.CountryType>('CN');
const indicator = ref<Api.Macro.IndicatorCode>('cpi');
const loading = ref(false);
const syncing = ref(false);
const latestItems = ref<Api.Macro.MacroIndicatorItem[]>([]);
const series = ref<Api.Macro.MacroIndicatorItem[]>([]);

/** 当前国家的指标选项（按已有数据动态生成） */
const indicatorOptions = computed(() => {
  const seen = new Map<string, string>();
  for (const it of latestItems.value) {
    if (it.country === country.value && !seen.has(it.indicator_code)) {
      seen.set(it.indicator_code, it.indicator_name);
    }
  }
  return Array.from(seen.entries()).map(([value, label]) => ({ value, label }));
});

/** 最新值卡片（当前国家） */
const cards = computed(() =>
  latestItems.value.filter(it => it.country === country.value)
);

function pctColor(val: number | null | undefined) {
  if (val === null || val === undefined) return FLAT;
  return val > 0 ? UP : val < 0 ? DOWN : FLAT;
}

function fmtPct(val: number | null | undefined) {
  if (val === null || val === undefined) return '-';
  return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
}

const { domRef, updateOptions } = useEcharts<ECOption>(() => ({
  tooltip: { trigger: 'axis' as const },
  grid: { left: 12, right: 16, top: 30, bottom: 30, containLabel: true },
  xAxis: { type: 'category' as const, data: [] },
  yAxis: { type: 'value' as const, scale: true },
  series: [
    {
      name: '',
      type: 'line' as const,
      data: [],
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: '#5470c6' },
      areaStyle: { opacity: 0.08, color: '#5470c6' },
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { type: 'dashed' as const, color: '#8c8c8c' },
        data: [{ yAxis: 0 }]
      }
    }
  ]
}));

function renderChart() {
  const name =
    cards.value.find(c => c.indicator_code === indicator.value)?.indicator_name ?? '';
  const values = series.value.map(it => (it.yoy ?? it.value) ?? null);
  updateOptions(prev => ({
    ...prev,
    series: [
      {
        ...prev.series[0],
        name,
        data: values
      }
    ],
    xAxis: { ...prev.xAxis, data: series.value.map(it => it.period) }
  }));
}

async function loadLatest() {
  const { data, error } = await fetchGetMacroLatest();
  if (!error) latestItems.value = data ?? [];
}

async function loadSeries() {
  loading.value = true;
  try {
    const { data, error } = await fetchGetMacroSeries(country.value, indicator.value, 24);
    if (!error) {
      series.value = data ?? [];
      renderChart();
    }
  } finally {
    loading.value = false;
  }
}

async function onSync() {
  syncing.value = true;
  try {
    const { error } = await fetchSyncMacro();
    if (!error) {
      window.$message?.success($t('page.macro.syncDone'));
      await loadLatest();
      await loadSeries();
    }
  } finally {
    syncing.value = false;
  }
}

function onCountryChange(c: string) {
  country.value = c as Api.Macro.CountryType;
  const first = indicatorOptions.value[0]?.value as Api.Macro.IndicatorCode | undefined;
  if (first && !indicatorOptions.value.find(o => o.value === indicator.value)) {
    indicator.value = first ?? 'cpi';
  }
}

watch(indicator, () => loadSeries());

onMounted(async () => {
  await loadLatest();
  const first = indicatorOptions.value[0]?.value as Api.Macro.IndicatorCode | undefined;
  if (first) indicator.value = first;
  await loadSeries();
});
</script>

<template>
  <div class="min-h-500px h-full flex flex-col gap-12px overflow-auto">
    <NCard :bordered="false" size="small" class="card-wrapper">
      <template #header>
        <div class="flex-y-center gap-8px">
          <span class="text-16px font-500">{{ $t('page.macro.title') }}</span>
          <NText depth="3" class="text-12px">{{ $t('page.macro.subtitle') }}</NText>
        </div>
      </template>
      <template #header-extra>
        <NButton v-if="canSync" size="small" tertiary :loading="syncing" @click="onSync">
          <template #icon><icon-mdi-refresh class="text-icon" /></template>
          {{ $t('page.macro.syncBtn') }}
        </NButton>
      </template>

      <!-- 国家切换 -->
      <NTabs :value="country" type="segment" size="small" class="mb-12px" @update:value="onCountryChange">
        <NTab name="CN">{{ $t('page.macro.countryCN') }}</NTab>
        <NTab name="US">{{ $t('page.macro.countryUS') }}</NTab>
      </NTabs>

      <!-- 最新值卡片 -->
      <NEmpty v-if="!cards.length" class="py-36px" :description="$t('page.macro.emptyTip')" />
      <NGrid v-else :x-gap="12" :y-gap="12" :cols="2" s:cols="3" l:cols="5" responsive="screen">
        <NGridItem v-for="item in cards" :key="`${item.country}-${item.indicator_code}`">
          <div
            class="cursor-pointer rounded-6px border px-12px py-10px"
            :class="item.indicator_code === indicator
              ? 'border-primary-400'
              : 'border-gray-200 dark:border-gray-700'"
            @click="indicator = item.indicator_code as Api.Macro.IndicatorCode"
          >
            <div class="flex items-center justify-between">
              <span class="text-13px font-500">{{ item.indicator_name }}</span>
              <NTag size="tiny" :bordered="false">{{ item.period }}</NTag>
            </div>
            <div class="mt-4px flex items-baseline gap-8px">
              <span
                class="text-20px font-600"
                :style="{ color: pctColor(item.yoy ?? item.value), fontFamily: 'monospace' }"
              >
                {{ fmtPct(item.yoy ?? item.value) }}
              </span>
              <NText depth="3" class="text-12px">
                {{ $t('page.macro.mom') }} {{ fmtPct(item.mom) }}
              </NText>
            </div>
          </div>
        </NGridItem>
      </NGrid>
    </NCard>

    <!-- 历史走势 -->
    <NCard :bordered="false" size="small" class="card-wrapper" :loading="loading">
      <template #header>
        <NSpace align="center" :size="12">
          <span class="text-16px font-500">{{ $t('page.macro.historyTitle') }}</span>
          <NSelect
            :value="indicator"
            :options="indicatorOptions"
            size="small"
            style="width: 200px"
            @update:value="(v: string) => (indicator = v as Api.Macro.IndicatorCode)"
          />
        </NSpace>
      </template>
      <div ref="domRef" class="h-320px w-full" />
    </NCard>
  </div>
</template>

<style scoped></style>
