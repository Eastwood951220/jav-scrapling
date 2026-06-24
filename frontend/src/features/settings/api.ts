import client from "../../shared/api/client";
import type { AppSettings } from "./types";

export type { AppSettings } from "./types";

export function fetchSettings(): Promise<AppSettings> {
  return client.get("/settings").then((res) => res.data);
}

export function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return client.put("/settings", data).then((res) => res.data);
}
