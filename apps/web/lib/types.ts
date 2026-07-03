// Shared API types mirroring the FastAPI Pydantic schemas.

export type Role = "admin" | "editor" | "author" | "viewer";
export type ReportStatus = "draft" | "published" | "archived";
export type Visibility = "public" | "internal" | "private";

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  team?: string | null;
  department?: string | null;
  title?: string | null;
  bio?: string | null;
  avatar_url?: string | null;
  created_at: string;
}

export interface TaxonomyItem {
  id: string;
  name: string;
  slug: string;
}

export interface Category extends TaxonomyItem {
  description?: string | null;
  parent_id?: string | null;
}

export interface ReportVersion {
  id: string;
  version: number;
  changelog?: string | null;
  created_at: string;
  has_html: boolean;
  has_pdf: boolean;
  media_kind?: "html" | "pdf" | "video" | "other" | null;
  content_type?: string | null;
  asset_name?: string | null;
}

export interface ReportSummary {
  id: string;
  title: string;
  slug: string;
  summary?: string | null;
  description?: string | null;
  status: ReportStatus;
  visibility: Visibility;
  view_count: number;
  current_version: number;
  created_at: string;
  updated_at: string;
  author: User;
  category?: Category | null;
  tags: TaxonomyItem[];
  technologies: TaxonomyItem[];
}

export interface ReportDetail extends ReportSummary {
  team?: string | null;
  department?: string | null;
  project?: string | null;
  github_repo?: string | null;
  pull_request?: string | null;
  demo_url?: string | null;
  video_url?: string | null;
  versions: ReportVersion[];
}

export interface PaginatedReports {
  items: ReportSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchResult {
  report: ReportSummary;
  rank: number;
  snippet?: string | null;
}

export interface SearchResponse {
  items: SearchResult[];
  total: number;
  query: string;
  semantic: boolean;
}

export interface Suggestion {
  label: string;
  type: "technology" | "tag" | "report";
  value: string;
}

export interface Comment {
  id: string;
  body: string;
  created_at: string;
  author: User;
  parent_id?: string | null;
  replies: Comment[];
}

export interface RecentComment {
  report_id: string;
  report_title: string;
  report_slug: string;
  author_name: string;
  body: string;
  created_at: string;
}

export interface DashboardData {
  recently_added: ReportSummary[];
  recently_updated: ReportSummary[];
  trending: ReportSummary[];
  most_viewed: ReportSummary[];
  recent_comments: RecentComment[];
  category_counts: Record<string, number>;
}

export interface TechnologyCount {
  name: string;
  slug: string;
  count: number;
}

export interface Collection {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_public: boolean;
  parent_id?: string | null;
  owner: User;
  created_at: string;
  report_count: number;
  subfolder_count: number;
}

export interface Breadcrumb {
  id: string;
  name: string;
  slug: string;
}

export interface CollectionDetail extends Collection {
  reports: ReportSummary[];
  children: Collection[];
  breadcrumbs: Breadcrumb[];
}

export interface Analytics {
  total_reports: number;
  total_published: number;
  total_users: number;
  total_views: number;
  views_last_30d: number;
  top_authors: { name: string; reports: number }[];
}
