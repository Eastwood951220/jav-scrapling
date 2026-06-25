/** Crawl task model. */
export interface CrawlTask {
  _id: string;
  name: string;
  url: string;
  url_type: string;
  is_skip: boolean;
  max_list_pages: number;
  has_magnet?: boolean;
  has_chinese_sub?: boolean;
  sort_type?: number;
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
  has_magnet?: boolean;
  has_chinese_sub?: boolean;
  sort_type?: number;
  final_url?: string;
}
