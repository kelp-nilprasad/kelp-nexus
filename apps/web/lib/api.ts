// Typed fetch client. Requests are same-origin (/api/* is proxied to FastAPI by
// next.config rewrites) so the httpOnly session cookie is sent automatically.
import type {
  Analytics,
  Category,
  Collection,
  CollectionDetail,
  Comment,
  DashboardData,
  PaginatedReports,
  ReportDetail,
  ReportSummary,
  SearchResponse,
  Suggestion,
  TaxonomyItem,
  TechnologyCount,
  User,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    // A 401 on a non-auth call means the session is missing/stale (e.g. the user
    // id no longer exists) — bounce to login so the user can re-authenticate
    // instead of seeing buttons silently do nothing. The /auth/* probes are
    // excluded so the login page itself doesn't loop.
    if (
      res.status === 401 &&
      typeof window !== "undefined" &&
      !path.startsWith("/auth/") &&
      window.location.pathname !== "/login"
    ) {
      window.location.assign("/login");
    }
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // auth
  authConfig: () => req<{ microsoft: boolean; dev_login: boolean }>("/auth/config"),
  devLogin: (email: string, password: string) =>
    req<{ access_token: string; user: User }>("/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => req<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  me: () => req<User>("/auth/me"),

  // dashboard / analytics
  dashboard: () => req<DashboardData>("/dashboard"),
  analytics: () => req<Analytics>("/analytics"),

  // reports
  listReports: (page = 1) => req<PaginatedReports>(`/reports?page=${page}`),
  getReport: (slug: string) => req<ReportDetail>(`/reports/${slug}`),
  createReport: (body: unknown) =>
    req<ReportDetail>("/reports", { method: "POST", body: JSON.stringify(body) }),
  updateReport: (slug: string, body: unknown) =>
    req<ReportDetail>(`/reports/${slug}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteReport: (slug: string) => req<void>(`/reports/${slug}`, { method: "DELETE" }),
  relatedReports: (slug: string) => req<ReportSummary[]>(`/reports/${slug}/related`),
  renderUrl: (slug: string, version?: number) =>
    `${BASE}/reports/${slug}/render${version ? `?version=${version}` : ""}`,

  uploadVersion: async (slug: string, form: FormData) => {
    const res = await fetch(`${BASE}/reports/${slug}/versions`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) throw new ApiError(res.status, "Upload failed");
    return res.json();
  },

  // search
  search: (params: Record<string, string>) =>
    req<SearchResponse>(`/search?${new URLSearchParams(params).toString()}`),
  searchSuggest: (q: string) =>
    req<Suggestion[]>(`/search/suggest?q=${encodeURIComponent(q)}`),

  // taxonomy
  categories: () => req<Category[]>("/categories"),
  tags: () => req<TaxonomyItem[]>("/tags"),
  technologies: () => req<TaxonomyItem[]>("/technologies"),
  technologyCloud: () => req<TechnologyCount[]>("/technologies/cloud"),

  // engagement
  comments: (reportId: string) => req<Comment[]>(`/reports/${reportId}/comments`),
  addComment: (reportId: string, body: string, parent_id?: string) =>
    req<Comment>(`/reports/${reportId}/comments`, {
      method: "POST",
      body: JSON.stringify({ body, parent_id }),
    }),
  favorites: () => req<ReportSummary[]>("/favorites"),
  addFavorite: (reportId: string) =>
    req<void>(`/reports/${reportId}/favorite`, { method: "PUT" }),
  removeFavorite: (reportId: string) =>
    req<void>(`/reports/${reportId}/favorite`, { method: "DELETE" }),
  recentlyViewed: () => req<ReportSummary[]>("/recently-viewed"),

  // collections
  collections: () => req<Collection[]>("/collections"),
  allCollections: () => req<Collection[]>("/collections?top_level=false"),
  collection: (idOrSlug: string) => req<CollectionDetail>(`/collections/${idOrSlug}`),
  createCollection: (body: {
    name: string;
    description?: string;
    is_public?: boolean;
    parent_id?: string;
  }) => req<Collection>("/collections", { method: "POST", body: JSON.stringify(body) }),
  deleteCollection: (idOrSlug: string) =>
    req<void>(`/collections/${idOrSlug}`, { method: "DELETE" }),
  addToCollection: (idOrSlug: string, reportId: string) =>
    req<void>(`/collections/${idOrSlug}/reports/${reportId}`, { method: "PUT" }),
  removeFromCollection: (idOrSlug: string, reportId: string) =>
    req<void>(`/collections/${idOrSlug}/reports/${reportId}`, { method: "DELETE" }),

  // profiles
  authors: () => req<User[]>("/users"),
  user: (id: string) => req<User>(`/users/${id}`),
  userReports: (id: string) => req<ReportSummary[]>(`/users/${id}/reports`),

  // admin
  adminUsers: () => req<User[]>("/admin/users"),
  setRole: (id: string, role: string) =>
    req<User>(`/admin/users/${id}/role`, { method: "PATCH", body: JSON.stringify({ role }) }),
};
