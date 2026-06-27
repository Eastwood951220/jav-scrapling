import client from "@/shared/api/client";
import type { MovieListResponse, StorageLocation } from "./types";

export type { MovieListResponse } from "./types";

export type FilterType = "actor" | "tag" | "director" | "maker" | "series";

export function fetchTaskNames(): Promise<{ name: string }[]> {
  return client.get("/movies/task-names").then((res) => res.data);
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
  director?: string;
  maker?: string;
  series?: string;
  date_from?: string;
  date_to?: string;
  storage_status?: string;
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
  director?: string;
  maker?: string;
  series?: string;
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

export function selectMagnet(movieId: string, dedupeKey: string): Promise<{ success: boolean; selected_magnet_dedupe_key: string }> {
  return client.post(`/movies/${movieId}/select-magnet`, { dedupe_key: dedupeKey }).then((res) => res.data);
}

export function fetchFilters(type: FilterType): Promise<string[]> {
  return client.get("/movies/filters", { params: { type } }).then((res) => res.data);
}

// Backward-compatible helpers
export function fetchActors(): Promise<string[]> {
  return fetchFilters("actor");
}

export function fetchTags(): Promise<string[]> {
  return fetchFilters("tag");
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

export function createStorageTask(
  movieId: string,
  magnetUrl: string,
  magnetMeta?: { has_chinese_sub?: boolean; tags?: string[] },
): Promise<StorageTaskCreateResponse> {
  return client.post("/storage/tasks", {
    movie_id: movieId,
    magnet_url: magnetUrl,
    has_chinese_sub: magnetMeta?.has_chinese_sub ?? false,
    tags: magnetMeta?.tags ?? [],
  }).then((res) => res.data);
}

export function batchCreateStorageTasks(
  movieIds: string[],
  options?: { skip_running?: boolean; skip_completed?: boolean; retry_failed?: boolean },
): Promise<StorageBatchResponse> {
  return client.post("/storage/tasks/batch", { movie_ids: movieIds, ...options }).then((res) => res.data);
}

// ---------------------------------------------------------------------------
// Storage location sync API
// ---------------------------------------------------------------------------

export interface SyncLocationResult {
  locations: StorageLocation[];
  synced: boolean;
}

export interface SyncBatchResult {
  results: { movie_id: string; synced: boolean; locations: StorageLocation[] }[];
  total: number;
}

export function syncMovieLocation(movieId: string): Promise<SyncLocationResult> {
  return client.post(`/movies/${movieId}/sync-location`).then((res) => res.data);
}

export function syncMovieLocationsBatch(ids: string[]): Promise<SyncBatchResult> {
  return client.post("/movies/sync-location/batch", { ids }).then((res) => res.data);
}
