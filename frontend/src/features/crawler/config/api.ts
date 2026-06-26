import client from "@/shared/api/client";
import type { AppConfig, CookiesConfig } from "./types";

export type { AppConfig, CookiesConfig, JavdbCookie } from "./types";

export function fetchConfig(): Promise<AppConfig> {
  return client.get("/crawler/config").then((res) => res.data);
}

export function updateConfig(data: Partial<AppConfig>): Promise<AppConfig> {
  return client.put("/crawler/config", data).then((res) => res.data);
}

export function fetchCookiesConfig(): Promise<CookiesConfig> {
  return client.get("/crawler/config/cookies").then((res) => res.data);
}

export function updateCookiesConfig(data: CookiesConfig): Promise<CookiesConfig> {
  return client.put("/crawler/config/cookies", data).then((res) => res.data);
}