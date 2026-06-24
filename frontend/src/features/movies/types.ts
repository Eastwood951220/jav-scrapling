import type { Movie } from "@/shared/types/common";

export type { Movie };

/** Paginated movie list response. */
export interface MovieListResponse {
  items: Record<string, unknown>[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}
