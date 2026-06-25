import { useEffect, useState, useCallback } from "react";
import {
  Table, Input, Select, Button, Space, Card, message, Drawer, Descriptions, Tag, Typography, InputNumber, Image,
} from "antd";
import { SearchOutlined, ReloadOutlined, DownloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchTaskNames, fetchMovies, fetchMovie } from "./api";
import type { Movie, MovieListResponse } from "./types";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";

export default function Movies() {
  const [taskOptions, setTaskOptions] = useState<{ value: string; label: string }[]>([]);
  const [selectedTask, setSelectedTask] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [ratingMin, setRatingMin] = useState<number | undefined>(undefined);
  const [sortBy, setSortBy] = useState("release_date");
  const [sortOrder, setSortOrder] = useState(-1);
  const [data, setData] = useState<MovieListResponse>({ items: [], total: 0, page: 1, limit: 20, total_pages: 1 });
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const loadTasks = useCallback(async () => {
    try {
      const tasks = await fetchTaskNames();
      const options = tasks.map((t) => ({ value: t.name, label: t.name }));
      setTaskOptions(options);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, []);

  const loadMovies = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const result = await fetchMovies({
        source_task_name: selectedTask,
        search: search || undefined,
        page,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
        rating_min: ratingMin,
      });
      setData(result);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [selectedTask, search, sortBy, sortOrder, ratingMin, pageSize]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  useEffect(() => {
    loadMovies();
  }, [loadMovies]);

  const handleViewDetail = async (id: string) => {
    try {
      const movie = await fetchMovie(id);
      setDetail(movie);
      setDetailOpen(true);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const handleExportMagnets = () => {
    const selectedItems = data.items.filter((item) => selectedRowKeys.includes(item._id));
    const magnets = selectedItems
      .map((item) => item.magnet)
      .filter((m): m is string => Boolean(m));

    if (magnets.length === 0) {
      message.warning("选中项无磁力链接");
      return;
    }

    const blob = new Blob([magnets.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `magnets_${selectedTask ?? "all"}_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(`已导出 ${magnets.length} 条磁力链接`);
  };

  const columns: ColumnsType<Movie> = [
    { title: "番号", dataIndex: "code", key: "code", width: 120 },
    {
      title: "封面",
      dataIndex: "cover",
      key: "cover",
      width: 80,
      render: (url: string) =>
        url ? (
          <Image src={url} width={60} referrerPolicy="no-referrer" placeholder />
        ) : null,
    },
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (text: string, record: Movie) => text || record.source_name || "-",
    },
    {
      title: "评分",
      dataIndex: "rating",
      key: "rating",
      width: 80,
      sorter: true,
      render: (v: number) => (v != null ? v.toFixed(2) : "-"),
    },
    {
      title: "发行日期",
      dataIndex: "release_date",
      key: "release_date",
      width: 110,
      sorter: true,
      defaultSortOrder: "descend",
    },
    {
      title: "时长",
      dataIndex: "duration",
      key: "duration",
      width: 70,
      render: (v: number) => (v != null ? `${v}分` : "-"),
    },
    {
      title: "演员",
      dataIndex: "actors",
      key: "actors",
      width: 180,
      ellipsis: true,
      render: (actors: string[]) =>
        Array.isArray(actors) ? (
          <Space size={[0, 4]} wrap>
            {actors.slice(0, 3).map((a) => <Tag key={a}>{a}</Tag>)}
            {actors.length > 3 && <Tag>+{actors.length - 3}</Tag>}
          </Space>
        ) : null,
    },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      width: 200,
      ellipsis: true,
      render: (tags: string[]) =>
        Array.isArray(tags) ? (
          <Space size={[0, 4]} wrap>
            {tags.slice(0, 3).map((tag) => <Tag key={tag}>{tag}</Tag>)}
            {tags.length > 3 && <Tag>+{tags.length - 3}</Tag>}
          </Space>
        ) : null,
    },
    {
      title: "操作",
      key: "actions",
      width: 80,
      render: (_: unknown, record: Movie) => (
        <Button type="link" size="small" onClick={() => handleViewDetail(record._id)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            style={{ width: 200 }}
            value={selectedTask}
            onChange={setSelectedTask}
            options={taskOptions}
            placeholder="选择任务"
            allowClear
          />
          <Input
            style={{ width: 240 }}
            placeholder="搜索番号、标题..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onPressEnter={() => loadMovies()}
            allowClear
          />
          <InputNumber
            style={{ width: 120 }}
            placeholder="最低评分"
            min={0}
            max={5}
            step={0.1}
            value={ratingMin}
            onChange={(v) => setRatingMin(v ?? undefined)}
          />
          <Select
            style={{ width: 140 }}
            value={`${sortBy}:${sortOrder}`}
            onChange={(v) => {
              const [by, order] = v.split(":");
              setSortBy(by);
              setSortOrder(Number(order));
            }}
            options={[
              { value: "release_date:-1", label: "发行日期 ↓" },
              { value: "release_date:1", label: "发行日期 ↑" },
              { value: "rating:-1", label: "评分 ↓" },
              { value: "rating:1", label: "评分 ↑" },
              { value: "created_at:-1", label: "抓取时间 ↓" },
              { value: "created_at:1", label: "抓取时间 ↑" },
            ]}
          />
          <Button type="primary" onClick={() => loadMovies()}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { setSearch(""); setRatingMin(undefined); setSortBy("release_date"); setSortOrder(-1); loadMovies(1); }}>
            刷新
          </Button>
          <Button
            icon={<DownloadOutlined />}
            disabled={selectedRowKeys.length === 0}
            onClick={handleExportMagnets}
          >
            导出磁力 ({selectedRowKeys.length})
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="_id"
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        pagination={{
          current: data.page,
          total: data.total,
          pageSize: pageSize,
          showSizeChanger: true,
          pageSizeOptions: ["20", "50", "100"],
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, size) => {
            if (size !== pageSize) {
              setPageSize(size);
            }
            loadMovies(page);
          },
          onShowSizeChange: (_current, size) => {
            setPageSize(size);
          },
        }}
        onChange={(_pagination, _filters, sorter) => {
          if (!Array.isArray(sorter) && sorter.column) {
            const field = sorter.field as string;
            // Ant Design cycles: ascend → descend → undefined (neutral)
            // When neutral, reset to default sort
            if (sorter.order === "ascend") {
              setSortBy(field);
              setSortOrder(1);
            } else if (sorter.order === "descend") {
              setSortBy(field);
              setSortOrder(-1);
            } else {
              // Neutral (third click) — reset to default
              setSortBy("release_date");
              setSortOrder(-1);
            }
          }
        }}
        scroll={{ x: 1200 }}
      />

      <Drawer
        title="影片详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={600}
      >
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="番号">{detail.code as string}</Descriptions.Item>
            <Descriptions.Item label="标题">{(detail.title as string) || (detail.source_name as string) || "-"}</Descriptions.Item>
            <Descriptions.Item label="发行日期">{detail.release_date as string}</Descriptions.Item>
            <Descriptions.Item label="时长">{detail.duration != null ? `${detail.duration}分` : "-"}</Descriptions.Item>
            <Descriptions.Item label="评分">{detail.rating != null ? (detail.rating as number).toFixed(2) : "-"}</Descriptions.Item>
            <Descriptions.Item label="导演">{detail.director as string || "-"}</Descriptions.Item>
            <Descriptions.Item label="制作商">{detail.maker as string || "-"}</Descriptions.Item>
            <Descriptions.Item label="系列">{detail.series as string || "-"}</Descriptions.Item>
            <Descriptions.Item label="演员">
              {Array.isArray(detail.actors)
                ? (detail.actors as string[]).map((a) => <Tag key={a}>{a}</Tag>)
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="标签">
              {Array.isArray(detail.tags)
                ? (detail.tags as string[]).map((t) => <Tag key={t}>{t}</Tag>)
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="中文字幕">{detail.has_chinese_sub ? "是" : "否"}</Descriptions.Item>
            <Descriptions.Item label="大小">{detail.size != null ? `${(detail.size as number / 1024).toFixed(1)} GB` : "-"}</Descriptions.Item>
            <Descriptions.Item label="封面">
              {detail.cover as string ? (
                <Image src={detail.cover as string} width={200} referrerPolicy="no-referrer" />
              ) : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="磁力链接">
              {detail.magnet as string ? (
                <Typography.Paragraph copyable style={{ marginBottom: 0, wordBreak: "break-all" }}>
                  {detail.magnet as string}
                </Typography.Paragraph>
              ) : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="来源URL">
              <Typography.Link href={detail.source_url as string} target="_blank">
                {detail.source_url as string}
              </Typography.Link>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
}
