import client from "@/shared/api/client";
import type { AppSettings, CookiesConfig } from "./types";

export type { AppSettings, CookiesConfig, JavdbCookie } from "./types";

export function fetchSettings(): Promise<AppSettings> {
  return client.get("/settings").then((res) => res.data);
}

export function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return client.put("/settings", data).then((res) => res.data);
}

export function fetchCookiesConfig(): Promise<CookiesConfig> {
  return client.get("/settings/cookies").then((res) => res.data);
}

export function updateCookiesConfig(data: CookiesConfig): Promise<CookiesConfig> {
  return client.put("/settings/cookies", data).then((res) => res.data);
}

export function syncMovieFilters(): Promise<{ actors: number; tags: number }> {
  return client.post("/movies/sync-filters").then((res) => res.data);
}
