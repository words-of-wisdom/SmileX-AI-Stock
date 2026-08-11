declare namespace Api {
  /**
   * namespace Demo
   *
   * backend api module: "demo" (示例：股票 SDK 简单调用)
   */
  namespace Demo {
    /** akshare 个股基础信息项 */
    interface StockInfoItem {
      /** 信息项名称 */
      item: string;
      /** 信息项值 */
      value: string;
    }

    /** Baostock 日 K 线数据项（原始字符串返回） */
    interface KlineItem {
      /** 交易日期 YYYY-MM-DD */
      date: string;
      /** 证券代码，如 sh.600519 */
      code: string;
      /** 开盘价 */
      open: string | null;
      /** 最高价 */
      high: string | null;
      /** 最低价 */
      low: string | null;
      /** 收盘价 */
      close: string | null;
      /** 成交量（股） */
      volume: string | null;
      /** 成交额（元） */
      amount: string | null;
      /** 涨跌幅(%) */
      pctChg: string | null;
    }
  }
}
