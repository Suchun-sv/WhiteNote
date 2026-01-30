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
  favorite_folders: string[];
  is_disliked: boolean;
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

export interface FolderInfo {
  name: string;
  count: number;
}

export interface CollectionListResponse {
  data: FolderInfo[];
}

export interface CollectionMutationResponse {
  success: boolean;
  message: string;
  affected_count: number;
}

// --- API client ---

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  
  // 开发环境下记录请求信息
  if (process.env.NODE_ENV === "development") {
    console.log("[API] Fetching:", url);
    console.log("[API] API_BASE:", API_BASE);
  }
  
  try {
    const res = await fetch(url);
    
    // 开发环境下记录响应信息
    if (process.env.NODE_ENV === "development") {
      console.log("[API] Response status:", res.status, res.statusText);
      console.log("[API] Response headers:", Object.fromEntries(res.headers.entries()));
    }
    
    if (!res.ok) {
      const errorText = await res.text().catch(() => res.statusText);
      const errorMsg = `API error: ${res.status} ${res.statusText}${errorText ? ` - ${errorText}` : ""}`;
      console.error("[API] Request failed:", url, errorMsg);
      throw new Error(errorMsg);
    }
    
    // 检查 Content-Type
    const contentType = res.headers.get("content-type");
    if (process.env.NODE_ENV === "development") {
      console.log("[API] Content-Type:", contentType);
    }
    
    // 尝试解析 JSON
    try {
      const data = await res.json();
      if (process.env.NODE_ENV === "development") {
        console.log("[API] Response data:", data);
      }
      return data as T;
    } catch (jsonError) {
      // JSON 解析失败
      const text = await res.text().catch(() => "");
      console.error("[API] JSON parse error:", {
        url,
        status: res.status,
        contentType,
        responseText: text.substring(0, 200), // 只显示前200个字符
        error: jsonError
      });
      throw new Error(
        `响应解析失败 (${url})。\n` +
        `状态码: ${res.status}\n` +
        `Content-Type: ${contentType || "未知"}\n` +
        `响应内容: ${text.substring(0, 100)}...`
      );
    }
  } catch (error) {
    // 捕获网络错误（如 Failed to fetch）
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      const detailedError = new Error(
        `无法连接到后端服务 (${API_BASE})。请检查：\n` +
        `1. 后端服务是否正在运行？\n` +
        `2. API URL 是否正确？当前: ${API_BASE}\n` +
        `3. 是否存在 CORS 问题？（后端需要允许 ${typeof window !== 'undefined' ? window.location.origin : '前端来源'}）\n` +
        `请求 URL: ${url}`
      );
      console.error("[API] Network error:", {
        url,
        apiBase: API_BASE,
        frontendOrigin: typeof window !== 'undefined' ? window.location.origin : 'unknown',
        error: error.message,
        suggestion: "检查后端服务是否运行，以及 CORS 配置是否正确"
      });
      throw detailedError;
    }
    // 重新抛出其他错误
    console.error("[API] Request error:", url, error);
    throw error;
  }
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const url = `${API_BASE}${path}`;
  
  if (process.env.NODE_ENV === "development") {
    console.log("[API] POST:", url, body);
  }
  
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const errorText = await res.text().catch(() => res.statusText);
      const errorMsg = `API error: ${res.status} ${res.statusText}${errorText ? ` - ${errorText}` : ""}`;
      console.error("[API] POST failed:", url, errorMsg);
      throw new Error(errorMsg);
    }
    return res.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      const detailedError = new Error(
        `无法连接到后端服务 (${API_BASE})。请求 URL: ${url}`
      );
      console.error("[API] Network error:", { url, apiBase: API_BASE, error: error.message });
      throw detailedError;
    }
    console.error("[API] POST error:", url, error);
    throw error;
  }
}

