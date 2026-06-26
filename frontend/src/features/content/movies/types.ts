import type { Movie } from "@/shared/types/common";

export type { Movie };

/** Paginated movie list response. */
export interface MovieListResponse {
  items: Movie[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}
