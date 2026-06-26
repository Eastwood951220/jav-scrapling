import client from "@/shared/api/client";
import type { AppConfig, CookiesConfig } from "./types";

export type { AppConfig, CookiesConfig, JavdbCookie } from "./types";

export function fetchConfig(): Promise<AppConfig> {
  return client.get("/config").then((res) => res.data);
}

export function updateConfig(data: Partial<AppConfig>): Promise<AppConfig> {
  return client.put("/config", data).then((res) => res.data);
}

export function fetchCookiesConfig(): Promise<CookiesConfig> {
  return client.get("/config/cookies").then((res) => res.data);
}

export function updateCookiesConfig(data: CookiesConfig): Promise<CookiesConfig> {
  return client.put("/config/cookies", data).then((res) => res.data);
}

export function syncMovieFilters(): Promise<{ actors: number; tags: number }> {
  return client.post("/movies/sync-filters").then((res) => res.data);
}
