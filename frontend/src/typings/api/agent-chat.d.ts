declare namespace Api {
  namespace AgentChat {
    /** SSE 事件类型 */
    type SSEEventType = 'token' | 'tool_call' | 'tool_result' | 'done' | 'error';

    /** SSE 事件 */
    interface SSEEvent {
      type: SSEEventType;
      /** token 事件的文字增量 */
      content?: string;
      /** tool_call / tool_result 的工具调用 ID */
      id?: string;
      /** tool_call / tool_result 的工具名称 */
      name?: string;
      /** tool_call 的工具参数 */
      arguments?: Record<string, any>;
      /** tool_result 的执行结果 */
      result?: any;
      /** error 事件的错误信息 */
      message?: string;
    }

    /** 消息角色 */
    type MessageRole = 'system' | 'user' | 'assistant';

    /** 工具调用记录（用于前端展示） */
    interface ToolCallRecord {
      id: string;
      name: string;
      arguments: Record<string, any>;
      result?: any;
    }

    /** 对话消息 */
    interface ChatMessage {
      role: MessageRole;
      content: string;
      /** assistant 消息携带的工具调用列表（用于前端展示） */
      tool_calls?: ToolCallRecord[];
    }

    /** 对话请求 */
    interface ChatRequest {
      /** 功能场景编码，决定使用哪个模型 */
      function_code: string;
      messages: ChatMessage[];
      stream: boolean;
    }

    /** 流式回调 */
    interface StreamCallbacks {
      onToken: (text: string) => void;
      onToolCall?: (id: string, name: string, args: Record<string, any>) => void;
      onToolResult?: (id: string, name: string, result: any) => void;
      onDone?: () => void;
      onError?: (msg: string) => void;
    }

    /** 功能场景选项 */
    interface FunctionOption {
      label: string;
      value: string;
    }
  }
}
