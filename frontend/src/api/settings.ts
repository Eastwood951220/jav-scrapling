import client from "./client";
import type { AppSettings } from "../features/settings/types";

export type { AppSettings } from "../features/settings/types";

export function fetchSettings(): Promise<AppSettings> {
  return client.get("/settings").then((res) => res.data);
}

export function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return client.put("/settings", data).then((res) => res.data);
}
