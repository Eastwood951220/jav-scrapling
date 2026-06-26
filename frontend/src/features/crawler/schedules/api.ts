import client from "@/shared/api/client";
import type { Schedule } from "./types";

export type { Schedule } from "./types";

export function fetchSchedules(): Promise<Schedule[]> {
  return client.get("/crawler/schedules").then((res) => res.data);
}

export function createSchedule(data: Omit<Schedule, "_id" | "created_at">): Promise<Schedule> {
  return client.post("/crawler/schedules", data).then((res) => res.data);
}

export function updateSchedule(id: string, data: Partial<Schedule>): Promise<Schedule> {
  return client.put(`/crawler/schedules/${id}`, data).then((res) => res.data);
}

export function deleteSchedule(id: string): Promise<void> {
  return client.delete(`/crawler/schedules/${id}`);
}
