declare namespace Api {
  /**
   * namespace StockMarket
   *
   * backend api module: "market" (大盘概览)
   */
  namespace StockMarket {
    /** 大盘指数快照项 */
    interface MarketIndexItem {
      /** 记录 ID */
      id: number;
      /** 快照日期 */
      record_date: string;
      /** 指数代码 */
      index_code: string;
      /** 指数名称 */
      index_name: string;
      /** 最新价 */
      latest_price: number | null;
      /** 涨跌幅(%) */
      change_pct: number | null;
      /** 涨跌额 */
      change_amount: number | null;
      /** 成交量(手) */
      volume: number | null;
      /** 成交额(元) */
      turnover: number | null;
      /** 振幅(%) */
      amplitude: number | null;
      /** 最高 */
      high: number | null;
      /** 最低 */
      low: number | null;
      /** 今开 */
      open: number | null;
      /** 昨收 */
      prev_close: number | null;
    }

    /** 指数历史趋势项 */
    interface MarketIndexHistoryItem {
      /** 快照日期 */
      record_date: string;
      /** 收盘价/最新价 */
      latest_price: number | null;
      /** 涨跌幅(%) */
      change_pct: number | null;
      /** 成交量(手) */
      volume: number | null;
      /** 成交额(元) */
      turnover: number | null;
      /** 最高 */
      high: number | null;
      /** 最低 */
      low: number | null;
      /** 今开 */
      open: number | null;
      /** 昨收 */
      prev_close: number | null;
    }

    /** 指数下拉选项 */
    interface MarketIndexOption {
      /** 指数代码 */
      index_code: string;
      /** 指数名称 */
      index_name: string;
    }
  }
}
