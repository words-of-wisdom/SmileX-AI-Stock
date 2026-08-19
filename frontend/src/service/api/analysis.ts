import { request } from '../request';

/** ==================== AI 大盘/板块分析 API ==================== */

/** manually trigger an analysis run (async, returns immediately) */
export function fetchRunAnalysis(analysisType: Api.Analysis.AnalysisType) {
  return request<Api.Analysis.AnalysisRunSubmitResult>({
    url: `/admin/analysis/${analysisType}/run`,
    method: 'post'
  });
}

/** get the latest analysis run (with report content, data is null when none) */
export function fetchGetLatestAnalysis(analysisType: Api.Analysis.AnalysisType) {
  return request<Api.Analysis.AnalysisRunDetail | null>({
    url: `/admin/analysis/${analysisType}/latest`,
    method: 'get'
  });
}

/** get analysis run history (paginated) */
export function fetchGetAnalysisRuns(
  analysisType: Api.Analysis.AnalysisType,
  params: { page: number; page_size: number }
) {
  return request<Api.Common.PaginatingQueryRecord<Api.Analysis.AnalysisRunItem>>({
    url: `/admin/analysis/${analysisType}/runs`,
    method: 'get',
    params
  });
}

/** get a single analysis run detail (with report content) */
export function fetchGetAnalysisRunDetail(runId: number) {
  return request<Api.Analysis.AnalysisRunDetail>({
    url: `/admin/analysis/runs/${runId}`,
    method: 'get'
  });
}

/** get analysis strategy config (returns defaults when not configured) */
export function fetchGetAnalysisConfig(analysisType: Api.Analysis.AnalysisType) {
  return request<Api.Analysis.AnalysisConfig>({
    url: `/admin/analysis/${analysisType}/config`,
    method: 'get'
  });
}

/** save analysis strategy config (takes effect on next generation) */
export function fetchUpdateAnalysisConfig(
  analysisType: Api.Analysis.AnalysisType,
  data: Api.Analysis.AnalysisConfigSaveParams
) {
  return request<Api.Analysis.AnalysisConfig>({
    url: `/admin/analysis/${analysisType}/config`,
    method: 'put',
    data
  });
}
