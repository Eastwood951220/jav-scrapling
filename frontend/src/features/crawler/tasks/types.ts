/** A single URL entry within a crawl task. */
export interface TaskUrlEntry {
  url: string;
  url_type: string;
  has_magnet?: boolean;
  has_chinese_sub?: boolean;
  sort_type?: number;
  source?: string;
  final_url?: string;
}

/** Crawl task model. */
export interface CrawlTask {
  _id: string;
  name: string;
  urls: TaskUrlEntry[];
  is_skip: boolean;
  created_at?: string;
  updated_at?: string;
}

/** Payload for creating or updating a crawl task. */
export interface TaskCreatePayload {
  name: string;
  urls: TaskUrlEntry[];
  is_skip?: boolean;
}
