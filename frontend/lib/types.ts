export type AgentLog = {
  ts?: string;
  agent: string;
  action: string;
  summary: string;
  output_preview?: string | null;
};

export type ProjectState = {
  id: string;
  genre: string;
  setting: string;
  style: string;
  keywords: string;
  audience: string;
  target_chapters: number;
  outline: string;
  characters: Record<string, unknown>;
  characters_text: string;
  chapters: Record<string, string>;
  created_at: string;
  updated_at: string;
};

export type APIResponse<T> = {
  data: T;
  error?: { code: string; message: string; details?: unknown } | null;
  agent_logs: AgentLog[];
};

export type RetrievedChunkSummary = {
  id: string;
  type: string;
  score: number;
  channel: string;
  chapter_no?: number | null;
  source_id?: string | null;
  snippet: string;
};

export type CriticIssue = {
  issue_type: string;
  severity: string;
  conflict: string;
  evidence_snippet?: string | null;
};

export type ExpandChapterResult = {
  chapter_number: number;
  text: string;
  context_used: string;
  retrieved_context_sources: RetrievedChunkSummary[];
  critic_issues: CriticIssue[];
  revised: boolean;
};

export type RagStats = Record<string, { chunks: number; last_updated_at?: unknown }>;

export type RagPreview = {
  query: string;
  vector_results: RetrievedChunkSummary[];
  keyword_results: RetrievedChunkSummary[];
  merged_candidates: RetrievedChunkSummary[];
  final_selected: RetrievedChunkSummary[];
  final_selected_grouped: Record<string, RetrievedChunkSummary[]>;
  context_string: string;
};
