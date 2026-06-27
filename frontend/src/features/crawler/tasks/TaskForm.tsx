import { useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Form, Input, Switch, Select, Button, Card, Row, Col, message } from "antd";
import { PlusOutlined, MinusCircleOutlined, SearchOutlined } from "@ant-design/icons";
import { createTask, fetchTask, updateTask, extractName } from "./api";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import type { TaskCreatePayload, TaskUrlEntry } from "./types";

type UrlType = "actors" | "series" | "makers" | "directors" | "video_codes" | "lists" | "tags" | "search";

interface CondParamConfig {
  magnet: string;
  sub: string;
  both: string;
}

const URL_TYPE_PARAMS: Record<string, CondParamConfig> = {
  actors: { magnet: "t=d", sub: "t=c", both: "t=c,d" },
  series: { magnet: "f=download", sub: "f=cnsub", both: "f=cnsub" },
  makers: { magnet: "f=download", sub: "f=cnsub", both: "f=cnsub" },
  directors: { magnet: "f=download", sub: "f=cnsub", both: "f=cnsub" },
  video_codes: { magnet: "f=download", sub: "f=cnsub", both: "f=cnsub" },
  lists: { magnet: "f=download", sub: "f=cnsub", both: "f=cnsub" },
  tags: { magnet: "c10=1", sub: "c10=2", both: "c10=1,2" },
  search: { magnet: "f=download", sub: "f=cnsub", both: "f=cnsub" },
};

const SORT_OPTIONS = [
  { value: 0, label: "日期降序" },
  { value: 5, label: "番号降序" },
];

const SEARCH_SORT_OPTIONS = [
  { value: 0, label: "按相关度" },
  { value: 1, label: "按发布日期" },
];

const URL_TYPE_LABELS: Record<UrlType, string> = {
  actors: "演员 (actors)",
  series: "系列 (series)",
  makers: "片商 (makers)",
  directors: "导演 (directors)",
  video_codes: "番号 (video_codes)",
  lists: "列表 (lists)",
  tags: "标签 (tags)",
  search: "搜索 (search)",
};

/** 从 URL 路径自动检测 URL 类型 */
export function detectUrlType(url: string): UrlType | null {
  try {
    const u = new URL(url);
    const path = u.pathname;

    if (path.startsWith("/search")) return "search";
    if (path.startsWith("/actors/")) return "actors";
    if (path.startsWith("/series/")) return "series";
    if (path.startsWith("/makers/")) return "makers";
    if (path.startsWith("/directors/")) return "directors";
    if (path.startsWith("/video_codes/")) return "video_codes";
    if (path.startsWith("/lists/")) return "lists";
    if (path === "/tags" || path.startsWith("/tags/")) return "tags";

    return null;
  } catch {
    return null;
  }
}

const PARAM_KEYS = ["t", "f", "c10", "sort", "page", "sb"] as const;

function stripQueryParams(rawUrl: string): string {
  try {
    const u = new URL(rawUrl);
    PARAM_KEYS.forEach((k) => u.searchParams.delete(k));
    const qs = u.searchParams.toString();
    return u.pathname + (qs ? `?${qs}` : "");
  } catch {
    return rawUrl;
  }
}

