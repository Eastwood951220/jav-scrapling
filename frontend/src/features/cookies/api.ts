import client from "@/shared/api/client";
import type { CookieFileInfo, CookieContent, CookieUpdate } from "./types";

export type { CookieFileInfo, CookieContent, CookieUpdate } from "./types";

export function fetchCookieFiles(): Promise<CookieFileInfo[]> {
  return client.get("/cookies").then((res) => res.data);
}

export function fetchCookieContent(filename: string): Promise<CookieContent> {
  return client.get(`/cookies/${encodeURIComponent(filename)}`).then((res) => res.data);
}

export function saveCookieFile(
  filename: string,
  data: CookieUpdate,
): Promise<CookieContent> {
  return client
    .put(`/cookies/${encodeURIComponent(filename)}`, data)
    .then((res) => res.data);
}

export function deleteCookieFile(filename: string): Promise<void> {
  return client.delete(`/cookies/${encodeURIComponent(filename)}`);
}
