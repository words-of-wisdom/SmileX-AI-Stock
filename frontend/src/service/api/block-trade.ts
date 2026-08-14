import { request } from '../request';

/** ==================== 大宗交易（暗盘） API ==================== */

/** get block trade sources overview */
export function fetchGetBlockTradeSources() {
  return request<Api.BlockTrade.BlockTradeSourceItem[]>({
    url: '/admin/stock/block-trade/sources',
    method: 'get'
  });
}

/** get block trade daily list */
export function fetchGetBlockTradeDailyList(date?: string | null) {
  return request<Api.BlockTrade.BlockTradeDailyItem[]>({
    url: '/admin/stock/block-trade/daily-list',
    method: 'get',
    params: { date: date || undefined }
  });
}

/** get block trade active list */
export function fetchGetBlockTradeActiveList(statWindow: Api.BlockTrade.StatWindow) {
  return request<Api.BlockTrade.BlockTradeActiveItem[]>({
    url: '/admin/stock/block-trade/active-list',
    method: 'get',
    params: { stat_window: statWindow }
  });
}

/** get available dates (daily board) */
export function fetchGetBlockTradeDates() {
  return request<string[]>({
    url: '/admin/stock/block-trade/dates',
    method: 'get'
  });
}

/** get single stock rank history */
export function fetchGetBlockTradeHistory(stockCode: string, days?: number) {
  return request<Api.BlockTrade.BlockTradeHistoryItem[]>({
    url: '/admin/stock/block-trade/history',
    method: 'get',
    params: { stock_code: stockCode, days: days || 30 }
  });
}

/** manually trigger block trade sync */
export function fetchSyncBlockTrade() {
  return request<{
    daily: { fetched: number; saved: number; record_date: string } | null;
    active: { fetched: number; saved: number; stat_window: string }[];
    failed: { sub_board: string; stat_window?: string; error: string }[];
  }>({
    url: '/admin/stock/block-trade/sync',
    method: 'post'
  });
}
