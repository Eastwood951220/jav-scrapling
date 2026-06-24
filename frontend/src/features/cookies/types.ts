/** Metadata about a cookie file returned by GET /api/cookies. */
export interface CookieFileInfo {
  filename: string;
  size_bytes: number;
  created_at: string | null;
}

/** Cookie key-value pairs returned by GET /api/cookies/{filename}. */
export interface CookieContent {
  filename: string;
  cookies: Record<string, string>;
}

/**
 * Request body for PUT /api/cookies/{filename}.
 * Cookies can be a flat key-value dict or an array of {name, value} objects.
 */
export interface CookieUpdate {
  cookies: Record<string, string> | Array<{ name: string; value: string }>;
}
