/**
 * Safely extract a human-readable message from any thrown value.
 *
 * Replaces the unsafe `(e as Error).message` pattern used throughout the
 * codebase, which silently returns `undefined` when the caught value is a
 * plain string, a non-Error object, or `undefined`.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message: unknown }).message);
  }
  return "未知错误";
}
