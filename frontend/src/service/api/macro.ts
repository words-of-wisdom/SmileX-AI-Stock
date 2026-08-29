import { request } from '../request';

/** ==================== 宏观指数 API ==================== */

/** get macro indicator history series (last N periods, period ascending, for charts) */
export function fetchGetMacroSeries(
  country: Api.Macro.CountryType,
  indicator: Api.Macro.IndicatorCode,
  limit = 24
) {
  return request<Api.Macro.MacroIndicatorItem[]>({
    url: '/admin/macro/indicators',
    method: 'get',
    params: { country, indicator, limit }
  });
}

/** get latest value of every country x indicator (for cards) */
export function fetchGetMacroLatest() {
  return request<Api.Macro.MacroIndicatorItem[]>({
    url: '/admin/macro/indicators/latest',
    method: 'get'
  });
}

/** manually trigger macro indicator sync (akshare fetch + upsert) */
export function fetchSyncMacro() {
  return request<Api.Macro.MacroSyncResult>({
    url: '/admin/macro/sync',
    method: 'post'
  });
}
