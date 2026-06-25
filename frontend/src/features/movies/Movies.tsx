import { useEffect, useState, useCallback } from "react";
import {
  Table, Input, Select, Button, Space, Card, message, Drawer, Descriptions, Tag, Typography,
} from "antd";
import { SearchOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchCollections, fetchMovies, fetchMovie, MovieListResponse } from "./api";
import type { Movie } from "@/shared/types/common";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";

export default function Movies() {
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("movies");
  const [search, setSearch] = useState("");
  const [data, setData] = useState<MovieListResponse>({ items: [], total: 0, page: 1, limit: 20, total_pages: 1 });
  const [loading, setLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

  const loadCollections = useCallback(async () => {
    try {
      const cols = await fetchCollections();
      setCollections(cols);
      if (cols.length > 0 && !cols.includes(selectedCollection)) {
        setSelectedCollection(cols[0]);
      }
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, []);

  const loadMovies = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const result = await fetchMovies({
        collection: selectedCollection,
        search: search || undefined,
        page,
        limit: 20,
      });
      setData(result);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [selectedCollection, search]);

  useEffect(() => {
    loadCollections();
  }, [loadCollections]);

  useEffect(() => {
    loadMovies();
  }, [loadMovies]);

  const handleViewDetail = async (id: string) => {
    try {
      const movie = await fetchMovie(id, selectedCollection);
      setDetail(movie);
      setDetailOpen(true);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const columns: ColumnsType<Movie> = [
    { title: "番号", dataIndex: "code", key: "code", width: 140 },
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (text: string) => text || "-",
    },
    { title: "日期", dataIndex: "release_date", key: "release_date", width: 110 },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      width: 250,
      render: (tags: string[]) =>
        Array.isArray(tags) ? (
          <Space size={[0, 4]} wrap>
            {tags.slice(0, 5).map((tag: string) => (
              <Tag key={tag}>{tag}</Tag>
            ))}
            {tags.length > 5 && <Tag>+{tags.length - 5}</Tag>}
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
            value={selectedCollection}
            onChange={setSelectedCollection}
            options={collections.map((c) => ({ value: c, label: c }))}
            placeholder="选择集合"
          />
          <Input
            style={{ width: 300 }}
            placeholder="搜索番号、标题..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onPressEnter={() => loadMovies()}
            allowClear
          />
          <Button type="primary" onClick={() => loadMovies()}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { setSearch(""); loadMovies(1); }}>
            刷新
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="_id"
        loading={loading}
        pagination={{
          current: data.page,
          total: data.total,
          pageSize: data.limit,
          onChange: (page) => loadMovies(page),
          showTotal: (total) => `共 ${total} 条`,
        }}
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
            <Descriptions.Item label="标题">{detail.title as string}</Descriptions.Item>
            <Descriptions.Item label="日期">{detail.date as string}</Descriptions.Item>
            <Descriptions.Item label="时长">{detail.length as string}</Descriptions.Item>
            <Descriptions.Item label="导演">{detail.director as string}</Descriptions.Item>
            <Descriptions.Item label="制作商">{detail.maker as string}</Descriptions.Item>
            <Descriptions.Item label="发行商">{detail.publisher as string}</Descriptions.Item>
            <Descriptions.Item label="演员">
              {Array.isArray(detail.actors)
                ? (detail.actors as string[]).map((a: string) => <Tag key={a}>{a}</Tag>)
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="标签">
              {Array.isArray(detail.tags)
                ? (detail.tags as string[]).map((t: string) => <Tag key={t}>{t}</Tag>)
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="封面">
              {detail.cover as string ? (
                <img
                  src={detail.cover as string}
                  alt="cover"
                  style={{ maxWidth: 200 }}
                  referrerPolicy="no-referrer"
                />
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
