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

/** Magnet entry attached to a movie. */
export interface MovieMagnet {
  magnet: string;
  title?: string;
  size?: string;
}

/** Storage task summary embedded in a movie document. */
export interface StorageSummary {
  last_task_id?: string;
  last_status?: string;
  updated_at?: string;
}

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
  magnets?: MovieMagnet[];
  size?: number;
  has_chinese_sub?: boolean;
  source_url?: string;
  source_name?: string;
  source_code?: string;
  source_page?: number;
  name?: string;
  storage_summary?: StorageSummary;
  created_at?: string;
  updated_at?: string;
}
