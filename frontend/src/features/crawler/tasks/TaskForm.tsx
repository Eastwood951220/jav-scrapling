import { useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Form, Input, Switch, Select, Button, Card, message } from "antd";
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
  series: { magnet: "f=download", sub: "f=cnsub", both: "" },
  makers: { magnet: "f=download", sub: "f=cnsub", both: "" },
  directors: { magnet: "f=download", sub: "f=cnsub", both: "" },
  video_codes: { magnet: "f=download", sub: "f=cnsub", both: "" },
  lists: { magnet: "f=download", sub: "f=cnsub", both: "" },
  tags: { magnet: "c10=1", sub: "c10=2", both: "c10=1,2" },
};

const SORT_OPTIONS = [
  { value: 0, label: "日期降序" },
  { value: 5, label: "番号降序" },
];

const URL_TYPE_OPTIONS = [
  { value: "actors", label: "演员 (actors)" },
  { value: "series", label: "系列 (series)" },
  { value: "makers", label: "片商 (makers)" },
  { value: "directors", label: "导演 (directors)" },
  { value: "video_codes", label: "番号 (video_codes)" },
  { value: "lists", label: "列表 (lists)" },
  { value: "tags", label: "标签 (tags)" },
  { value: "search", label: "搜索 (search)" },
];

const PARAM_KEYS = ["t", "f", "c10", "sort", "page"] as const;

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
  if (!baseUrl || !(urlType in URL_TYPE_PARAMS)) return baseUrl;

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
}: {
  index: number;
  remove?: () => void;
  onNameExtracted?: (index: number, name: string) => void;
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
      <Form.Item
        name={[index, "url"]}
        label="URL"
        rules={[{ required: true, message: "请输入URL" }]}
      >
        <Input placeholder="https://javdb.com/actors/..." />
      </Form.Item>

      <Form.Item
        name={[index, "url_type"]}
        label="URL类型"
        rules={[{ required: true }]}
      >
        <Select options={URL_TYPE_OPTIONS} />
      </Form.Item>

      <Form.Item noStyle shouldUpdate={(prev, cur) => {
        const prevUrls = prev.urls?.[index];
        const curUrls = cur.urls?.[index];
        return prevUrls?.url_type !== curUrls?.url_type;
      }}>
        {({ getFieldValue }) => {
          const urlType = getFieldValue(["urls", index, "url_type"]) as UrlType;
          const showConditions = urlType in URL_TYPE_PARAMS;
          const showSort = urlType === "video_codes";

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
                  <Select options={SORT_OPTIONS} />
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
          const canExtract = url && urlType && urlType !== "search" && urlType !== "tags";

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
        if (!urlName && urlType && urlType !== "search" && urlType !== "tags") {
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
    <Card title={isEdit ? "编辑任务" : "新建任务"} style={{ maxWidth: 800 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          urls: [{ url_type: "actors", has_magnet: true, has_chinese_sub: false, sort_type: 0 }],
          is_skip: false,
        }}
      >
        <Form.Item name="name" label="任务名称" rules={[{ required: true, message: "请输入任务名称" }]}>
          <Input placeholder="例如：某演员名称" />
        </Form.Item>

        <Form.Item label="URL 列表" required>
          <Form.List name="urls">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <UrlEntryCard
                    key={field.key}
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
                  />
                ))}
                <Button
                  type="dashed"
                  onClick={() => add({ url_type: "actors", has_magnet: true, has_chinese_sub: false, sort_type: 0 })}
                  icon={<PlusOutlined />}
                  block
                >
                  添加 URL
                </Button>
              </>
            )}
          </Form.List>
        </Form.Item>

        <Form.Item name="is_skip" label="禁用此任务" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Form.Item>
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
