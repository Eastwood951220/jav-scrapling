import { useState } from "react";
import { Outlet, useNavigate, useLocation, createFileRoute } from "@tanstack/react-router";
import { Layout as AntLayout, Menu, Typography } from "antd";
import {
  UnorderedListOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import styles from "../shared/styles/layout.module.css";

const { Sider, Content, Header } = AntLayout;

const menuItems = [
  { key: "/tasks", icon: <UnorderedListOutlined />, label: "任务配置" },
  { key: "/schedules", icon: <ClockCircleOutlined />, label: "定时任务" },
  { key: "/settings", icon: <SettingOutlined />, label: "系统设置" },
  { key: "/runs", icon: <HistoryOutlined />, label: "运行历史" },
  { key: "/movies", icon: <PlayCircleOutlined />, label: "内容浏览" },
];

export const Route = createFileRoute("/_app")({
  component: AppLayoutComponent,
});

function AppLayoutComponent() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey =
    menuItems.find((item) => location.pathname.startsWith(item.key))?.key ||
    "/tasks";

  const currentLabel =
    menuItems.find((item) => location.pathname.startsWith(item.key))?.label ||
    "配置管理";

  return (
    <AntLayout className={styles.root} hasSider>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        style={{
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div className={styles.logo}>
          <Typography.Text
            strong
            className={collapsed ? styles.logoTextCollapsed : styles.logoText}
          >
            {collapsed ? "JS" : "Jav Scrapling"}
          </Typography.Text>
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate({ to: key })}
          className={styles.menu}
        />
      </Sider>

      <AntLayout className={styles.rightPanel}>
        <Header className={styles.header}>
          <Typography.Title level={4} className={styles.headerTitle}>
            {currentLabel}
          </Typography.Title>
        </Header>

        <Content className={styles.content}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
