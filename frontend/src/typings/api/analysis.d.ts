declare namespace Api {
  namespace Analysis {
    /** 分析类型 */
    export type AnalysisType = 'market' | 'sector';

    /** 明日研判（parsed_result.tomorrow_outlook） */
    export interface TomorrowOutlook {
      direction?: string;
      summary?: string;
    }

    /** 大盘分析结构化摘要（parsed_result） */
    export interface MarketParsedResult {
      sentiment?: string;
      score?: number;
      summary?: string;
      key_points?: string[];
      tomorrow_outlook?: TomorrowOutlook;
    }

    /** 板块分析热门板块项 */
    export interface HotBoardItem {
      board_name?: string;
      board_type?: string;
      change_pct?: number | null;
      viewpoint?: string;
    }

    /** 板块分析结构化摘要（parsed_result） */
    export interface SectorParsedResult {
      rotation_summary?: string;
      hot_boards?: HotBoardItem[];
      key_points?: string[];
      tomorrow_outlook?: TomorrowOutlook;
    }

    /** 分析策略配置（无记录时后端返回默认值，data 始终非空） */
    export interface AnalysisConfig {
      analysis_type: AnalysisType | string;
      prompt_template: string | null;
      include_tomorrow: boolean;
      updated_at: string | null;
    }

    /** 分析策略配置保存参数 */
    export interface AnalysisConfigSaveParams {
      prompt_template?: string | null;
      include_tomorrow: boolean;
    }

    /** 分析执行记录（列表项） */
    export interface AnalysisRunItem {
      id: number;
      analysis_type: AnalysisType | string;
      run_date: string;
      trigger_type: 'schedule' | 'manual';
      status: 'running' | 'success' | 'failed';
      parsed_result: MarketParsedResult | SectorParsedResult | Record<string, unknown> | null;
      error_msg: string | null;
      created_at: string | null;
    }

    /** 分析执行记录详情（含报告原文） */
    export interface AnalysisRunDetail extends AnalysisRunItem {
      ai_raw_response: string | null;
    }

    /** 分析提交结果（异步执行：接口立即返回，结果见执行记录） */
    export interface AnalysisRunSubmitResult {
      run_id: number;
      status: string;
    }
  }
}
