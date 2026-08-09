declare namespace Api {
  /**
   * namespace News
   *
   * backend api module: "news" (资讯聚合)
   */
  namespace News {
    /** 新闻列表项 */
    interface News {
      /** 新闻 ID */
      id: number;
      /** 新闻标题 */
      title: string;
      /** 新闻摘要 */
      summary: string | null;
      /** 原文链接 */
      url: string;
      /** 新闻源 key */
      source: string;
      /** 新闻源中文名 */
      source_name: string;
      /** 作者 */
      author: string | null;
      /** 发布时间 */
      published_at: string | null;
      /** 创建时间 */
      created_at: string | null;
    }

    /** 新闻详情 */
    interface NewsDetail extends News {
      /** 新闻正文 */
      content: string | null;
      /** 原始时间字符串 */
      raw_time: string | null;
    }

    /** 新闻搜索参数 */
    type NewsSearchParams = CommonType.RecordNullable<
      {
        keyword?: string | null;
        source?: string | null;
        start_time?: string | null;
        end_time?: string | null;
      } & Common.CommonSearchParams
    >;

    /** 新闻列表 */
    type NewsList = Common.PaginatingQueryRecord<News>;

    /** 新闻源统计项 */
    interface NewsSourceItem {
      /** 新闻源 key */
      source: string;
      /** 新闻源中文名 */
      source_name: string;
      /** 该源新闻条数 */
      count: number;
    }
  }
}
