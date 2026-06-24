/** Filter configuration for crawl tasks. */
export interface FilterConfig {
  only_chinese: boolean;
  exclude_multi_person: boolean;
  extra_filters?: Record<string, unknown>;
}

/** Crawl task model. */
export interface CrawlTask {
  _id: string;
  name: string;
  url: string;
  url_type: string;
  is_skip: boolean;
  max_list_pages: number;
  filter: FilterConfig;
  source?: string;
  final_url?: string;
  created_at?: string;
  updated_at?: string;
}

/** Payload for creating or updating a crawl task. */
export interface TaskCreatePayload {
  name: string;
  url: string;
  url_type: string;
  is_skip?: boolean;
  max_list_pages?: number;
  filter?: FilterConfig;
}
