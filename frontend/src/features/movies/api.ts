import client from "@/shared/api/client";
import type { MovieListResponse } from "./types";

export type { MovieListResponse } from "./types";

export function fetchTaskNames(): Promise<{ _id: string; name: string }[]> {
  return client.get("/tasks").then((res) => res.data);
}

export function fetchMovies(params: {
  source_task_name?: string;
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: number;
  rating_min?: number;
}): Promise<MovieListResponse> {
  return client.get("/movies", { params }).then((res) => res.data);
}

export function fetchMovie(id: string): Promise<Record<string, unknown>> {
  return client.get(`/movies/${id}`).then((res) => res.data);
}

export function deleteMovie(id: string): Promise<{ deleted: boolean }> {
  return client.delete(`/movies/${id}`).then((res) => res.data);
}

export function deleteMovies(ids: string[]): Promise<{ deleted: number }> {
  return client.delete("/movies/batch", { data: { ids } }).then((res) => res.data);
}
