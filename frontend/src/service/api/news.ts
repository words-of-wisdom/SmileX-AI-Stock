import { request } from '../request';

/** ==================== 资讯聚合 API ==================== */

/** get news list */
export function fetchGetNewsList(params?: Api.News.NewsSearchParams) {
  return request<Api.News.NewsList>({
    url: '/admin/sys/news/list',
    method: 'get',
    params
  });
}

/** get news detail */
export function fetchGetNewsDetail(newsId: number) {
  return request<Api.News.NewsDetail>({
    url: `/admin/sys/news/${newsId}`,
    method: 'get'
  });
}

/** get news source statistics */
export function fetchGetNewsSources() {
  return request<Api.News.NewsSourceItem[]>({
    url: '/admin/sys/news/sources',
    method: 'get'
  });
}
