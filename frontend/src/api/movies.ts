import client from "./client";

export interface MovieListResponse {
  items: Record<string, unknown>[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export function fetchCollections(): Promise<string[]> {
  return client.get("/movies/collections").then((res) => res.data);
}

export function fetchMovies(params: {
  collection?: string;
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: number;
}): Promise<MovieListResponse> {
  return client.get("/movies", { params }).then((res) => res.data);
}

export function fetchMovie(id: string, collection?: string): Promise<Record<string, unknown>> {
  return client.get(`/movies/${id}`, { params: { collection } }).then((res) => res.data);
}
