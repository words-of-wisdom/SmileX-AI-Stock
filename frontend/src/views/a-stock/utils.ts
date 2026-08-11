import dayjs from 'dayjs';

/**
 * 是否处于 A 股行情自动刷新时段
 *
 * 覆盖盘中交易时段（09:25-11:35 / 12:55-15:00），并预留收盘后缓冲到 15:40：
 * 收盘后同步任务在 15:30-15:35 落库，缓冲时段内的最后一轮定时刷新能保证拿到完整收盘数据；
 * 时段之外（含周末）页面只保留手动刷新，不再定时轮询。
 * 法定节假日未做日历判断，落在工作日即视为可刷新（多读一次静态快照无副作用）。
 */
export function isStockAutoRefreshTime(): boolean {
  const now = dayjs();
  const day = now.day();
  if (day === 0 || day === 6) return false;
  const minutes = now.hour() * 60 + now.minute();
  return (minutes >= 565 && minutes <= 695) || (minutes >= 775 && minutes <= 940);
}

/** A 股涨跌色：红涨绿跌 */
export const STOCK_UP_COLOR = '#f5222d';
export const STOCK_DOWN_COLOR = '#52c41a';
export const STOCK_FLAT_COLOR = '#8c8c8c';

/** 按涨跌取值对应的颜色（红涨绿跌，无值/持平取灰色） */
export function stockChangeColor(val: number | null | undefined): string {
  if (val === null || val === undefined || val === 0) return STOCK_FLAT_COLOR;
  return val > 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR;
}

/** 定点格式化，无值显示 "-" */
export function fmtFixed(val: number | null | undefined, digits = 2): string {
  if (val === null || val === undefined) return '-';
  return val.toFixed(digits);
}

/** 金额格式化（元 → 万/亿），无值显示 "-" */
export function fmtMoney(val: number | null | undefined): string {
  if (val === null || val === undefined) return '-';
  const abs = Math.abs(val);
  if (abs >= 100000000) return `${(val / 100000000).toFixed(2)}亿`;
  if (abs >= 10000) return `${(val / 10000).toFixed(1)}万`;
  return val.toFixed(0);
}

/** 带正负号的金额格式化（净流入类，正数补 "+"） */
export function fmtSignedMoney(val: number | null | undefined): string {
  if (val === null || val === undefined) return '-';
  const text = fmtMoney(val);
  return val > 0 ? `+${text}` : text;
}

/** 成交量格式化（手 → 万手/亿手），无值显示 "-" */
export function fmtVolume(val: number | null | undefined): string {
  if (val === null || val === undefined) return '-';
  const abs = Math.abs(val);
  if (abs >= 100000000) return `${(val / 100000000).toFixed(2)}亿手`;
  if (abs >= 10000) return `${(val / 10000).toFixed(0)}万手`;
  return val.toFixed(0);
}
