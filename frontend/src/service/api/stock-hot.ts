import { request } from '../request';

/** ==================== 股票热榜 API ==================== */

/** get stock hot source list */
export function fetchGetStockHotSources() {
  return request<Api.StockHot.StockHotSourceItem[]>({
    url: '/admin/stock/stock-hot/sources',
    method: 'get'
  });
}

/** get stock hot rank list */
export function fetchGetStockHotList(source: string, date?: string | null) {
  return request<Api.StockHot.StockHotRankItem[]>({
    url: '/admin/stock/stock-hot/list',
    method: 'get',
    params: { source, date: date || undefined }
  });
}

/** get available dates */
export function fetchGetStockHotDates(source: string) {
  return request<string[]>({
    url: '/admin/stock/stock-hot/dates',
    method: 'get',
    params: { source }
  });
}

/** get single stock rank history */
export function fetchGetStockHotHistory(source: string, stockCode: string, days?: number) {
  return request<Api.StockHot.StockHotHistoryItem[]>({
    url: '/admin/stock/stock-hot/history',
    method: 'get',
    params: { source, stock_code: stockCode, days: days || 30 }
  });
}

/** manually trigger stock hot sync */
export function fetchSyncStockHot() {
  return request<{ fetched: number; saved: number; failed_sources: { source: string; error: string }[] }>({
    url: '/admin/stock/stock-hot/sync',
    method: 'post'
  });
}
