/** TypeScript types matching backend Pydantic schemas. */

export interface TaskCreate {
  description: string;
  project_id?: string | null;
}

export interface TaskResponse {
  id: string;
  project_id: string | null;
  description: string;
  status: TaskStatus;
  result_summary: string | null;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface StepResponse {
  id: string;
  order: number;
  title: string;
  description: string;
  status: StepStatus;
  retry_count: number;
  created_at: string;
}

export interface CodeArtifactResponse {
  id: string;
  file_path: string;
  content: string;
  language: string | null;
  version: number;
  created_at: string;
}

export interface StepDetail extends StepResponse {
  code_artifacts: CodeArtifactResponse[];
}

export interface TaskDetail extends TaskResponse {
  steps: StepDetail[];
}

export interface PaginatedTasks {
  items: TaskResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface ProjectResponse {
  id: string;
  name: string;
  root_path: string;
  description: string | null;
  indexed_at: string | null;
  created_at: string;
}

export interface IndexRequest {
  directory: string;
  project_name: string;
  description?: string | null;
}

export interface IndexResponse {
  project_id: string;
  project_name: string;
  files_indexed: number;
  message: string;
}

export interface SearchRequest {
  query: string;
  project_id?: string | null;
  top_k?: number;
}

export interface SearchResultItem {
  file_path: string;
  start_line: number;
  end_line: number;
  code_snippet: string;
  chunk_type: string;
  name: string;
  language: string;
  similarity_score: number;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
}

export interface WSMessage {
  event: "task_status" | "step_status" | "done" | "error";
  data: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, string>;
}

export type TaskStatus =
  | "pending"
  | "planning"
  | "in_progress"
  | "reviewing"
  | "completed"
  | "failed"
  | "cancelled";

export type StepStatus =
  | "pending"
  | "generating"
  | "reviewing"
  | "executing"
  | "passed"
  | "failed"
  | "skipped";
