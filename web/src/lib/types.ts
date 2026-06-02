export interface JobStatus {
  status: string;
  date?: string;
  time?: string;
  error?: string;
  duration_seconds?: number;
  steps?: Array<{ name: string; status: string; error?: string }>;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  scripts?: Record<string, boolean>;
  indexes?: Record<string, boolean>;
  jobs?: {
    daily?: JobStatus;
    weekly?: JobStatus;
    sync?: JobStatus;
  };
}

export interface MetricsResponse {
  success: boolean;
  health_score: number;
  health_grade: string;
  inbox_count: number;
  orphan_notes: number;
  untagged_notes: number;
  stale_seedlings: number;
  atomic_notes_count: number;
  total_notes: number;
  vectorized_notes: number;
  total_links: number;
  calculated_at: string;
  error?: string;
}

export interface CaptureTextRequest {
  content: string;
  source?: string;
  title?: string;
  tags?: string[];
}

export interface CaptureTextResponse {
  success: boolean;
  file?: string;
  error?: string;
}

export interface InboxItem {
  file: string;
  created: string;
  source: string;
  type: string;
  title: string;
  suggested_action: string;
  content_length: number;
}

export interface InboxResponse {
  success: boolean;
  items: InboxItem[];
  total: number;
}

export interface SearchResult {
  path: string;
  title: string;
  score: number;
  snippet?: string;
  type?: string;
}

export interface AskRequest {
  question: string;
  limit?: number;
  save_category?: string;
}

export interface AskResponse {
  success: boolean;
  query: string;
  answer: string;
  references: SearchResult[];
  notes_count: number;
  saved?: string;
}

export interface BriefResponse {
  success: boolean;
  date?: string;
  week?: string;
  content?: string;
  dry_run: boolean;
  error?: string;
}