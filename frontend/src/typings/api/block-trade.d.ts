declare namespace Api {
  /**
   * namespace BlockTrade
   *
   * backend api module: "block-trade" (大宗交易 / 暗盘跟踪)
   */
  namespace BlockTrade {
    /** 活跃A股统计窗口 */
    type StatWindow = '近一月' | '近三月' | '近六月' | '近一年';

    /** 子榜类型 */
    type SubBoard = 'daily' | 'active';

    /** 每日统计单项（含排名变化） */
    interface BlockTradeDailyItem {
      /** 记录 ID */
      id: number;
      /** 交易日期 */
      record_date: string | null;
      /** 当日排名（按占流通市值比降序） */
      rank: number;
      /** 排名变化：正=上升，负=下降，null=新进榜 */
      rank_change: number | null;
      /** 证券代码 */
      stock_code: string;
      /** 证券简称 */
      stock_name: string;
      /** 涨跌幅(%) */
      change_pct: number | null;
      /** 收盘价 */
      close_price: number | null;
      /** 成交价 */
      trade_price: number | null;
      /** 折溢率(%)，正=溢价，负=折价 */
      premium_rate: number | null;
      /** 成交笔数 */
      trade_count: number | null;
      /** 成交总量(股) */
      trade_volume: number | null;
      /** 成交总额(万元) */
      trade_amount: number | null;
      /** 成交总额/流通市值(%) */
      amount_ratio: number | null;
    }

    /** 活跃A股统计单项 */
    interface BlockTradeActiveItem {
      /** 记录 ID */
      id: number;
      /** 统计窗口 */
      stat_window: string;
      /** 排名（按上榜次数降序） */
      rank: number;
      /** 证券代码 */
      stock_code: string;
      /** 证券简称 */
      stock_name: string;
      /** 最新价 */
      latest_price: number | null;
      /** 涨跌幅(%) */
      change_pct: number | null;
      /** 最近上榜日 */
      last_list_date: string | null;
      /** 上榜次数-总计 */
      list_count_total: number | null;
      /** 上榜次数-溢价 */
      list_count_premium: number | null;
      /** 上榜次数-折价 */
      list_count_discount: number | null;
      /** 总成交额(万元) */
      total_amount: number | null;
      /** 折溢率(%) */
      premium_rate: number | null;
      /** 成交总额/流通市值(%) */
      amount_ratio: number | null;
      /** 上榜后1日平均涨跌幅(%) */
      avg_change_1d: number | null;
      /** 上榜后5日平均涨跌幅(%) */
      avg_change_5d: number | null;
      /** 上榜后10日平均涨跌幅(%) */
      avg_change_10d: number | null;
      /** 上榜后20日平均涨跌幅(%) */
      avg_change_20d: number | null;
    }

    /** 子榜概览统计项 */
    interface BlockTradeSourceItem {
      /** 子榜：daily-每日统计 / active-活跃A股 */
      sub_board: SubBoard;
      /** 子榜中文名 */
      source_name: string;
      /** 统计窗口（仅 active 子榜有值） */
      stat_window: string | null;
      /** 最近快照日期（仅 daily 子榜有值） */
      last_record_date: string | null;
      /** 最近同步时间 */
      last_sync_at: string | null;
      /** 最新快照条数 */
      count: number;
    }

    /** 单股历史排名趋势项 */
    interface BlockTradeHistoryItem {
      /** 快照日期 */
      record_date: string;
      /** 排名 */
      rank: number;
    }
  }
}
