import { request } from '../request';

/** ==================== 大盘概览 API ==================== */

/** get market index list */
export function fetchGetMarketIndices(date?: string | null) {
  return request<Api.StockMarket.MarketIndexItem[]>({
    url: '/admin/stock/market/indices',
    method: 'get',
    params: { date: date || undefined }
  });
}

/** get market index options */
export function fetchGetMarketIndexOptions() {
  return request<Api.StockMarket.MarketIndexOption[]>({
    url: '/admin/stock/market/indices/options',
    method: 'get'
  });
}

/** get single index history */
export function fetchGetMarketIndexHistory(indexCode: string, days?: number) {
  return request<Api.StockMarket.MarketIndexHistoryItem[]>({
    url: '/admin/stock/market/indices/history',
    method: 'get',
    params: { index_code: indexCode, days: days || 90 }
  });
}

/** get available market dates */
export function fetchGetMarketDates() {
  return request<string[]>({
    url: '/admin/stock/market/dates',
    method: 'get'
  });
}

/** manually trigger market sync */
export function fetchSyncMarket() {
  return request<{ fetched: number; saved: number }>({
    url: '/admin/stock/market/sync',
    method: 'post'
  });
}
