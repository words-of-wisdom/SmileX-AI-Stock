import { request } from '../request';

/** ==================== 券商研报 API ==================== */

/** paged research report list (filters: stock/keyword/org/rating/date range) */
export function fetchGetResearchReports(params: Api.Research.ReportQuery) {
  return request<Api.Common.PaginatingQueryRecord<Api.Research.ResearchReportItem>>({
    url: '/admin/research/reports',
    method: 'get',
    params: {
      page: params.page,
      page_size: params.pageSize,
      stock_code: params.stockCode || undefined,
      keyword: params.keyword || undefined,
      org_name: params.orgName || undefined,
      rating: params.rating || undefined,
      start_date: params.startDate || undefined,
      end_date: params.endDate || undefined
    }
  });
}

/** research report overview stats (last N days) */
export function fetchGetResearchStats(days = 30) {
  return request<Api.Research.ResearchStats>({
    url: '/admin/research/reports/stats',
    method: 'get',
    params: { days }
  });
}

/** research report stats grouped by stock within a time window */
export function fetchGetResearchStockStats(days: number, stockCode?: string) {
  return request<Api.Research.ResearchStockStatItem[]>({
    url: '/admin/research/reports/stock-stats',
    method: 'get',
    params: { days, stock_code: stockCode || undefined }
  });
}

/** manually trigger research report sync (optional stock codes) */
export function fetchSyncResearchReports(stockCodes: string[] = []) {
  return request<Api.Research.ResearchSyncResult>({
    url: '/admin/research/reports/sync',
    method: 'post',
    data: { stock_codes: stockCodes }
  });
}