async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const url = `${API_BASE}${path}`;
  
  try {
    const res = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const errorText = await res.text().catch(() => res.statusText);
      throw new Error(`API error: ${res.status} ${res.statusText}${errorText ? ` - ${errorText}` : ""}`);
    }
    return res.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new Error(`无法连接到后端服务 (${API_BASE})。请求 URL: ${url}`);
    }
    throw error;
  }
}

async function apiDelete<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  
  try {
    const res = await fetch(url, { method: "DELETE" });
    if (!res.ok) {
      const errorText = await res.text().catch(() => res.statusText);
      throw new Error(`API error: ${res.status} ${res.statusText}${errorText ? ` - ${errorText}` : ""}`);
    }
    return res.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new Error(`无法连接到后端服务 (${API_BASE})。请求 URL: ${url}`);
    }
    throw error;
  }
}

// --- Papers ---

export interface FetchPapersParams {
  page?: number;
  size?: number;
  keyword?: string;
  sort_by?: string;
  order?: string;
  folder?: string;
}

export function fetchPapers(params: FetchPapersParams = {}): Promise<PaperListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.size) searchParams.set("size", String(params.size));
  if (params.keyword) searchParams.set("keyword", params.keyword);
  if (params.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params.order) searchParams.set("order", params.order);
  if (params.folder) searchParams.set("folder", params.folder);

  const qs = searchParams.toString();
  return apiFetch<PaperListResponse>(`/api/papers${qs ? `?${qs}` : ""}`);
}

export function fetchPaperById(id: string): Promise<PaperDetail> {
  return apiFetch<PaperDetail>(`/api/papers/${id}`);
}

// --- Favorites ---

export function addFavorite(paperId: string, folder: string) {
  return apiPost<{ success: boolean; added: boolean }>(
    `/api/papers/${paperId}/favorite`,
    { folder },
  );
}

export function removeFavorite(paperId: string, folder: string) {
  return apiDelete<{ success: boolean; removed: boolean }>(
    `/api/papers/${paperId}/favorite?folder=${encodeURIComponent(folder)}`,
  );
}

export function markDislike(paperId: string) {
  return apiPost<{ success: boolean }>(`/api/papers/${paperId}/dislike`);
}

export function unmarkDislike(paperId: string) {
  return apiDelete<{ success: boolean }>(`/api/papers/${paperId}/dislike`);
}

// --- Collections ---

export function fetchCollections(): Promise<CollectionListResponse> {
  return apiFetch<CollectionListResponse>("/api/collections");
}

export function createCollection(name: string) {
  return apiPost<CollectionMutationResponse>("/api/collections", { name });
}

export function renameCollection(oldName: string, newName: string) {
  return apiPut<CollectionMutationResponse>(
    `/api/collections/${encodeURIComponent(oldName)}`,
    { new_name: newName },
  );
}

export function deleteCollection(folderName: string) {
  return apiDelete<CollectionMutationResponse>(
    `/api/collections/${encodeURIComponent(folderName)}`,
  );
}

// --- Chat ---

export interface ChatMessageRequest {
  message: string;
  session_id?: string;
  language?: string;
}

export interface ChatMessageResponse {
  session_id: string;
  reply: string;
}

export interface ChatSessionInfo {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatHistoryResponse {
  sessions: ChatSessionInfo[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface SessionMessagesResponse {
  session_id: string;
  title: string | null;
  messages: ChatMessage[];
}

export function sendChatMessage(
  paperId: string,
  body: ChatMessageRequest
): Promise<ChatMessageResponse> {
  return apiPost<ChatMessageResponse>(`/api/chat/${paperId}`, body);
}

export function getChatHistory(paperId: string): Promise<ChatHistoryResponse> {
  return apiFetch<ChatHistoryResponse>(`/api/chat/${paperId}/history`);
}

export function getSessionMessages(
  paperId: string,
  sessionId: string
): Promise<SessionMessagesResponse> {
  return apiFetch<SessionMessagesResponse>(
    `/api/chat/${paperId}/sessions/${sessionId}`
  );
}
