import client from "./client";
import type { Schedule } from "../features/schedules/types";

export type { Schedule } from "../features/schedules/types";

export function fetchSchedules(): Promise<Schedule[]> {
  return client.get("/schedules").then((res) => res.data);
}

export function createSchedule(data: Omit<Schedule, "_id" | "created_at">): Promise<Schedule> {
  return client.post("/schedules", data).then((res) => res.data);
}

export function updateSchedule(id: string, data: Partial<Schedule>): Promise<Schedule> {
  return client.put(`/schedules/${id}`, data).then((res) => res.data);
}

export function deleteSchedule(id: string): Promise<void> {
  return client.delete(`/schedules/${id}`);
}
