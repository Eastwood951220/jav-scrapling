/** A scheduled task configuration. */
export interface Schedule {
  _id: string;
  name: string;
  task_ids: string[];
  cron_expression: string;
  enabled: boolean;
  created_at?: string;
}
