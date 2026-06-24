import client from "./client";

export interface AppSettings {
  MONGO_URI?: string;
  MONGO_DB_NAME?: string;
  MONGO_CONNECT_TIMEOUT_MS?: number;
  MAX_LIST_PAGES?: number;
  LIST_PAGE_DELAY_MIN?: number;
  LIST_PAGE_DELAY_MAX?: number;
  DETAIL_PAGE_DELAY_MIN?: number;
  DETAIL_PAGE_DELAY_MAX?: number;
  SECURITY_WAIT_SECONDS?: number;
  REQUEST_TIMEOUT?: number;
  USE_DYNAMIC_FETCHER?: boolean;
  [key: string]: unknown;
}

export function fetchSettings(): Promise<AppSettings> {
  return client.get("/settings").then((res) => res.data);
}

export function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return client.put("/settings", data).then((res) => res.data);
}
