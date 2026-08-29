declare namespace Api {
  namespace Macro {
    /** 国家/地区 */
    export type CountryType = 'CN' | 'US';

    /** 指标代码 */
    export type IndicatorCode = 'cpi' | 'ppi' | 'm0' | 'm1' | 'm2' | 'core_cpi';

    /** 宏观指标记录（序列点 / 最新值卡片共用） */
    export interface MacroIndicatorItem {
      id: number;
      country: CountryType | string;
      indicator_code: IndicatorCode | string;
      indicator_name: string;
      period: string;
      value: number | null;
      yoy: number | null;
      mom: number | null;
      unit: string;
      source: string | null;
      released_at: string | null;
    }

    /** 手动同步结果 */
    export interface MacroSyncResult {
      sources: Record<string, number>;
      saved: number;
    }
  }
}