function buildFinalUrl(
  baseUrl: string,
  urlType: UrlType,
  hasMagnet: boolean,
  hasSub: boolean,
  sortType: number,
): string {
  if (!baseUrl) return baseUrl;

  // search 类型不使用 URL_TYPE_PARAMS，直接处理
  if (urlType === "search") {
    const stripped = stripQueryParams(baseUrl);
    const parts: string[] = [];

    if (hasMagnet && hasSub) {
      // 同时勾选磁力和字幕时，优先显示磁力
      parts.push("f=download");
    } else if (hasMagnet) {
      parts.push("f=download");
    } else if (hasSub) {
      parts.push("f=cnsub");
    }

    // sb 排序参数
    parts.push(`sb=${sortType}`);

    if (parts.length === 0) return stripped;

    try {
      const u = new URL(baseUrl);
      const base = u.origin + stripped;
      return base + (stripped.includes("?") ? "&" : "?") + parts.join("&");
    } catch {
      return stripped + (stripped.includes("?") ? "&" : "?") + parts.join("&");
    }
  }

  if (!(urlType in URL_TYPE_PARAMS)) return baseUrl;

  const stripped = stripQueryParams(baseUrl);
  const parts: string[] = [];

  const cfg = URL_TYPE_PARAMS[urlType];
  if (hasMagnet && hasSub && cfg.both) {
    parts.push(cfg.both);
  } else if (hasMagnet) {
    parts.push(cfg.magnet);
  } else if (hasSub) {
    parts.push(cfg.sub);
  }

  if ((urlType === "actors" || urlType === "video_codes") && sortType !== 0) {
    parts.push(`sort=${sortType}`);
  }

  if (parts.length === 0) return stripped;

  try {
    const u = new URL(baseUrl);
    const base = u.origin + stripped;
    return base + (stripped.includes("?") ? "&" : "?") + parts.join("&");
  } catch {
    return stripped + (stripped.includes("?") ? "&" : "?") + parts.join("&");
  }
}

