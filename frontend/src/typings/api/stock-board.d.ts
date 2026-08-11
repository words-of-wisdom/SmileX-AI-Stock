declare namespace Api {
  /**
   * namespace StockBoard
   *
   * backend api module: "board" (行业/概念板块)
   */
  namespace StockBoard {
    /** 板块类型 */
    type BoardType = 'industry' | 'concept';

    /** 排序字段 */
    type SortBy = 'change_pct' | 'net_inflow';

    /** 板块日快照项 */
    interface BoardDailyItem {
      /** 记录 ID */
      id: number;
      /** 快照日期 */
      record_date: string;
      /** 板块类型: industry/concept */
      board_type: BoardType;
      /** 板块代码 */
      board_code: string;
      /** 板块名称 */
      board_name: string;
      /** 涨跌幅(%) */
      change_pct: number | null;
      /** 成交额(元) */
      turnover: number | null;
      /** 换手率(%) */
      turnover_rate: number | null;
      /** 成交量(手) */
      volume: number | null;
      /** 主力净流入(元) */
      net_inflow: number | null;
      /** 上涨家数 */
      rising_count: number | null;
      /** 下跌家数 */
      falling_count: number | null;
      /** 领涨股代码 */
      leading_stock_code: string | null;
      /** 领涨股名称 */
      leading_stock_name: string | null;
      /** 领涨股涨跌幅(%) */
      leading_stock_change_pct: number | null;
    }

    /** 板块历史趋势项 */
    interface BoardHistoryItem {
      /** 快照日期 */
      record_date: string;
      /** 涨跌幅(%) */
      change_pct: number | null;
      /** 成交额(元) */
      turnover: number | null;
      /** 主力净流入(元) */
      net_inflow: number | null;
      /** 上涨家数 */
      rising_count: number | null;
      /** 下跌家数 */
      falling_count: number | null;
    }

    /** 板块列表查询参数 */
    interface BoardListParams {
      board_type?: BoardType;
      date?: string | null;
      sort_by?: SortBy;
      sort_order?: 'asc' | 'desc';
    }
  }
}
