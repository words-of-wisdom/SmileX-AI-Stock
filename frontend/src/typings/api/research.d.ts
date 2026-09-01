declare namespace Api {
  namespace Research {
    /** 券商研报记录 */
    interface ResearchReportItem {
      id: number;
      stock_code: string;
      stock_name: string | null;
      title: string;
      url: string;
      org_name: string | null;
      rating: string | null;
      industry: string | null;
      /** 盈利预测：{ [年份]: { eps, pe } } */
      forecast: Record<string, { eps?: number; pe?: number }> | null;
      published_date: string | null;
      fetched_at: string | null;
    }

    interface RatingCount {
      rating: string;
      count: number;
    }

    interface NameCount {
      name: string | null;
      count: number;
    }

    /** 研报概览统计 */
    interface ResearchStats {
      days: number;
      total: number;
      stock_count: number;
      org_count: number;
      rating_distribution: RatingCount[];
      hot_stocks: NameCount[];
      hot_orgs: NameCount[];
    }

    /** 按股票分组的研报统计项 */
    interface ResearchStockStatItem {
      stock_code: string;
      stock_name: string | null;
      report_count: number;
      positive_count: number;
      org_count: number;
      latest_date: string | null;
    }

    /** 手动同步结果 */
    interface ResearchSyncResult {
      codes: number;
      saved: number;
      failed: number;
    }

    /** 研报列表查询参数 */
    interface ReportQuery {
      page: number;
      pageSize: number;
      stockCode?: string;
      keyword?: string;
      orgName?: string;
      rating?: string;
      startDate?: string;
      endDate?: string;
    }
  }
}
