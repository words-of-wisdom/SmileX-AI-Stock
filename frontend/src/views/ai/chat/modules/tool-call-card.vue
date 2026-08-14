<script setup lang="ts">
import { computed, ref } from 'vue';
import { NCollapse, NCollapseItem, NTag } from 'naive-ui';

const props = defineProps<{
  toolCall: Api.AgentChat.ToolCallRecord;
}>();

const expanded = ref<string[]>([]);

const toolLabelMap: Record<string, string> = {
  get_hot_stocks: '股票热榜',
  get_market_indices: '大盘指数',
  get_market_fund_flow: '资金流向',
  get_board_ranking: '板块排行',
  get_limit_up_stocks: '涨停股池',
  get_latest_news: '最新新闻'
};

const toolName = computed(() => toolLabelMap[props.toolCall.name] || props.toolCall.name);
const hasResult = computed(() => props.toolCall.result !== undefined);
const hasError = computed(() => hasResult.value && props.toolCall.result?.error);

const argsPreview = computed(() => {
  const args = props.toolCall.arguments;
  if (!args || Object.keys(args).length === 0) return '无参数';
  return Object.entries(args)
    .filter(([, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ');
});

const resultPreview = computed(() => {
  if (!hasResult.value) return '';
  if (hasError.value) return `错误: ${props.toolCall.result.error}`;
  const r = props.toolCall.result;
  if (r.items) return `返回 ${r.items.length} 条数据`;
  if (r.sources) {
    const counts = Object.entries(r.sources).map(([k, v]: any) => `${k}: ${v.items?.length || 0}条`);
    return counts.join(', ');
  }
  return '执行成功';
});
</script>

<template>
  <div class="tool-call-card">
    <NCollapse v-model:expanded-names="expanded" :default-expanded-names="[]">
      <NCollapseItem name="tool">
        <template #header>
          <div class="flex items-center gap-6px">
            <span class="text-13px font-500">{{ toolName }}</span>
            <NTag size="small" :type="hasError ? 'error' : hasResult ? 'success' : 'info'" round>
              {{ hasError ? '失败' : hasResult ? '完成' : '执行中' }}
            </NTag>
            <span v-if="argsPreview" class="text-12px text-gray-400">{{ argsPreview }}</span>
            <span v-if="resultPreview" class="text-12px" :class="hasError ? 'text-red-400' : 'text-green-500'">
              · {{ resultPreview }}
            </span>
          </div>
        </template>
        <div class="tool-detail">
          <div class="mb-8px">
            <span class="detail-label">工具名称:</span>
            <code class="detail-value">{{ toolCall.name }}</code>
          </div>
          <div class="mb-8px">
            <span class="detail-label">参数:</span>
            <pre class="detail-code">{{ JSON.stringify(toolCall.arguments, null, 2) }}</pre>
          </div>
          <div v-if="hasResult">
            <span class="detail-label">结果:</span>
            <pre class="detail-code" :class="{ 'text-red-400': hasError }">{{ JSON.stringify(toolCall.result, null, 2).slice(0, 500) }}</pre>
          </div>
        </div>
      </NCollapseItem>
    </NCollapse>
  </div>
</template>

<style scoped>
.tool-call-card {
  border: 1px solid var(--n-border-color, #e0e0e6);
  border-radius: 6px;
  margin: 8px 0;
  overflow: hidden;
}

.tool-detail {
  padding: 8px 12px;
  font-size: 12px;
}

.detail-label {
  color: var(--n-text-color-3, #999);
  font-weight: 500;
  margin-right: 4px;
}

.detail-value {
  font-family: 'Fira Code', monospace;
  background: var(--n-color-target, rgba(0, 0, 0, 0.04));
  padding: 1px 6px;
  border-radius: 3px;
}

.detail-code {
  margin: 4px 0;
  padding: 8px;
  background: var(--n-color-target, rgba(0, 0, 0, 0.04));
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
