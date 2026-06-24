import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Input,
  List,
  message,
  Modal,
  Popconfirm,
  Space,
  Table,
  Typography,
} from "antd";
import {
  DeleteOutlined,
  FileAddOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import {
  fetchCookieFiles,
  fetchCookieContent,
  saveCookieFile,
  deleteCookieFile,
  type CookieFileInfo,
} from "./api";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import styles from "@/shared/styles/pages.module.css";

interface CookieEntry {
  key: string;
  name: string;
  value: string;
}

export default function Cookies() {
  const [files, setFiles] = useState<CookieFileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [entries, setEntries] = useState<CookieEntry[]>([]);
  const [saving, setSaving] = useState(false);
  const [newFileModalOpen, setNewFileModalOpen] = useState(false);
  const [newFilename, setNewFilename] = useState("");

  const loadFiles = useCallback(async () => {
    try {
      const data = await fetchCookieFiles();
      setFiles(data);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, []);

  const loadContent = useCallback(async (filename: string) => {
    try {
      const data = await fetchCookieContent(filename);
      const cookieEntries: CookieEntry[] = Object.entries(data.cookies).map(
        ([name, value], index) => ({
          key: `${index}`,
          name,
          value,
        }),
      );
      setEntries(cookieEntries);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, []);

  useEffect(() => {
    loadFiles().finally(() => setLoading(false));
  }, [loadFiles]);

  useEffect(() => {
    if (selectedFile) {
      loadContent(selectedFile);
    } else {
      setEntries([]);
    }
  }, [selectedFile, loadContent]);

  const handleAddEntry = () => {
    const newEntry: CookieEntry = {
      key: `${Date.now()}`,
      name: "",
      value: "",
    };
    setEntries((prev) => [...prev, newEntry]);
  };

  const handleEntryChange = useCallback(
    (key: string, field: "name" | "value", changedValue: string) => {
      setEntries((prev) =>
        prev.map((entry) =>
          entry.key === key ? { ...entry, [field]: changedValue } : entry,
        ),
      );
    },
    [],
  );

  const handleDeleteEntry = useCallback((key: string) => {
    setEntries((prev) => prev.filter((entry) => entry.key !== key));
  }, []);

  const handleSave = async () => {
    if (!selectedFile) return;
    const cookieDict: Record<string, string> = {};
    for (const entry of entries) {
      if (entry.name.trim()) {
        cookieDict[entry.name.trim()] = entry.value;
      }
    }
    setSaving(true);
    try {
      await saveCookieFile(selectedFile, { cookies: cookieDict });
      message.success(`Cookie 文件 "${selectedFile}" 已保存`);
      await loadFiles();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFile = async (filename: string) => {
    try {
      await deleteCookieFile(filename);
      message.success(`Cookie 文件 "${filename}" 已删除`);
      if (selectedFile === filename) {
        setSelectedFile(null);
        setEntries([]);
      }
      await loadFiles();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const handleCreateFile = async () => {
    const trimmed = newFilename.trim();
    if (!trimmed) {
      message.warning("请输入文件名");
      return;
    }
    const filename = trimmed.endsWith(".json") ? trimmed : `${trimmed}.json`;
    try {
      await saveCookieFile(filename, { cookies: {} });
      message.success(`Cookie 文件 "${filename}" 已创建`);
      setNewFileModalOpen(false);
      setNewFilename("");
      await loadFiles();
      setSelectedFile(filename);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const columns = useMemo(
    () => [
      {
        title: "名称",
        dataIndex: "name",
        key: "name",
        width: 200,
        render: (_: unknown, record: CookieEntry) => (
          <Input
            value={record.name}
            placeholder="cookie 名称"
            onChange={(e) =>
              handleEntryChange(record.key, "name", e.target.value)
            }
          />
        ),
      },
      {
        title: "值",
        dataIndex: "value",
        key: "value",
        render: (_: unknown, record: CookieEntry) => (
          <Input
            value={record.value}
            placeholder="cookie 值"
            onChange={(e) =>
              handleEntryChange(record.key, "value", e.target.value)
            }
          />
        ),
      },
      {
        title: "",
        key: "action",
        width: 50,
        render: (_: unknown, record: CookieEntry) => (
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteEntry(record.key)}
          />
        ),
      },
    ],
    [],
  );

  if (loading) return <FullPageSpinner />;

  return (
    <div style={{ display: "flex", gap: 24, height: "100%" }}>
      {/* File list sidebar */}
      <Card
        title="Cookie 文件"
        size="small"
        style={{ width: 260, flexShrink: 0 }}
        extra={
          <Button
            type="primary"
            size="small"
            icon={<FileAddOutlined />}
            onClick={() => setNewFileModalOpen(true)}
          >
            新建
          </Button>
        }
      >
        <List
          dataSource={files}
          locale={{ emptyText: "暂无 Cookie 文件" }}
          renderItem={(file) => (
            <List.Item
              onClick={() => setSelectedFile(file.filename)}
              style={{
                cursor: "pointer",
                background:
                  selectedFile === file.filename ? "#e6f4ff" : undefined,
                padding: "8px 12px",
                borderRadius: 6,
              }}
              actions={[
                <Popconfirm
                  key="delete"
                  title={`确定删除 "${file.filename}"？`}
                  onConfirm={() => handleDeleteFile(file.filename)}
                >
                  <Button type="text" size="small" danger>
                    删除
                  </Button>
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Typography.Text
                    strong={selectedFile === file.filename}
                    style={{ fontSize: 13 }}
                  >
                    {file.filename}
                  </Typography.Text>
                }
                description={`${file.size_bytes} bytes`}
              />
            </List.Item>
          )}
        />
      </Card>

      {/* Editor */}
      <Card
        title={
          selectedFile
            ? `编辑: ${selectedFile}`
            : "选择一个 Cookie 文件进行编辑"
        }
        style={{ flex: 1 }}
        className={styles.formCard}
        extra={
          selectedFile ? (
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAddEntry}
              >
                添加
              </Button>
              <Button type="primary" onClick={handleSave} loading={saving}>
                保存
              </Button>
            </Space>
          ) : null
        }
      >
        {selectedFile ? (
          <Table
            dataSource={entries}
            columns={columns}
            pagination={false}
            size="small"
            locale={{ emptyText: "暂无 cookie，点击「添加」按钮新增" }}
            scroll={{ y: "calc(100vh - 340px)" }}
          />
        ) : (
          <Typography.Text type="secondary">
            请在左侧选择一个文件，或点击「新建」创建新的 Cookie 文件。
          </Typography.Text>
        )}
      </Card>

      {/* New file modal */}
      <Modal
        title="新建 Cookie 文件"
        open={newFileModalOpen}
        onOk={handleCreateFile}
        onCancel={() => {
          setNewFileModalOpen(false);
          setNewFilename("");
        }}
        okText="创建"
        cancelText="取消"
      >
        <Input
          placeholder="输入文件名（例如 javdb_cookies.json）"
          value={newFilename}
          onChange={(e) => setNewFilename(e.target.value)}
          onPressEnter={handleCreateFile}
        />
      </Modal>
    </div>
  );
}
