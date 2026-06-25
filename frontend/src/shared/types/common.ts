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
  date?: string;
  length?: string;
  director?: string;
  maker?: string;
  publisher?: string;
  actors?: string[];
  tags?: string[];
  cover?: string;
  source_url?: string;
}
