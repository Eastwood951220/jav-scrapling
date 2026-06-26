import client from "@/shared/api/client";
import type { MovieListResponse } from "./types";

export type { MovieListResponse } from "./types";

export function fetchTaskNames(): Promise<{ _id: string; name: string }[]> {
  return client.get("/crawler/tasks").then((res) => res.data);
}

export function fetchMovies(params: {
  source_task_name?: string;
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: number;
  rating_min?: number;
  actors?: string;
  tags?: string;
  date_from?: string;
  date_to?: string;
}): Promise<MovieListResponse> {
  return client.get("/movies", { params }).then((res) => res.data);
}

export interface MagnetExportItem {
  code: string;
  title: string;
  magnet: string;
  size: string;
}

export function fetchAllMagnets(params: {
  source_task_name?: string;
  search?: string;
  rating_min?: number;
  actors?: string;
  tags?: string;
  date_from?: string;
  date_to?: string;
}): Promise<{ magnets: MagnetExportItem[]; total: number }> {
  return client.get("/movies/magnets", { params }).then((res) => res.data);
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

export function fetchActors(): Promise<string[]> {
  return client.get("/movies/actors").then((res) => res.data);
}

export function fetchTags(): Promise<string[]> {
  return client.get("/movies/tags").then((res) => res.data);
}

export function syncMovieFilters(): Promise<{ actors: number; tags: number }> {
  return client.post("/movies/sync-filters").then((res) => res.data);
}

// ---------------------------------------------------------------------------
// Storage task API
// ---------------------------------------------------------------------------

export interface StorageTaskCreateResponse {
  task_id: string;
  status: string;
}

export interface StorageBatchItem {
  movie_id: string;
  result: string;
  task_id?: string;
  reason?: string;
}

export interface StorageBatchResponse {
  requested: number;
  created: number;
  skipped: number;
  items: StorageBatchItem[];
}

export function createStorageTask(movieId: string, magnetUrl: string): Promise<StorageTaskCreateResponse> {
  return client.post("/storage/tasks", { movie_id: movieId, magnet_url: magnetUrl }).then((res) => res.data);
}

export function batchCreateStorageTasks(
  movieIds: string[],
  options?: { skip_running?: boolean; skip_completed?: boolean; retry_failed?: boolean },
): Promise<StorageBatchResponse> {
  return client.post("/storage/tasks/batch", { movie_ids: movieIds, ...options }).then((res) => res.data);
}
