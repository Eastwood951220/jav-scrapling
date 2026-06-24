import client from "./client";

export interface FilterConfig {
  only_chinese: boolean;
  exclude_multi_person: boolean;
  extra_filters?: Record<string, unknown>;
}

export interface CrawlTask {
  _id: string;
  name: string;
  url: string;
  url_type: string;
  is_skip: boolean;
  max_list_pages: number;
  filter: FilterConfig;
  source?: string;
  final_url?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TaskCreatePayload {
  name: string;
  url: string;
  url_type: string;
  is_skip?: boolean;
  max_list_pages?: number;
  filter?: FilterConfig;
}

export function fetchTasks(): Promise<CrawlTask[]> {
  return client.get("/tasks").then((res) => res.data);
}

export function fetchTask(id: string): Promise<CrawlTask> {
  return client.get(`/tasks/${id}`).then((res) => res.data);
}

export function createTask(data: TaskCreatePayload): Promise<CrawlTask> {
  return client.post("/tasks", data).then((res) => res.data);
}

export function updateTask(id: string, data: Partial<TaskCreatePayload>): Promise<CrawlTask> {
  return client.put(`/tasks/${id}`, data).then((res) => res.data);
}

export function deleteTask(id: string): Promise<{ deleted: boolean }> {
  return client.delete(`/tasks/${id}`).then((res) => res.data);
}

export function runTask(id: string): Promise<unknown> {
  return client.post(`/tasks/${id}/run`).then((res) => res.data);
}
