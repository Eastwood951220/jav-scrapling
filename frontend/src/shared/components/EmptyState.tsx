import { Empty } from "antd";

interface EmptyStateProps {
  description?: string;
}

/**
 * Consistent empty-state placeholder for tables and lists.
 * Defaults to "暂无数据" (No Data).
 */
export default function EmptyState({ description = "暂无数据" }: EmptyStateProps) {
  return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={description} />;
}
