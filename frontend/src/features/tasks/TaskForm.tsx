import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Form, Input, InputNumber, Switch, Select, Button, Card, message } from "antd";
import { createTask, fetchTask, updateTask } from "./api";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import type { TaskCreatePayload } from "./types";

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

/** Parse query string into a Map preserving key order. */
function parseUrlParams(rawUrl: string): Map<string, string> {
  const params = new Map<string, string>();
  try {
    const u = new URL(rawUrl);
    u.searchParams.forEach((v, k) => params.set(k, v));
  } catch {
    // invalid URL, return empty
  }
  return params;
}

/** Detect has_magnet / has_chinese_sub / sort_type from existing URL params. */
function detectOptionsFromUrl(
  rawUrl: string,
  urlType: UrlType,
): { hasMagnet: boolean; hasSub: boolean; sortType: number } {
  const params = parseUrlParams(rawUrl);
  let hasMagnet = false;
  let hasSub = false;
  let sortType = 0;

  if (urlType === "actors") {
    const t = params.get("t") ?? "";
    hasMagnet = t.includes("d");
    hasSub = t.includes("c");
    sortType = Number(params.get("sort") ?? "0");
  } else if (urlType === "tags") {
    const c10 = params.get("c10") ?? "";
    hasMagnet = c10.includes("1");
    hasSub = c10.includes("2");
  } else if (urlType in URL_TYPE_PARAMS) {
    const f = params.get("f") ?? "";
    hasMagnet = f === "download";
    hasSub = f === "cnsub";
    if (urlType === "video_codes") {
      sortType = Number(params.get("sort") ?? "0");
    }
  }

  return { hasMagnet, hasSub, sortType };
}

/** Strip known query params from URL, keeping only the path. */
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

/** Build the final URL from base path + condition options. */
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

  // Use the origin from baseUrl if available, otherwise just path
  try {
    const u = new URL(baseUrl);
    const base = u.origin + stripped;
    return base + (stripped.includes("?") ? "&" : "?") + parts.join("&");
  } catch {
    return stripped + (stripped.includes("?") ? "&" : "?") + parts.join("&");
  }
}

export default function TaskForm() {
  const { id } = useParams({ strict: false }) as { id?: string };
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleUrlBlur = useCallback(() => {
    const url: string = form.getFieldValue("url") ?? "";
    const urlType = form.getFieldValue("url_type") as UrlType;
    if (!url || !(urlType in URL_TYPE_PARAMS)) return;

    const detected = detectOptionsFromUrl(url, urlType);
    form.setFieldsValue({
      has_magnet: detected.hasMagnet,
      has_chinese_sub: detected.hasSub,
      sort_type: detected.sortType,
    });
  }, [form]);

  useEffect(() => {
    if (!isEdit || !id) return;

    setLoading(true);
    fetchTask(id)
      .then((task) => {
        form.setFieldsValue({
          name: task.name,
          url: task.url,
          url_type: task.url_type,
          is_skip: task.is_skip,
          max_list_pages: task.max_list_pages,
          has_magnet: task.has_magnet ?? true,
          has_chinese_sub: task.has_chinese_sub ?? false,
          sort_type: task.sort_type ?? 0,
        });
      })
      .catch((e) => message.error(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [id, isEdit, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true);
    try {
      const urlType = values.url_type as UrlType;
      const finalUrl = buildFinalUrl(
        values.url as string,
        urlType,
        (values.has_magnet as boolean) ?? false,
        (values.has_chinese_sub as boolean) ?? false,
        (values.sort_type as number) ?? 0,
      );

      const payload: TaskCreatePayload = {
        name: values.name as string,
        url: values.url as string,
        url_type: urlType,
        is_skip: (values.is_skip as boolean) ?? false,
        max_list_pages: (values.max_list_pages as number) ?? 50,
        has_magnet: (values.has_magnet as boolean) ?? false,
        has_chinese_sub: (values.has_chinese_sub as boolean) ?? false,
        sort_type: (values.sort_type as number) ?? 0,
        final_url: finalUrl,
      };

      if (isEdit && id) {
        await updateTask(id, payload);
        message.success("任务已更新");
      } else {
        await createTask(payload);
        message.success("任务已创建");
      }
      navigate({ to: "/tasks" });
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <FullPageSpinner />;

  return (
    <Card title={isEdit ? "编辑任务" : "新建任务"} style={{ maxWidth: 700 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          url_type: "actors",
          is_skip: false,
          max_list_pages: 50,
          has_magnet: true,
          has_chinese_sub: false,
          sort_type: 0,
        }}
      >
        <Form.Item name="name" label="任务名称" rules={[{ required: true, message: "请输入任务名称" }]}>
          <Input placeholder="例如：某演员名称" />
        </Form.Item>

        <Form.Item name="url" label="URL" rules={[{ required: true, message: "请输入URL" }]}>
          <Input placeholder="https://javdb.com/actors/..." onBlur={handleUrlBlur} />
        </Form.Item>

        <Form.Item name="url_type" label="URL类型" rules={[{ required: true }]}>
          <Select options={URL_TYPE_OPTIONS} />
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, cur) => prev.url_type !== cur.url_type}>
          {({ getFieldValue }) => {
            const urlType = getFieldValue("url_type") as UrlType;
            const showConditions = urlType in URL_TYPE_PARAMS;
            const showSort = urlType === "video_codes";

            if (!showConditions) return null;

            return (
              <>
                <Form.Item name="has_magnet" label="含磁力链接" valuePropName="checked">
                  <Switch />
                </Form.Item>

                <Form.Item name="has_chinese_sub" label="含中文字幕" valuePropName="checked">
                  <Switch />
                </Form.Item>

                {showSort && (
                  <Form.Item name="sort_type" label="排序方式">
                    <Select options={SORT_OPTIONS} />
                  </Form.Item>
                )}
              </>
            );
          }}
        </Form.Item>

        <Form.Item name="max_list_pages" label="最大翻页数">
          <InputNumber min={1} max={100} />
        </Form.Item>

        <Form.Item name="is_skip" label="禁用此任务" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => {
            const baseUrl: string = getFieldValue("url") ?? "";
            const urlType = getFieldValue("url_type") as UrlType;
            const hasMagnet = (getFieldValue("has_magnet") as boolean) ?? false;
            const hasSub = (getFieldValue("has_chinese_sub") as boolean) ?? false;
            const sortType = (getFieldValue("sort_type") as number) ?? 0;
            const finalUrl = buildFinalUrl(baseUrl, urlType, hasMagnet, hasSub, sortType);

            return (
              <Form.Item label="最终 URL 预览">
                <Input value={finalUrl} disabled />
              </Form.Item>
            );
          }}
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting}>
            {isEdit ? "更新" : "创建"}
          </Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate({ to: "/tasks" })}>
            取消
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
