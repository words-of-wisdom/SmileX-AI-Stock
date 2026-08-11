import { request } from '../request';

/** ==================== 行业/概念板块 API ==================== */

/** get board list */
export function fetchGetBoardList(params: Api.StockBoard.BoardListParams) {
  return request<Api.StockBoard.BoardDailyItem[]>({
    url: '/admin/stock/board/list',
    method: 'get',
    params
  });
}

/** get board history */
export function fetchGetBoardHistory(
  boardType: Api.StockBoard.BoardType,
  boardCode: string,
  days?: number
) {
  return request<Api.StockBoard.BoardHistoryItem[]>({
    url: '/admin/stock/board/history',
    method: 'get',
    params: { board_type: boardType, board_code: boardCode, days: days || 30 }
  });
}

/** get available board dates */
export function fetchGetBoardDates(boardType: Api.StockBoard.BoardType) {
  return request<string[]>({
    url: '/admin/stock/board/dates',
    method: 'get',
    params: { board_type: boardType }
  });
}

/** manually trigger board sync */
export function fetchSyncBoard(boardType: Api.StockBoard.BoardType = 'industry') {
  return request<{ fetched: number; saved: number; board_type: string }>({
    url: '/admin/stock/board/sync',
    method: 'post',
    params: { board_type: boardType }
  });
}
