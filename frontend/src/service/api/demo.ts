import { request } from '../request';

/** ==================== 示例：股票 SDK 简单调用 API ==================== */

/** akshare 示例：获取个股基础信息 */
export function fetchAkshareStockInfo(symbol: string) {
  return request<Api.Demo.StockInfoItem[]>({
    url: '/admin/demo/akshare/stock-info',
    method: 'get',
    params: { symbol }
  });
}

/** Baostock 示例：获取日 K 线数据 */
export function fetchBaostockKline(code: string, days: number) {
  return request<Api.Demo.KlineItem[]>({
    url: '/admin/demo/baostock/kline',
    method: 'get',
    params: { code, days }
  });
}
