<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import { NButton, NEmpty, NInput, NSelect, NSpace, NSpin, useMessage } from 'naive-ui';
import MarkdownIt from 'markdown-it';
import { streamAgentChat } from '@/service/api';
import ToolCallCard from './modules/tool-call-card.vue';

defineOptions({ name: 'AiChat' });

const message = useMessage();
const md = new MarkdownIt({ breaks: true, linkify: true, html: false });

// ==================== 状态 ====================

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: Api.AgentChat.ToolCallRecord[];
  pending?: boolean; // 正在流式生成中
  error?: boolean;
}

const messages = ref<DisplayMessage[]>([]);
const inputText = ref('');
const sending = ref(false);
const scrollContainer = ref<HTMLElement>();
const selectedFunction = ref('chat_qa');
let abortController: AbortController | null = null;

const functionOptions: Api.AgentChat.FunctionOption[] = [
  { label: '对话问答', value: 'chat_qa' },
  { label: '智能选股', value: 'stock_picking' },
  { label: '舆情分析', value: 'sentiment_analysis' },
  { label: '新闻摘要', value: 'news_summary' },
  { label: '趋势预测', value: 'trend_prediction' }
];

const quickPrompts = [
  '今天大盘走势如何？',
  '当前涨停的股票有哪些？连板数最高的是？',
  '哪个行业板块今天涨幅最大？',
  '主力资金最近几天是净流入还是净流出？',
  '最新的财经新闻有哪些？'
];

// ==================== 渲染 ====================

function renderMarkdown(text: string): string {
  return md.render(text || '');
}

// ==================== 滚动 ====================

function scrollToBottom() {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
    }
  });
}

watch(() => messages.value.length, scrollToBottom);
watch(
  () => messages.value[messages.value.length - 1]?.content,
  scrollToBottom
);

// ==================== 发送消息 ====================

function genId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function handleSend() {
  const text = inputText.value.trim();
  if (!text || sending.value) return;

  // 构造对话历史（发送给后端的）
  const history: Api.AgentChat.ChatMessage[] = messages.value
    .filter(m => !m.error && m.content)
    .map(m => ({
      role: m.role,
      content: m.content,
      // 后端只需要纯文本内容，tool_calls 由后端内部管理
    }));
  history.push({ role: 'user', content: text });

  // UI: 添加用户消息
  messages.value.push({ id: genId(), role: 'user', content: text });
  inputText.value = '';

  // UI: 添加 assistant 占位消息
  const assistantId = genId();
  const assistantMsg: DisplayMessage = {
    id: assistantId,
    role: 'assistant',
    content: '',
    toolCalls: [],
    pending: true
  };
  messages.value.push(assistantMsg);
  scrollToBottom();

  sending.value = true;
  abortController = new AbortController();

  try {
    await streamAgentChat(
      { function_code: selectedFunction.value, messages: history, stream: true },
      {
        onToken: (token: string) => {
          const msg = messages.value.find(m => m.id === assistantId);
          if (msg) {
            msg.content += token;
          }
        },
        onToolCall: (id: string, name: string, args: Record<string, any>) => {
          const msg = messages.value.find(m => m.id === assistantId);
          if (msg) {
            if (!msg.toolCalls) msg.toolCalls = [];
            msg.toolCalls.push({ id, name, arguments: args });
          }
        },
        onToolResult: (id: string, name: string, result: any) => {
          const msg = messages.value.find(m => m.id === assistantId);
          if (msg && msg.toolCalls) {
            const tc = msg.toolCalls.find(t => t.id === id);
            if (tc) {
              tc.result = result;
            }
          }
        },
        onDone: () => {
          const msg = messages.value.find(m => m.id === assistantId);
          if (msg) {
            msg.pending = false;
          }
        },
        onError: (msg: string) => {
          const target = messages.value.find(m => m.id === assistantId);
          if (target) {
            target.pending = false;
            target.error = true;
            target.content += `\n\n> ❌ ${msg}`;
          }
          message.error(msg);
        }
      },
      abortController.signal
    );
  } catch (error: any) {
    const target = messages.value.find(m => m.id === assistantId);
    if (target) {
      target.pending = false;
      if (target.content === '') {
        target.error = true;
        target.content = `> ❌ 请求失败: ${error?.message || '未知错误'}`;
      }
    }
  } finally {
    sending.value = false;
    abortController = null;
  }
}

function handleStop() {
  if (abortController) {
    abortController.abort();
    abortController = null;
    sending.value = false;
    // 标记最后一条消息为已完成
    const last = messages.value[messages.value.length - 1];
    if (last && last.pending) {
      last.pending = false;
      last.content += '\n\n> ⏹ 已停止生成';
    }
  }
}

function handleClear() {
  messages.value = [];
}

function handleQuickPrompt(prompt: string) {
  inputText.value = prompt;
}

