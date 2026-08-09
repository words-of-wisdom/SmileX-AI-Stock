<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { $t } from '@/locales';

defineOptions({
  name: 'NewsSourceTabs'
});

const props = defineProps<{
  sources: Api.News.NewsSourceItem[];
}>();

const emit = defineEmits<{
  (e: 'select', payload: { source: string | null; group: string | null }): void;
}>();

/** 求多字符串的最长公共前缀（不足 2 字返回空） */
function commonPrefix(names: string[]): string {
  if (names.length < 2) return '';
  const sorted = [...names].sort();
  const a = sorted[0];
  const b = sorted[sorted.length - 1];
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i++;
  const prefix = a.slice(0, i);
  return prefix.length >= 2 ? prefix : '';
}

/** 按分组聚合，保持插入顺序，并计算组内公共前缀用于二级简化显示 */
const groupList = computed(() => {
  const map = new Map<string, Api.News.NewsSourceItem[]>();
  for (const s of props.sources) {
    const g = s.group || '其他';
    if (!map.has(g)) map.set(g, []);
    map.get(g)!.push(s);
  }
  return Array.from(map.entries()).map(([group, items]) => {
    const prefix = commonPrefix(items.map(i => i.source_name));
    return {
      group,
      items,
      count: items.reduce((acc, s) => acc + s.count, 0),
      prefix
    };
  });
});

/** 第一级选中项：null = 全部 */
const activeGroup = ref<string | null>(null);
/** 第二级选中来源 key：null = 该分类全部 */
const activeSource = ref<string | null>(null);

/** 当前展开的分组来源列表 */
const activeGroupData = computed(() => {
  if (!activeGroup.value) return null;
  return groupList.value.find(g => g.group === activeGroup.value) ?? null;
});

/** 点击"全部来源" */
function clickAll() {
  activeGroup.value = null;
  activeSource.value = null;
  emit('select', { source: null, group: null });
}

/** 点击第一级分组：统一按分组过滤 */
function clickGroup(group: string) {
  activeGroup.value = group;
  activeSource.value = null;
  emit('select', { source: null, group });
}

/** 选择二级来源 */
function selectSource(key: string | null) {
  activeSource.value = key;
  emit('select', { source: key, group: activeGroup.value });
}

/** 二级标签简化显示：去掉组内公共前缀 */
function shortLabel(prefix: string, name: string): string {
  if (prefix && name.startsWith(prefix)) {
    const rest = name.slice(prefix.length);
    return rest || name;
  }
  return name;
}

/** 外部 sources 刷新时重置选中 */
watch(
  () => props.sources,
  () => {
    activeGroup.value = null;
    activeSource.value = null;
  }
);
</script>

<template>
  <NCard :bordered="false" size="small" class="card-wrapper">
    <!-- 第一级 -->
    <div class="news-tab-row">
      <span
        class="news-tab-item"
        :class="{ 'news-tab-item--active': activeGroup === null }"
        @click="clickAll"
      >
        {{ $t('page.news.allSources') }}
      </span>
      <span
        v-for="g in groupList"
        :key="g.group"
        class="news-tab-item"
        :class="{ 'news-tab-item--active': activeGroup === g.group }"
        @click="clickGroup(g.group)"
      >
        {{ g.group }}
        <NTag :bordered="false" size="tiny" round class="news-tab-count">{{ g.count }}</NTag>
      </span>
    </div>
    <!-- 第二级：选中多来源分组后展开 -->
    <div v-if="activeGroupData && activeGroupData.items.length > 1" class="news-tab-row news-tab-row--sub">
      <span
        class="news-tab-item news-tab-item--sub"
        :class="{ 'news-tab-item--active': activeSource === null }"
        @click="selectSource(null)"
      >
        全部
      </span>
      <span
        v-for="s in activeGroupData.items"
        :key="s.source"
        class="news-tab-item news-tab-item--sub"
        :class="{ 'news-tab-item--active': activeSource === s.source }"
        @click="selectSource(s.source)"
      >
        {{ shortLabel(activeGroupData.prefix, s.source_name) }}
        <NTag :bordered="false" size="tiny" round class="news-tab-count">{{ s.count }}</NTag>
      </span>
    </div>
  </NCard>
</template>

<style scoped>
.news-tab-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.news-tab-row--sub {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.09);
}

.news-tab-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: var(--n-border-radius, 4px);
  font-size: 13px;
  color: rgb(var(--base-text-color));
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.news-tab-item:hover {
  background: rgba(var(--primary-color), 0.1);
  color: rgb(var(--primary-color));
}

.news-tab-item--active {
  background: rgb(var(--primary-color));
  color: #fff;
}

.news-tab-item--active:hover {
  background: rgb(var(--primary-color));
  color: #fff;
}

.news-tab-item--sub {
  font-size: 12px;
  padding: 3px 10px;
}

.news-tab-count {
  font-size: 11px;
}

html.dark .news-tab-row--sub {
  border-top-color: rgba(255, 255, 255, 0.09);
}
</style>
