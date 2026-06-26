import { useState } from "react";
import {
  Outlet,
  Navigate,
  useNavigate,
  useLocation,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { ConfigProvider, Layout as AntLayout, Menu, Typography } from "antd";
import zhCN from "antd/locale/zh_CN";
import {
  UnorderedListOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
  DatabaseOutlined,
  CloudOutlined,
} from "@ant-design/icons";
import ErrorBoundary from "@/shared/components/ErrorBoundary";
import AuthLayout from "@/shared/components/AuthLayout";
import { lightTheme } from "@/theme";
import styles from "@/shared/styles/layout.module.css";

import LoginPage from "@/features/_auth/login-placeholder";
import TaskList from "@/features/tasks/TaskList";
import TaskForm from "@/features/tasks/TaskForm";
import Schedules from "@/features/schedules/Schedules";
import Settings from "@/features/settings/Settings";
import RunList from "@/features/runs/RunList";
import RunDetail from "@/features/runs/RunDetail";
import Movies from "@/features/movies/Movies";
import StorageConfig from "@/features/storage-config/StorageConfig";

// ── Root ──────────────────────────────────────────────
const rootRoute = createRootRoute({
  component: () => (
    <ConfigProvider locale={zhCN} theme={lightTheme}>
      <ErrorBoundary>
        <Outlet />
      </ErrorBoundary>
    </ConfigProvider>
  ),
});

// ── Auth layout ───────────────────────────────────────
const authLayout = createRoute({
  id: "_auth",
  getParentRoute: () => rootRoute,
  component: () => (
    <AuthLayout>
      <Outlet />
    </AuthLayout>
  ),
});

const loginRoute = createRoute({
  path: "/login",
  getParentRoute: () => authLayout,
  component: LoginPage,
});

// ── App layout ────────────────────────────────────────

const { Sider, Content, Header } = AntLayout;

const menuItems = [
  {
    type: "group" as const,
    label: "爬虫模块",
    children: [
      { key: "/tasks", icon: <UnorderedListOutlined />, label: "任务配置" },
      { key: "/schedules", icon: <ClockCircleOutlined />, label: "定时任务" },
      { key: "/runs", icon: <HistoryOutlined />, label: "运行历史" },
      { key: "/settings", icon: <SettingOutlined />, label: "爬虫设置" },
    ],
  },
  {
    type: "group" as const,
    label: "存储模块",
    children: [
      { key: "/storage/tasks", icon: <DatabaseOutlined />, label: "存储任务" },
      { key: "/storage/config", icon: <CloudOutlined />, label: "存储配置" },
    ],
  },
  {
    type: "group" as const,
    label: "内容管理",
    children: [
      { key: "/movies", icon: <PlayCircleOutlined />, label: "内容浏览" },
    ],
  },
];

function AppLayoutComponent() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const flatItems = menuItems.flatMap((g) => g.children || []);

  const selectedKey =
    flatItems.find((item) => location.pathname.startsWith(item.key))?.key ||
    "/tasks";

  const currentLabel =
    flatItems.find((item) => location.pathname.startsWith(item.key))?.label ||
    "爬虫模块";

  return (
    <AntLayout className={styles.root} hasSider>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}
      >
        <div className={styles.logo}>
          <Typography.Text strong className={collapsed ? styles.logoTextCollapsed : styles.logoText}>
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

const appLayout = createRoute({
  id: "_app",
  getParentRoute: () => rootRoute,
  component: AppLayoutComponent,
});

// ── App child routes ──────────────────────────────────
const appIndexRoute = createRoute({
  path: "/",
  getParentRoute: () => appLayout,
  component: () => <Navigate to="/tasks" />,
});

const tasksIndexRoute = createRoute({
  path: "/tasks",
  getParentRoute: () => appLayout,
  component: TaskList,
});

const tasksNewRoute = createRoute({
  path: "/tasks/new",
  getParentRoute: () => appLayout,
  component: TaskForm,
});

const tasksEditRoute = createRoute({
  path: "/tasks/$id/edit",
  getParentRoute: () => appLayout,
  component: TaskForm,
});

const schedulesRoute = createRoute({
  path: "/schedules",
  getParentRoute: () => appLayout,
  component: Schedules,
});

const settingsRoute = createRoute({
  path: "/settings",
  getParentRoute: () => appLayout,
  component: Settings,
});

const runsIndexRoute = createRoute({
  path: "/runs",
  getParentRoute: () => appLayout,
  component: RunList,
});

const runsDetailRoute = createRoute({
  path: "/runs/$id",
  getParentRoute: () => appLayout,
  component: RunDetail,
});

const moviesRoute = createRoute({
  path: "/movies",
  getParentRoute: () => appLayout,
  component: Movies,
});

const storageConfigRoute = createRoute({
  path: "/storage/config",
  getParentRoute: () => appLayout,
  component: StorageConfig,
});

const storageTasksRoute = createRoute({
  path: "/storage/tasks",
  getParentRoute: () => appLayout,
  component: () => (
    <div style={{ padding: 24, textAlign: "center" }}>
      <Typography.Title level={4}>存储任务</Typography.Title>
      <Typography.Text type="secondary">即将在 Phase 3 实现</Typography.Text>
    </div>
  ),
});

// ── Build tree ────────────────────────────────────────
const routeTree = rootRoute.addChildren([
  authLayout.addChildren([loginRoute]),
  appLayout.addChildren([
    appIndexRoute,
    tasksIndexRoute,
    tasksNewRoute,
    tasksEditRoute,
    schedulesRoute,
    settingsRoute,
    runsIndexRoute,
    runsDetailRoute,
    moviesRoute,
    storageConfigRoute,
    storageTasksRoute,
  ]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