/** A single URL entry form card. */
function UrlEntryCard({
  index,
  remove,
  onNameExtracted,
  onUrlTypeDetected,
}: {
  index: number;
  remove?: () => void;
  onNameExtracted?: (index: number, name: string) => void;
  onUrlTypeDetected?: (index: number, urlType: UrlType) => void;
}) {
  const [extracting, setExtracting] = useState(false);

  return (
    <Card
      size="small"
      title={`URL ${index + 1}`}
      extra={remove && (
        <Button
          type="text"
          danger
          icon={<MinusCircleOutlined />}
          onClick={remove}
          size="small"
        />
      )}
      style={{ marginBottom: 12 }}
    >
      <Form.Item noStyle shouldUpdate={(prev, cur) => {
        const prevUrl = prev.urls?.[index]?.url;
        const curUrl = cur.urls?.[index]?.url;
        return prevUrl !== curUrl;
      }}>
        {({ getFieldValue }) => {
          const url = getFieldValue(["urls", index, "url"]) as string;
          const detected = url ? detectUrlType(url) : null;
          const currentType = getFieldValue(["urls", index, "url_type"]) as UrlType | undefined;

          // URL 变化时自动更新 url_type
          if (detected && detected !== currentType && onUrlTypeDetected) {
            setTimeout(() => onUrlTypeDetected(index, detected), 0);
          }

          return (
            <>
              <Form.Item
                name={[index, "url"]}
                label="URL"
                rules={[{ required: true, message: "请输入URL" }]}
              >
                <Input placeholder="https://javdb.com/actors/..." />
              </Form.Item>

              <Form.Item label="URL类型">
                <Input
                  value={detected ? URL_TYPE_LABELS[detected] : (url ? "无法识别" : "请输入URL")}
                  disabled
                />
              </Form.Item>

              {/* 隐藏字段存储 url_type 值 */}
              <Form.Item name={[index, "url_type"]} hidden>
                <Input />
              </Form.Item>
            </>
          );
        }}
      </Form.Item>

      <Form.Item noStyle shouldUpdate={(prev, cur) => {
        const prevUrls = prev.urls?.[index];
        const curUrls = cur.urls?.[index];
        return prevUrls?.url_type !== curUrls?.url_type;
      }}>
        {({ getFieldValue }) => {
          const urlType = getFieldValue(["urls", index, "url_type"]) as UrlType;
          const showConditions = urlType in URL_TYPE_PARAMS;
          const showSort = urlType === "video_codes" || urlType === "search";
          const sortOptions = urlType === "search" ? SEARCH_SORT_OPTIONS : SORT_OPTIONS;

          if (!showConditions) return null;

          return (
            <>
              <Form.Item name={[index, "has_magnet"]} label="含磁力链接" valuePropName="checked">
                <Switch />
              </Form.Item>

              <Form.Item name={[index, "has_chinese_sub"]} label="含中文字幕" valuePropName="checked">
                <Switch />
              </Form.Item>

              {showSort && (
                <Form.Item name={[index, "sort_type"]} label="排序方式">
                  <Select options={sortOptions} />
                </Form.Item>
              )}
            </>
          );
        }}
      </Form.Item>

      <Form.Item noStyle shouldUpdate>
        {({ getFieldValue }) => {
          const baseUrl: string = getFieldValue(["urls", index, "url"]) ?? "";
          const urlType = getFieldValue(["urls", index, "url_type"]) as UrlType;
          const hasMagnet = (getFieldValue(["urls", index, "has_magnet"]) as boolean) ?? false;
          const hasSub = (getFieldValue(["urls", index, "has_chinese_sub"]) as boolean) ?? false;
          const sortType = (getFieldValue(["urls", index, "sort_type"]) as number) ?? 0;
          const finalUrl = buildFinalUrl(baseUrl, urlType, hasMagnet, hasSub, sortType);

          return (
            <Form.Item label="最终 URL 预览">
              <Input value={finalUrl} disabled />
            </Form.Item>
          );
        }}
      </Form.Item>

      {/* url_name display (read-only) */}
      <Form.Item noStyle shouldUpdate={(prev, cur) => {
        const prevUrls = prev.urls?.[index];
        const curUrls = cur.urls?.[index];
        return prevUrls?.url_name !== curUrls?.url_name;
      }}>
        {({ getFieldValue }) => {
          const urlName = getFieldValue(["urls", index, "url_name"]) as string | undefined;
          if (!urlName) return null;
          return (
            <Form.Item label="URL 名称">
              <Input value={urlName} disabled />
            </Form.Item>
          );
        }}
      </Form.Item>

      <Form.Item noStyle shouldUpdate={(prev, cur) => {
        const prevUrls = prev.urls?.[index];
        const curUrls = cur.urls?.[index];
        return prevUrls?.url !== curUrls?.url || prevUrls?.url_type !== curUrls?.url_type;
      }}>
        {({ getFieldValue }) => {
          const url = getFieldValue(["urls", index, "url"]) as string;
          const urlType = getFieldValue(["urls", index, "url_type"]) as string;
          const canExtract = url && urlType && urlType !== "tags";

          return (
            <Button
              icon={<SearchOutlined />}
              loading={extracting}
              disabled={!canExtract}
              onClick={async () => {
                if (!url || !urlType) return;
                setExtracting(true);
                try {
                  const result = await extractName(url, urlType);
                  if (result.name && onNameExtracted) {
                    onNameExtracted(index, result.name);
                  } else if (!result.name) {
                    message.warning("未能提取到名称");
                  }
                } catch (e: unknown) {
                  message.error(getErrorMessage(e));
                } finally {
                  setExtracting(false);
                }
              }}
            >
              获取名称
            </Button>
          );
        }}
      </Form.Item>
    </Card>
  );
}

