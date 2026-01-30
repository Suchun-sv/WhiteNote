// --- TypeScript interfaces matching backend schemas ---

export interface PaperCard {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  ai_title: string | null;
  ai_abstract: string | null;
  arxiv_primary_category: string | null;
  arxiv_categories: string[] | null;
  created_at: string;
  arxiv_published: string | null;
}

export interface PaperDetail {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  keywords: string[];
  pdf_url: string | null;
  ai_title: string | null;
  ai_title_provider: string | null;
  ai_abstract: string | null;
  ai_abstract_provider: string | null;
  ai_summary: string | null;
  ai_summary_provider: string | null;
  summary_job_status: string | null;
  comic_job_status: string | null;
  favorite_folders: string[];
  favorited_at: string | null;
  is_disliked: boolean;
  created_at: string;
  updated_at: string;
  arxiv_entry_id: string | null;
  arxiv_updated: string | null;
  arxiv_published: string | null;
  arxiv_authors: string[] | null;
  arxiv_comment: string | null;
  arxiv_journal_ref: string | null;
  arxiv_doi: string | null;
  arxiv_primary_category: string | null;
  arxiv_categories: string[] | null;
  arxiv_links: string[] | null;
}

export interface PaginationMeta {
  page: number;
  size: number;
  total: number;
  total_pages: number;
}

export interface PaperListResponse {
  data: PaperCard[];
  pagination: PaginationMeta;
}

// --- API client ---

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface FetchPapersParams {
  page?: number;
  size?: number;
  keyword?: string;
  sort_by?: string;
  order?: string;
}

export function fetchPapers(params: FetchPapersParams = {}): Promise<PaperListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.size) searchParams.set("size", String(params.size));
  if (params.keyword) searchParams.set("keyword", params.keyword);
  if (params.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params.order) searchParams.set("order", params.order);

  const qs = searchParams.toString();
  return apiFetch<PaperListResponse>(`/api/papers${qs ? `?${qs}` : ""}`);
}

export function fetchPaperById(id: string): Promise<PaperDetail> {
  return apiFetch<PaperDetail>(`/api/papers/${id}`);
}
