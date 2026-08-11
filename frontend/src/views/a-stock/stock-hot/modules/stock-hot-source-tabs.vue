<script setup lang="ts">
import { computed } from 'vue';

defineOptions({
  name: 'StockHotSourceTabs'
});

const props = defineProps<{
  sources: Api.StockHot.StockHotSourceItem[];
  active: string;
}>();

const emit = defineEmits<{
  (e: 'select', source: string): void;
}>();

const groupList = computed(() => {
  const map = new Map<string, Api.StockHot.StockHotSourceItem[]>();
  for (const s of props.sources) {
    const g = s.group || '其他';
    if (!map.has(g)) map.set(g, []);
    map.get(g)!.push(s);
  }
  return Array.from(map.entries()).map(([group, items]) => ({ group, items }));
});
</script>

<template>
  <NCard :bordered="false" size="small" class="card-wrapper">
    <template v-for="g in groupList" :key="g.group">
      <div class="source-group">
        <span class="source-group-label">{{ g.group }}</span>
        <div class="source-items">
          <button
            v-for="s in g.items"
            :key="s.source"
            type="button"
            class="source-item"
            :class="{ 'source-item--active': active === s.source }"
            @click="emit('select', s.source)"
          >
            {{ s.source_name }}
            <span v-if="s.count > 0" class="source-item-count">{{ s.count }}</span>
          </button>
        </div>
      </div>
    </template>
  </NCard>
</template>

<style scoped>
.source-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-group + .source-group {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.source-group-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: rgba(var(--base-text-color), 0.45);
  width: 60px;
}

.source-items {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.source-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  font-size: 13px;
  color: rgba(var(--base-text-color), 0.65);
  background: transparent;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  outline: none;
}

.source-item:hover {
  border-color: rgba(var(--primary-color), 0.4);
  color: rgb(var(--primary-color));
}

.source-item--active {
  border-color: rgb(var(--primary-color));
  background: rgba(var(--primary-color), 0.08);
  color: rgb(var(--primary-color));
  font-weight: 500;
}

.source-item--active:hover {
  border-color: rgb(var(--primary-color));
  background: rgba(var(--primary-color), 0.12);
  color: rgb(var(--primary-color));
}

.source-item-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 500;
  color: #fff;
  background: rgba(var(--primary-color), 0.5);
}

html.dark .source-group + .source-group {
  border-top-color: rgba(255, 255, 255, 0.08);
}

html.dark .source-item {
  border-color: rgba(255, 255, 255, 0.1);
}
</style>
