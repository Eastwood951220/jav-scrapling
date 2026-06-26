import { Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { TaskFile } from "../types";

function formatFileSize(bytes?: number): string {
  if (bytes == null) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default function FilesTable({ files }: { files: TaskFile[] }) {
  const columns: ColumnsType<TaskFile> = [
    { title: "文件名", dataIndex: "filename", key: "filename", ellipsis: true },
    { title: "路径", dataIndex: "path", key: "path", ellipsis: true },
    { title: "大小", dataIndex: "size", key: "size", width: 100, render: (v?: number) => formatFileSize(v) },
    { title: "扩展名", dataIndex: "extension", key: "extension", width: 80 },
    { title: "分类", dataIndex: "category", key: "category", width: 100 },
    { title: "结果", dataIndex: "result", key: "result", width: 100 },
  ];

  return (
    <Table<TaskFile>
      rowKey="path"
      columns={columns}
      dataSource={files}
      size="small"
      pagination={{ pageSize: 20, showSizeChanger: true }}
      scroll={{ x: 800 }}
    />
  );
}
