const DEFAULT_API_BASE = "http://localhost:8000";

const rawBase =
  process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, "") || DEFAULT_API_BASE;

export const API_BASE = rawBase.endsWith("/api") ? rawBase : `${rawBase}/api`;
