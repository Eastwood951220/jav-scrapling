import { useEffect, useMemo, useRef, useState } from "react";
import { Input, Select, Space, Switch, Tag, Timeline, Typography } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { logLevelColors, stepLabels } from "../constants";
import type { TaskLogEntry } from "../types";

const LOG_LEVEL_OPTIONS = [
  { value: "INFO", label: "INFO" },
  { value: "WARNING", label: "WARNING" },
  { value: "ERROR", label: "ERROR" },
];

interface LogsPanelProps {
  logs: TaskLogEntry[];
  isActive: boolean;
}

export default function LogsPanel({ logs, isActive }: LogsPanelProps) {
  const [level, setLevel] = useState<string | undefined>(undefined);
  const [step, setStep] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  const stepOptions = useMemo(
    () => Array.from(new Set(logs.map((entry) => entry.step).filter(Boolean))).map((value) => ({
      value: value as string,
      label: stepLabels[value as string] || value,
    })),
    [logs],
  );

  const filteredLogs = logs.filter((entry) => {
    if (level && entry.level !== level) return false;
    if (step && entry.step !== step) return false;
    if (search && !entry.message.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select style={{ width: 140 }} placeholder="日志级别" allowClear value={level} onChange={setLevel} options={LOG_LEVEL_OPTIONS} />
        <Select style={{ width: 160 }} placeholder="筛选步骤" allowClear value={step} onChange={setStep} options={stepOptions} />
        <Input
          placeholder="搜索日志"
          prefix={<SearchOutlined />}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          style={{ width: 220 }}
          allowClear
        />
        <Space>
          <Typography.Text type="secondary">自动滚动</Typography.Text>
          <Switch size="small" checked={autoScroll} onChange={setAutoScroll} />
        </Space>
        <Typography.Text type="secondary">共 {filteredLogs.length} 条</Typography.Text>
      </Space>

      {filteredLogs.length === 0 ? (
        <Typography.Text type="secondary">{isActive ? "等待日志..." : "无日志"}</Typography.Text>
      ) : (
        <div style={{ maxHeight: 500, overflow: "auto" }}>
          <Timeline
            items={filteredLogs.map((entry, idx) => ({
              key: idx,
              color: logLevelColors[entry.level] || "gray",
              children: (
                <div>
                  <Space size="small">
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(entry.timestamp).toLocaleString()}
                    </Typography.Text>
                    <Tag color={logLevelColors[entry.level] || "default"} style={{ fontSize: 11 }}>
                      {entry.level}
                    </Tag>
                    {entry.step && (
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        [{stepLabels[entry.step] || entry.step}]
                      </Typography.Text>
                    )}
                  </Space>
                  <Typography.Text
                    type={entry.level === "ERROR" ? "danger" : undefined}
                    style={{ display: "block", marginTop: 2 }}
                  >
                    {entry.message}
                  </Typography.Text>
                  {entry.data && Object.keys(entry.data).length > 0 && (
                    <pre
                      style={{
                        fontSize: 11,
                        background: "#f5f5f5",
                        padding: "4px 8px",
                        borderRadius: 4,
                        marginTop: 4,
                        maxHeight: 120,
                        overflow: "auto",
                      }}
                    >
                      {JSON.stringify(entry.data, null, 2)}
                    </pre>
                  )}
                </div>
              ),
            }))}
          />
          <div ref={logEndRef} />
        </div>
      )}
    </>
  );
}
