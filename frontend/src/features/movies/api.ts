import client from "@/shared/api/client";
import type { MovieListResponse } from "./types";

export type { MovieListResponse } from "./types";

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