function onKeyDown(e: KeyboardEvent) {
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  }
}

onUnmounted(() => {
  if (abortController) {
    abortController.abort();
  }
});

const hasMessages = computed(() => messages.value.length > 0);
</script>

<template>
  <div class="h-full flex-col-stretch">
    <!-- 顶部工具栏 -->
    <div class="chat-toolbar flex items-center justify-between px-16px py-12px">
      <NSpace align="center" :size="12">
        <NSelect
          v-model:value="selectedFunction"
          :options="functionOptions"
          size="small"
          style="width: 140px"
        />
        <span class="text-12px text-gray-400">{{ functionOptions.find(f => f.value === selectedFunction)?.label }}</span>
      </NSpace>
      <NButton size="small" quaternary :disabled="sending" @click="handleClear">
        清空对话
      </NButton>
    </div>

    <!-- 消息区域 -->
    <div ref="scrollContainer" class="chat-messages flex-1 overflow-y-auto px-16px">
      <!-- 空状态 -->
      <div v-if="!hasMessages" class="empty-state">
        <NEmpty description="开始与 AI 助手对话，它可以帮助你分析A股市场数据">
          <template #extra>
            <div class="quick-prompts">
              <div class="text-12px text-gray-400 mb-8px">试试这些问题：</div>
              <div v-for="prompt in quickPrompts" :key="prompt" class="quick-prompt" @click="handleQuickPrompt(prompt)">
                {{ prompt }}
              </div>
            </div>
          </template>
        </NEmpty>
      </div>

      <!-- 消息列表 -->
      <div v-else class="message-list py-16px">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-item"
          :class="msg.role"
        >
          <div class="message-avatar">
            {{ msg.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div class="message-body">
            <!-- 工具调用卡片 -->
            <template v-if="msg.toolCalls && msg.toolCalls.length > 0">
              <ToolCallCard
                v-for="tc in msg.toolCalls"
                :key="tc.id"
                :tool-call="tc"
              />
            </template>

            <!-- 消息内容 -->
            <div
              v-if="msg.content"
              class="message-content"
              :class="{ error: msg.error }"
              v-html="renderMarkdown(msg.content)"
            />

            <!-- 加载指示器 -->
            <div v-if="msg.pending && !msg.content && !(msg.toolCalls && msg.toolCalls.length > 0)" class="message-loading">
              <NSpin size="small" />
              <span class="ml-8px text-12px text-gray-400">思考中...</span>
            </div>

            <!-- 打字光标 -->
            <span v-if="msg.pending && msg.content" class="typing-cursor">▋</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input-area px-16px py-12px">
      <div class="input-wrapper">
        <NInput
          v-model:value="inputText"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 5 }"
          placeholder="输入你的问题...（Ctrl+Enter 发送）"
          :disabled="sending"
          @keydown="onKeyDown"
        />
        <div class="flex justify-end mt-8px gap-8px">
          <template v-if="sending">
            <NButton size="small" type="error" ghost @click="handleStop">
              停止生成
            </NButton>
          </template>
          <template v-else>
            <NButton
              size="small"
              type="primary"
              :disabled="!inputText.trim()"
              @click="handleSend"
            >
              发送
            </NButton>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-toolbar {
  border-bottom: 1px solid var(--n-border-color, #efeff5);
}

.chat-messages {
  scroll-behavior: smooth;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.quick-prompts {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.quick-prompt {
  padding: 6px 16px;
  border: 1px solid var(--n-border-color, #e0e0e6);
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-prompt:hover {
  border-color: rgb(var(--primary-color));
  color: rgb(var(--primary-color));
  background: rgba(var(--primary-color), 0.06);
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border-radius: 8px;
  background: var(--n-color-target, rgba(0, 0, 0, 0.04));
}

.message-item.user .message-avatar {
  order: 2;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-body {
  max-width: 75%;
  display: flex;
  flex-direction: column;
}

.message-item.user .message-body {
  align-items: flex-end;
}

.message-content {
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--n-color-target, rgba(0, 0, 0, 0.04));
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
}

.message-item.assistant .message-content {
  background: var(--card-color, #fff);
  border: 1px solid var(--n-border-color, #efeff5);
}

.message-content.error {
  color: #d03050;
}

.message-content :deep(p) {
  margin: 0 0 8px;
}

.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}

.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid var(--n-border-color, #e0e0e6);
  padding: 4px 10px;
}

.message-content :deep(code) {
  font-family: 'Fira Code', monospace;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 13px;
}

.message-loading {
  display: flex;
  align-items: center;
  padding: 10px 16px;
}

.typing-cursor {
  display: inline-block;
  animation: blink 1s steps(2) infinite;
  color: rgb(var(--primary-color));
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.chat-input-area {
  border-top: 1px solid var(--n-border-color, #efeff5);
}

.input-wrapper {
  max-width: 900px;
  margin: 0 auto;
}
</style>