export default function TaskForm() {
  const { id } = useParams({ strict: false }) as { id?: string };
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isEdit || !id) return;

    setLoading(true);
    fetchTask(id)
      .then((task) => {
        form.setFieldsValue({
          name: task.name,
          urls: task.urls?.map((u) => ({
            url: u.url,
            url_type: u.url_type,
            has_magnet: u.has_magnet ?? true,
            has_chinese_sub: u.has_chinese_sub ?? false,
            sort_type: u.sort_type ?? 0,
            url_name: u.url_name ?? "",
          })) ?? [],
          is_skip: task.is_skip,
        });
      })
      .catch((e) => message.error(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [id, isEdit, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    // Validate URL uniqueness
    const urlEntries = values.urls as Record<string, unknown>[];
    const urlSet = new Set<string>();
    for (let i = 0; i < urlEntries.length; i++) {
      const url = urlEntries[i].url as string;
      if (url && urlSet.has(url)) {
        message.error(`URL 重复: ${url}`);
        setSubmitting(false);
        return;
      }
      if (url) urlSet.add(url);
    }

    setSubmitting(true);
    try {
      // Auto-extract missing url_name values
      const enrichedEntries: TaskUrlEntry[] = [];
      for (const entry of urlEntries) {
        const urlType = entry.url_type as string;
        let urlName = entry.url_name as string | undefined;

        // If no url_name and the type supports extraction, auto-fetch
        if (!urlName && urlType && urlType !== "tags") {
          try {
            const result = await extractName(entry.url as string, urlType);
            if (result.name) {
              urlName = result.name;
            }
          } catch {
            // Extraction failure should not block submission
          }
        }

        enrichedEntries.push({
          url: entry.url as string,
          url_type: urlType,
          has_magnet: (entry.has_magnet as boolean) ?? false,
          has_chinese_sub: (entry.has_chinese_sub as boolean) ?? false,
          sort_type: (entry.sort_type as number) ?? 0,
          url_name: urlName ?? "",
        });
      }

      const payload: TaskCreatePayload = {
        name: values.name as string,
        urls: enrichedEntries,
        is_skip: (values.is_skip as boolean) ?? false,
      };

      if (isEdit && id) {
        await updateTask(id, payload);
        message.success("任务已更新");
      } else {
        await createTask(payload);
        message.success("任务已创建");
      }
      navigate({ to: "/crawler/tasks" });
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <FullPageSpinner />;

  return (
    <Card title={isEdit ? "编辑任务" : "新建任务"}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          urls: [{ has_magnet: true, has_chinese_sub: false, sort_type: 0 }],
          is_skip: false,
        }}
      >
        <Row gutter={24}>
          <Col flex="auto">
            <Form.Item name="name" label="任务名称" rules={[{ required: true, message: "请输入任务名称" }]}>
              <Input placeholder="例如：某演员名称" />
            </Form.Item>
          </Col>
          <Col flex="120px">
            <Form.Item name="is_skip" label="启用状态" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="URL 列表" required style={{ marginBottom: 8 }}>
        </Form.Item>

        <Form.List name="urls">
          {(fields, { add, remove }) => (
            <Row gutter={[16, 16]}>
              {fields.map((field) => (
                <Col key={field.key} xs={24} lg={12} xl={8}>
                  <UrlEntryCard
                    index={field.name}
                    remove={fields.length > 1 ? () => remove(field.name) : undefined}
                    onNameExtracted={(idx, name) => {
                      // Save url_name to the corresponding URL entry
                      const urls = form.getFieldValue("urls") ?? [];
                      const updated = urls.map((u: Record<string, unknown>, i: number) =>
                        i === idx ? { ...u, url_name: name } : u,
                      );
                      form.setFieldsValue({ urls: updated });

                      // Auto-fill task name (only when empty)
                      const currentName = form.getFieldValue("name");
                      if (!currentName) {
                        form.setFieldsValue({ name });
                      }
                    }}
                    onUrlTypeDetected={(idx, urlType) => {
                      const urls = form.getFieldValue("urls") ?? [];
                      const updated = urls.map((u: Record<string, unknown>, i: number) =>
                        i === idx ? { ...u, url_type: urlType } : u,
                      );
                      form.setFieldsValue({ urls: updated });
                    }}
                  />
                </Col>
              ))}
              <Col xs={24} lg={12} xl={8}>
                <Button
                  type="dashed"
                  onClick={() => add({ has_magnet: true, has_chinese_sub: false, sort_type: 0 })}
                  icon={<PlusOutlined />}
                  style={{ height: "100%", minHeight: 200, width: "100%" }}
                >
                  添加 URL
                </Button>
              </Col>
            </Row>
          )}
        </Form.List>

        <Form.Item style={{ marginTop: 24 }}>
          <Button type="primary" htmlType="submit" loading={submitting}>
            {isEdit ? "更新" : "创建"}
          </Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate({ to: "/crawler/tasks" })}>
            取消
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
