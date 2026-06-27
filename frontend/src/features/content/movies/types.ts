import type { Movie, StorageLocation } from "@/shared/types/common";

export type { Movie, StorageLocation };

/** Paginated movie list response. */
export interface MovieListResponse {
  items: Movie[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}
