/** A single cookie entry matching the browser-export format. */
export interface JavdbCookie {
  domain: string;
  expirationDate: number | null;
  hostOnly: boolean;
  httpOnly: boolean;
  name: string;
  path: string;
  sameSite: string | null;
  secure: boolean;
  session: boolean;
  storeId: string | null;
  value: string;
}

/** Wrapper for the cookie array stored in the JSON file. */
export interface CookiesConfig {
  cookies: JavdbCookie[];
}

/** Application settings stored in MongoDB / env vars. */
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
  BATCH_SAVE_SIZE?: number;
  [key: string]: unknown;
}
