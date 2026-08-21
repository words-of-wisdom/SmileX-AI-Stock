/**
 * AI 分析模块共享工具（大盘分析/板块分析页面共用）
 */

/**
 * 金额单位统一格式化（按数量级分级）：
 * ≥1亿 → X.XX亿；≥1千万 → X.XX千万；≥1万 → X.X万；其余整数原样
 * 负数（净流出）按绝对值分级，保留负号
 */
export function fmtAmountCn(val: number | null | undefined): string {
  if (val === null || val === undefined) return '-';
  const abs = Math.abs(val);
  if (abs >= 1e8) return `${(val / 1e8).toFixed(2)}亿`;
  if (abs >= 1e7) return `${(val / 1e7).toFixed(2)}千万`;
  if (abs >= 1e4) return `${(val / 1e4).toFixed(1)}万`;
  return val.toFixed(0);
}
