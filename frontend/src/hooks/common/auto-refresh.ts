import dayjs, { type Dayjs } from 'dayjs';
import { onActivated, onDeactivated, onMounted, onUnmounted, ref } from 'vue';

/**
 * 页面数据自动刷新 Hook
 *
 * - 页面挂载 / keep-alive 重新激活时启动定时器，停用 / 卸载时停止，退出页面后定时器不会空转
 * - 定时触发为静默刷新（silent=true），页面可据此跳过 loading 闪烁
 * - 每次刷新成功后更新 lastRefreshTime，供页面展示"最后刷新时间"
 */
interface UseAutoRefreshOptions {
  /** 刷新间隔（毫秒），默认 60 秒 */
  interval?: number;
  /** 定时触发前的闸门：返回 false 跳过本轮刷新（手动调 refresh 不受影响） */
  shouldRefresh?: () => boolean;
}

export function useAutoRefresh(refreshFn: (silent: boolean) => Promise<void> | void, options: UseAutoRefreshOptions = {}) {
  const { interval = 60_000, shouldRefresh } = options;
  /** 最近一次刷新完成时间 */
  const lastRefreshTime = ref<Dayjs | null>(null);

  let timer: ReturnType<typeof setInterval> | null = null;
  /** 上一次刷新未结束时跳过本次触发，避免定时器并发请求 */
  let refreshing = false;

  async function refresh(silent = false) {
    if (refreshing) return;
    refreshing = true;
    try {
      await refreshFn(silent);
      lastRefreshTime.value = dayjs();
    } finally {
      refreshing = false;
    }
  }

  function stopTimer() {
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  }

  function startTimer() {
    stopTimer();
    timer = setInterval(() => {
      if (shouldRefresh && !shouldRefresh()) return;
      void refresh(true);
    }, interval);
  }

  onMounted(startTimer);
  onActivated(startTimer);
  onDeactivated(stopTimer);
  onUnmounted(stopTimer);

  return { lastRefreshTime, refresh, stopTimer };
}
