/** Generic paginated API response envelope. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

/** Task run lifecycle statuses. */
export type RunStatus = "queued" | "running" | "completed" | "failed" | "stopped";

/** Movie document returned by the backend. */
export interface Movie {
  _id: string;
  code: string;
  title: string;
  cover?: string;
  release_date?: string;
  duration?: number;
  director?: string;
  maker?: string;
  publisher?: string;
  series?: string;
  rating?: number;
  tags?: string[];
  actors?: string[];
  magnet?: string;
  size?: number;
  has_chinese_sub?: boolean;
  source_url?: string;
  source_name?: string;
  source_code?: string;
  source_page?: number;
  name?: string;
  created_at?: string;
  updated_at?: string;
}
