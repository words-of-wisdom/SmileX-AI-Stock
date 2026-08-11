declare namespace Api {
  /**
   * namespace StockHot
   *
   * backend api module: "stock-hot" (股票热榜)
   */
  namespace StockHot {
    /** 热榜排名项（含排名变化） */
    interface StockHotRankItem {
      /** 记录 ID */
      id: number;
      /** 榜单源 key */
      source: string;
      /** 榜单源中文名 */
      source_name: string;
      /** 快照日期 */
      record_date: string | null;
      /** 当日排名 */
      rank: number;
      /** 排名变化：正=上升，负=下降，null=新进榜 */
      rank_change: number | null;
      /** 股票代码 */
      stock_code: string;
      /** 股票名称 */
      stock_name: string;
      /** 最新价 */
      latest_price: number | null;
      /** 涨跌幅(%) */
      change_pct: number | null;
      /** 热度/关注数 */
      hot_value: number | null;
    }

    /** 热榜源统计项 */
    interface StockHotSourceItem {
      /** 榜单源 key */
      source: string;
      /** 榜单源中文名 */
      source_name: string;
      /** 来源分组 */
      group: string;
      /** 最近快照日期 */
      last_record_date: string | null;
      /** 最近同步时间 */
      last_sync_at: string | null;
      /** 最新快照条数 */
      count: number;
    }

    /** 单股历史排名趋势项 */
    interface StockHotHistoryItem {
      /** 快照日期 */
      record_date: string;
      /** 排名 */
      rank: number;
    }
  }
}
