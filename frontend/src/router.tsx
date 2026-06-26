import {useState} from "react";
import {
    Outlet,
    Navigate,
    useNavigate,
    useLocation,
    createRootRoute,
    createRoute,
    createRouter,
} from "@tanstack/react-router";
import {ConfigProvider, Layout as AntLayout, Menu, Typography} from "antd";
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
import {lightTheme} from "@/theme";
import styles from "@/shared/styles/layout.module.css";

import LoginPage from "@/features/_auth/login-placeholder";
import Movies from "@/features/content/movies/Movies";

import CrawlerTaskList from "@/features/crawler/tasks/TaskList";
import CrawlerTaskForm from "@/features/crawler/tasks/TaskForm";
import CrawlerSchedules from "@/features/crawler/schedules/Schedules";
import CrawlerConfig from "@/features/crawler/config/Config";
import CrawlerRunList from "@/features/crawler/runs/RunList";
import CrawlerRunDetail from "@/features/crawler/runs/RunDetail";

import StorageConfig from "@/features/storage/config/Config";
import StorageTaskList from "@/features/storage/tasks/TaskList";
import StorageTaskDetail from "@/features/storage/tasks/TaskDetail";

// ── Root ──────────────────────────────────────────────
const rootRoute = createRootRoute({
    component: () => (
        <ConfigProvider locale={zhCN} theme={lightTheme}>
            <ErrorBoundary>
                <Outlet/>
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
            <Outlet/>
        </AuthLayout>
    ),
});

const loginRoute = createRoute({
    path: "/login",
    getParentRoute: () => authLayout,
    component: LoginPage,
});

// ── App layout ────────────────────────────────────────

const {Sider, Content, Header} = AntLayout;

const menuItems = [
     {
        type: "group" as const,
        label: "内容管理",
        children: [
            {key: "/movies", icon: <PlayCircleOutlined/>, label: "内容浏览"},
        ],
    },
    {
        type: "group" as const,
        label: "爬虫模块",
        children: [
            {key: "/crawler/tasks", icon: <UnorderedListOutlined/>, label: "任务配置"},
            {key: "/crawler/schedules", icon: <ClockCircleOutlined/>, label: "定时任务"},
            {key: "/crawler/runs", icon: <HistoryOutlined/>, label: "运行历史"},
            {key: "/crawler/config", icon: <SettingOutlined/>, label: "爬虫配置"},
        ],
    },
    {
        type: "group" as const,
        label: "存储模块",
        children: [
            {key: "/storage/tasks", icon: <DatabaseOutlined/>, label: "存储任务"},
            {key: "/storage/config", icon: <CloudOutlined/>, label: "存储配置"},
        ],
    }
];

function AppLayoutComponent() {
    const [collapsed, setCollapsed] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();

    const flatItems = menuItems.flatMap((g) => g.children || []);

    const selectedKey =
        flatItems.find((item) => location.pathname.startsWith(item.key))?.key ||
        "/movies";

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
                style={{overflow: "hidden", display: "flex", flexDirection: "column"}}
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
                    onClick={({key}) => navigate({to: key})}
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
                    <Outlet/>
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
    component: () => <Navigate to="/movies"/>,
});

const crawlerTasksIndexRoute = createRoute({
    path: "/crawler/tasks",
    getParentRoute: () => appLayout,
    component: CrawlerTaskList,
});

const crawlerTasksNewRoute = createRoute({
    path: "/crawler/tasks/new",
    getParentRoute: () => appLayout,
    component: CrawlerTaskForm,
});

const crawlerTasksEditRoute = createRoute({
    path: "/crawler/tasks/$id/edit",
    getParentRoute: () => appLayout,
    component: CrawlerTaskForm,
});

const crawlerSchedulesRoute = createRoute({
    path: "/crawler/schedules",
    getParentRoute: () => appLayout,
    component: CrawlerSchedules,
});

const crawlerConfigRoute = createRoute({
    path: "/crawler/config",
    getParentRoute: () => appLayout,
    component: CrawlerConfig,
});

const crawlerRunsIndexRoute = createRoute({
    path: "/crawler/runs",
    getParentRoute: () => appLayout,
    component: CrawlerRunList,
});

const crawlerRunsDetailRoute = createRoute({
    path: "/crawler/runs/$id",
    getParentRoute: () => appLayout,
    component: CrawlerRunDetail,
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
    component: StorageTaskList,
});

const storageTaskDetailRoute = createRoute({
    path: "/storage/tasks/$id",
    getParentRoute: () => appLayout,
    component: StorageTaskDetail,
});

// ── Build tree ────────────────────────────────────────
const routeTree = rootRoute.addChildren([
    authLayout.addChildren([loginRoute]),
    appLayout.addChildren([
        appIndexRoute,
        moviesRoute,
        crawlerTasksIndexRoute,
        crawlerTasksNewRoute,
        crawlerTasksEditRoute,
        crawlerSchedulesRoute,
        crawlerConfigRoute,
        crawlerRunsIndexRoute,
        crawlerRunsDetailRoute,
        storageConfigRoute,
        storageTasksRoute,
        storageTaskDetailRoute,
    ]),
]);

export const router = createRouter({routeTree});

declare module "@tanstack/react-router" {
    interface Register {
        router: typeof router;
    }
}
