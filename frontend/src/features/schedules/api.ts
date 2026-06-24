// Re-exported from legacy api/ directory.
// Once api/schedules.ts migrates, move the source here.
export {
  fetchSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
} from "../../api/schedules";
export type { Schedule } from "../../api/schedules";
