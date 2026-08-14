import { fetchEventSource } from '@microsoft/fetch-event-source';
import { getAuthorization } from '@/service/request/shared';
import { getServiceBaseURL } from '@/utils/service';
import { getLocale } from '@/locales';

const isHttpProxy = import.meta.env.DEV && import.meta.env.VITE_HTTP_PROXY === 'Y';
const { baseURL } = getServiceBaseURL(import.meta.env, isHttpProxy);

/**
 * Agent 流式对话（SSE）
 *
 * 使用 fetch-event-source 而非原生 EventSource，因为需要：
 * - POST 请求体携带 messages
 * - 自定义 Authorization header
 */
export function streamAgentChat(
  body: Api.AgentChat.ChatRequest,
  callbacks: Api.AgentChat.StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  return fetchEventSource(`${baseURL}/admin/agent/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthorization() || '',
      'Accept-Language': getLocale()
    },
    body: JSON.stringify(body),
    signal,
    async onopen(response) {
      if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
        return;
      }
      throw new Error(`SSE 连接失败: HTTP ${response.status}`);
    },
    onmessage(ev) {
      try {
        const event: Api.AgentChat.SSEEvent = JSON.parse(ev.data);
        switch (event.type) {
          case 'token':
            callbacks.onToken(event.content || '');
            break;
          case 'tool_call':
            callbacks.onToolCall?.(event.id || '', event.name || '', event.arguments || {});
            break;
          case 'tool_result':
            callbacks.onToolResult?.(event.id || '', event.name || '', event.result);
            break;
          case 'done':
            callbacks.onDone?.();
            break;
          case 'error':
            callbacks.onError?.(event.message || '未知错误');
            break;
          default:
            break;
        }
      } catch (e) {
        console.warn('[AgentChat] SSE 消息解析失败:', ev.data, e);
      }
    },
    onerror(err) {
      // 抛出错误会触发重试，这里直接返回错误停止重试
      callbacks.onError?.(err?.message || '网络连接错误');
      throw err;
    }
  });
}
