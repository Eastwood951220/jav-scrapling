import React, {useEffect, useState, useCallback} from "react";
import {
    Table,
    Input,
    Select,
    Button,
    Space,
    Card,
    message,
    Drawer,
    Descriptions,
    Tag,
    Typography,
    InputNumber,
    Image,
    Popconfirm,
    DatePicker,
    Modal,
    Switch,
    Statistic,
    Row,
    Col,
} from "antd";
import {SearchOutlined, ReloadOutlined, DownloadOutlined, DeleteOutlined, CloudUploadOutlined, SyncOutlined} from "@ant-design/icons";
import type {ColumnsType} from "antd/es/table";
import type {Dayjs} from "dayjs";
import {
    fetchTaskNames,
    fetchMovies,
    fetchMovie,
    deleteMovie,
    deleteMovies,
    fetchFilters,
    fetchAllMagnets,
    createStorageTask,
    batchCreateStorageTasks,
    selectMagnet,
    syncMovieLocation,
    syncMovieLocationsBatch,
} from "./api";
import type {StorageBatchResponse, SyncBatchResult} from "./api";
import type {Movie, MovieListResponse} from "./types";
import type {MovieMagnet} from "@/shared/types/common";
import {getErrorMessage} from "@/shared/hooks/useErrorMessage";

export default function Movies() {
    const [taskOptions, setTaskOptions] = useState<{ value: string; label: string }[]>([]);
    const [selectedTask, setSelectedTask] = useState<string | undefined>(undefined);
    const [search, setSearch] = useState("");
    const [ratingMin, setRatingMin] = useState<number | undefined>(undefined);
    const [sortBy, setSortBy] = useState("code");
    const [sortOrder, setSortOrder] = useState(-1);
    const [data, setData] = useState<MovieListResponse>({items: [], total: 0, page: 1, limit: 20, total_pages: 1});
    const [pageSize, setPageSize] = useState(20);
    const [loading, setLoading] = useState(false);
    const [detailOpen, setDetailOpen] = useState(false);
    const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
    const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
    const [actorOptions, setActorOptions] = useState<{ value: string; label: string }[]>([]);
    const [tagOptions, setTagOptions] = useState<{ value: string; label: string }[]>([]);
    const [selectedActors, setSelectedActors] = useState<string[]>([]);
    const [selectedTags, setSelectedTags] = useState<string[]>([]);
    const [directorOptions, setDirectorOptions] = useState<{ value: string; label: string }[]>([]);
    const [makerOptions, setMakerOptions] = useState<{ value: string; label: string }[]>([]);
    const [seriesOptions, setSeriesOptions] = useState<{ value: string; label: string }[]>([]);
    const [selectedDirectors, setSelectedDirectors] = useState<string[]>([]);
    const [selectedMakers, setSelectedMakers] = useState<string[]>([]);
    const [selectedSeries, setSelectedSeries] = useState<string[]>([]);
    const [filtersLoading, setFiltersLoading] = useState(false);
    const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);
    const [storageStatus, setStorageStatus] = useState<string | undefined>(undefined);

    // Storage push state
    const [pushModalOpen, setPushModalOpen] = useState(false);
    const [pushMovie, setPushMovie] = useState<Movie | null>(null);
    const [pushMagnet, setPushMagnet] = useState<string | undefined>(undefined);
    const [pushLoading, setPushLoading] = useState(false);
    const [batchPushOpen, setBatchPushOpen] = useState(false);
    const [batchSkipRunning, setBatchSkipRunning] = useState(true);
    const [batchSkipCompleted, setBatchSkipCompleted] = useState(true);
    const [batchRetryFailed, setBatchRetryFailed] = useState(false);
    const [batchPushLoading, setBatchPushLoading] = useState(false);
    const [batchResult, setBatchResult] = useState<StorageBatchResponse | null>(null);
    const [selectMagnetOpen, setSelectMagnetOpen] = useState(false);
    const [selectMagnetMovie, setSelectMagnetMovie] = useState<Movie | null>(null);
    const [selectMagnetLoading, setSelectMagnetLoading] = useState(false);
    const [syncLoading, setSyncLoading] = useState(false);
    const [batchSyncLoading, setBatchSyncLoading] = useState(false);
    const [batchSyncResult, setBatchSyncResult] = useState<SyncBatchResult | null>(null);

    const loadFilters = useCallback(async () => {
        setFiltersLoading(true);
        try {
            const [actors, tags, directors, makers, series] = await Promise.all([
                fetchFilters("actor"),
                fetchFilters("tag"),
                fetchFilters("director"),
                fetchFilters("maker"),
                fetchFilters("series"),
            ]);
            setActorOptions(actors.map((a) => ({value: a, label: a})));
            setTagOptions(tags.map((t) => ({value: t, label: t})));
            setDirectorOptions(directors.map((d) => ({value: d, label: d})));
            setMakerOptions(makers.map((m) => ({value: m, label: m})));
            setSeriesOptions(series.map((s) => ({value: s, label: s})));
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        } finally {
            setFiltersLoading(false);
        }
    }, []);

    const loadTasks = useCallback(async () => {
        try {
            const tasks = await fetchTaskNames();
            const options = tasks.map((t) => ({value: t.name, label: t.name}));
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
                actors: selectedActors.length > 0 ? selectedActors.join(",") : undefined,
                tags: selectedTags.length > 0 ? selectedTags.join(",") : undefined,
                director: selectedDirectors.length > 0 ? selectedDirectors.join(",") : undefined,
                maker: selectedMakers.length > 0 ? selectedMakers.join(",") : undefined,
                series: selectedSeries.length > 0 ? selectedSeries.join(",") : undefined,
                date_from: dateRange[0]?.format("YYYY-MM-DD"),
                date_to: dateRange[1]?.format("YYYY-MM-DD"),
                storage_status: storageStatus,
            });
            setData(result);
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        } finally {
            setLoading(false);
        }
    }, [selectedTask, search, sortBy, sortOrder, ratingMin, pageSize, selectedActors, selectedTags, selectedDirectors, selectedMakers, selectedSeries, dateRange, storageStatus]);

    useEffect(() => {
        loadTasks();
        loadFilters();
    }, [loadTasks, loadFilters]);

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

    const getMovieMagnetLinks = (movie: Movie): string[] => {
        const magnetLinks = Array.isArray(movie.magnets)
            ? movie.magnets.map((m) => m.magnet).filter((m): m is string => Boolean(m?.trim()))
            : [];
        if (magnetLinks.length > 0) return magnetLinks;
        return movie.magnet ? [movie.magnet] : [];
    };

    const handleExportMagnets = async () => {
        let magnetStrings: string[] = [];

        if (selectedRowKeys.length > 0) {
            // 有勾选则导出勾选项
            magnetStrings = data.items
                .filter((item) => selectedRowKeys.includes(item._id))
                .flatMap(getMovieMagnetLinks);
        } else {
            // 无勾选则调用后端接口导出当前筛选条件下的全部磁力
            try {
                const result = await fetchAllMagnets({
                    source_task_name: selectedTask,
                    search: search || undefined,
                    rating_min: ratingMin,
                    actors: selectedActors.length > 0 ? selectedActors.join(",") : undefined,
                    tags: selectedTags.length > 0 ? selectedTags.join(",") : undefined,
                    director: selectedDirectors.length > 0 ? selectedDirectors.join(",") : undefined,
                    maker: selectedMakers.length > 0 ? selectedMakers.join(",") : undefined,
                    series: selectedSeries.length > 0 ? selectedSeries.join(",") : undefined,
                    date_from: dateRange[0]?.format("YYYY-MM-DD"),
                    date_to: dateRange[1]?.format("YYYY-MM-DD"),
                });
                magnetStrings = result.magnets.map((m) => m.magnet).filter(Boolean);
            } catch (e: unknown) {
                message.error(getErrorMessage(e));
                return;
            }
        }

        if (magnetStrings.length === 0) {
            message.warning("无可导出的磁力链接");
            return;
        }

        const blob = new Blob([magnetStrings.join("\n")], {type: "text/plain;charset=utf-8"});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `magnets_${selectedTask ?? "all"}_${new Date().toISOString().slice(0, 10)}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        message.success(`已导出 ${magnetStrings.length} 条磁力链接`);
    };

    const handleDelete = useCallback(async (id: string) => {
        try {
            await deleteMovie(id);
            message.success("已删除");
            loadMovies(data.page);
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        }
    }, [loadMovies, data.page]);

    const handleBatchDelete = useCallback(async () => {
        if (selectedRowKeys.length === 0) return;
        try {
            const result = await deleteMovies(selectedRowKeys as string[]);
            message.success(`已删除 ${result.deleted} 条`);
            setSelectedRowKeys([]);
            loadMovies(data.page);
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        }
    }, [selectedRowKeys, loadMovies, data.page]);

    // --- Storage push handlers ---

    const getMagnetOptions = (movie: Movie): { value: string; label: string }[] => {
        const magnets: MovieMagnet[] = (movie.magnets ?? []).filter((m) => Boolean(m.magnet?.trim()));
        if (magnets.length > 0) {
            return magnets.map((m) => {
                const labelName = m.name || m.title || m.magnet.slice(0, 40);
                const labelSize = m.size_text || m.size;
                const labelFiles = m.file_text ? `, ${m.file_text}` : "";
                const labelTags = m.tags?.length ? ` [${m.tags.join(", ")}]` : "";
                return {
                    value: m.magnet,
                    label: `${labelName}${labelSize ? ` (${labelSize}${labelFiles})` : ""}${labelTags}`,
                };
            });
        }
        if (movie.magnet) {
            return [{value: movie.magnet, label: movie.magnet}];
        }
        return [];
    };

    const getDetailMagnets = (value: unknown): MovieMagnet[] => {
        if (!Array.isArray(value)) return [];
        return value.filter((item): item is MovieMagnet => typeof item === "object" && item !== null);
    };

    const getMagnetSizeText = (magnet: MovieMagnet): string => {
        if (magnet.size_text) return magnet.size_text;
        if (typeof magnet.size === "string" && magnet.size.trim()) return magnet.size;
        const sizeMb = typeof magnet.size_mb === "number" ? magnet.size_mb : magnet.size;
        return typeof sizeMb === "number" ? `${(sizeMb / 1024).toFixed(1)} GB` : "";
    };

    const getDetailSizeText = (size: unknown, magnets: MovieMagnet[]): string => {
        if (typeof size === "number") return `${(size / 1024).toFixed(1)} GB`;
        if (typeof size === "string" && size.trim()) return size;
        const firstMagnetSize = magnets.length > 0 ? getMagnetSizeText(magnets[0]) : "";
        return firstMagnetSize || "-";
    };

    const getMagnetDisplayText = (magnet: MovieMagnet): string => {
        const metadata = [magnet.name || magnet.title, getMagnetSizeText(magnet), magnet.file_text].filter(Boolean).join(" · ");
        return metadata ? `${metadata}\n${magnet.magnet}` : magnet.magnet;
    };

    const handleOpenPush = (movie: Movie) => {
        const options = getMagnetOptions(movie);
        setPushMovie(movie);
        setPushMagnet(options.length > 0 ? options[0].value : undefined);
        setPushModalOpen(true);
    };

    const handleConfirmPush = async () => {
        if (!pushMovie || !pushMagnet) return;
        setPushLoading(true);
        try {
            // Find selected magnet metadata
            const selectedMagnet = (pushMovie.magnets ?? []).find((m) => m.magnet === pushMagnet);
            const magnetMeta = {
                has_chinese_sub: selectedMagnet?.has_chinese_sub ?? false,
                tags: selectedMagnet?.tags ?? [],
            };
            const res = await createStorageTask(pushMovie._id, pushMagnet, magnetMeta);
            if (res.status === "existing") {
                message.info("已有进行中的任务");
            } else {
                message.success("已创建推送任务");
            }
            setPushModalOpen(false);
            loadMovies(data.page);
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        } finally {
            setPushLoading(false);
        }
    };

    const handleOpenBatchPush = () => {
        setBatchResult(null);
        setBatchSkipRunning(true);
        setBatchSkipCompleted(true);
        setBatchRetryFailed(false);
        setBatchPushOpen(true);
    };

    const handleConfirmBatchPush = async () => {
        setBatchPushLoading(true);
        try {
            const result = await batchCreateStorageTasks(selectedRowKeys as string[], {
                skip_running: batchSkipRunning,
                skip_completed: batchSkipCompleted,
                retry_failed: batchRetryFailed,
            });
            setBatchResult(result);
            message.success(`创建 ${result.created} 个任务，跳过 ${result.skipped} 个`);
            loadMovies(data.page);
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        } finally {
            setBatchPushLoading(false);
        }
    };

    const handleOpenSelectMagnet = (movie: Movie) => {
        setSelectMagnetMovie(movie);
        setSelectMagnetOpen(true);
    };

    const handleSelectMagnet = async (dedupeKey: string) => {
        if (!selectMagnetMovie) return;
        setSelectMagnetLoading(true);
        try {
            await selectMagnet(selectMagnetMovie._id, dedupeKey);
            message.success("已选择最佳磁力");
            setSelectMagnetOpen(false);
            setData((prev) => ({
                ...prev,
                items: prev.items.map((item) =>
                    item._id === selectMagnetMovie._id
                        ? { ...item, selected_magnet_dedupe_key: dedupeKey }
                        : item
                ),
            }));
            if (detail && (detail._id as string) === selectMagnetMovie._id) {
                setDetail({ ...detail, selected_magnet_dedupe_key: dedupeKey });
            }
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        } finally {
            setSelectMagnetLoading(false);
        }
    };

    // --- Storage location sync handlers ---

    const handleSyncLocation = async (movie: Movie) => {
        setSyncLoading(true);
        try {
            const result = await syncMovieLocation(movie._id);
            message.success("同步完成");
            setData((prev) => ({
                ...prev,
                items: prev.items.map((item) =>
                    item._id === movie._id
                        ? { ...item, storage_summary: { ...item.storage_summary, locations: result.locations, synced_at: new Date().toISOString() } }
                        : item
                ),
            }));
            if (detail && (detail._id as string) === movie._id) {
                const storageSummary = (detail.storage_summary as Record<string, unknown>) || {};
                setDetail({ ...detail, storage_summary: { ...storageSummary, locations: result.locations, synced_at: new Date().toISOString() } });
            }
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        } finally {
            setSyncLoading(false);
        }
    };

    const handleBatchSync = async () => {
        if (selectedRowKeys.length === 0) return;
        setBatchSyncLoading(true);
        setBatchSyncResult(null);
        try {
            const result = await syncMovieLocationsBatch(selectedRowKeys as string[]);
            setBatchSyncResult(result);
            message.success(`同步完成: ${result.total} 部`);
            loadMovies(data.page);
        } catch (e: unknown) {
            message.error(getErrorMessage(e));
        } finally {
            setBatchSyncLoading(false);
        }
    };

    const storageStatusColor: Record<string, string> = {
        pending: "processing",
        running: "processing",
        waiting_download: "processing",
        waiting_retry: "warning",
        downloading: "processing",
        moving: "processing",
        completed: "success",
        failed: "error",
        retryable: "warning",
        missing: "error",
    };

    const storageStatusText: Record<string, string> = {
        pending: "等待中",
        running: "运行中",
        waiting_download: "等待下载",
        waiting_retry: "等待重试",
        downloading: "下载中",
        moving: "移动中",
        completed: "已完成",
        failed: "失败",
        retryable: "可重试",
        missing: "文件缺失",
    };

    const columns: ColumnsType<Movie> = [
        {title: "番号", dataIndex: "code", key: "code", width: 120},
        {
            title: "标题",
            dataIndex: "source_name",
            key: "source_name",
            ellipsis: true,
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
            width: 160,
            sorter: true,
            defaultSortOrder: "descend",
        },
        {
            title: "时长",
            dataIndex: "duration",
            key: "duration",
            width: 100,
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
            width: 240,
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
            title: "存储状态",
            key: "storage_status",
            width: 100,
            render: (_: unknown, record: Movie) => {
                const status = record.storage_summary?.last_status;
                if (!status) return <Typography.Text type="secondary">-</Typography.Text>;
                return <Tag color={storageStatusColor[status]}>{storageStatusText[status] || status}</Tag>;
            },
        },
        {
            title: "操作",
            key: "actions",
            fixed: 'right',
            width: 400,
            render: (_: unknown, record: Movie) => {
                const ss = record.storage_summary;
                const hasMagnet = getMovieMagnetLinks(record).length > 0;
                return (
                    <Space size="small">
                        <Button type="link" size="small" onClick={() => handleViewDetail(record._id)}>
                            详情
                        </Button>
                        <Button
                            type="link"
                            size="small"
                            disabled={!hasMagnet}
                            onClick={() => handleOpenSelectMagnet(record)}
                        >
                            选择磁力
                        </Button>
                        {ss?.locations && ss.locations.length > 0 && (
                            <Button
                                type="link"
                                size="small"
                                icon={<SyncOutlined/>}
                                loading={syncLoading}
                                onClick={() => handleSyncLocation(record)}
                            >
                                同步存储
                            </Button>
                        )}
                        {ss?.last_status && ["pending", "running", "waiting_download", "downloading", "moving"].includes(ss.last_status) ? (
                            <Button type="link" size="small" disabled>
                                推送中
                            </Button>
                        ) : (
                            <Button
                                type="link"
                                size="small"
                                icon={<CloudUploadOutlined/>}
                                disabled={!hasMagnet}
                                onClick={() => handleOpenPush(record)}
                            >
                                {ss?.last_status === "completed" ? "重新推送" : "推送存储"}
                            </Button>
                        )}
                        <Popconfirm
                            title="确认删除此影片？"
                            description="删除后不可恢复"
                            onConfirm={() => handleDelete(record._id)}
                            okText="删除"
                            cancelText="取消"
                            okButtonProps={{danger: true}}
                        >
                            <Button type="link" danger size="small" icon={<DeleteOutlined/>}>
                                删除
                            </Button>
                        </Popconfirm>
                    </Space>
                );
            },
        }

    ];

    const detailMagnets = getDetailMagnets(detail?.magnets);
    const detailMagnetLinks = detailMagnets.filter((m) => typeof m.magnet === "string" && m.magnet.trim());
    const detailHasChineseSub = Boolean(detail?.has_chinese_sub) || detailMagnets.some((m) => Boolean(m.has_chinese_sub));
    const detailSizeText = getDetailSizeText(detail?.size, detailMagnets);

    return (
        <div>
            <Card size="small" style={{marginBottom: 16}}>
                <Space wrap>
                    <Select
                        style={{width: 200}}
                        value={selectedTask}
                        onChange={setSelectedTask}
                        options={taskOptions}
                        placeholder="选择任务"
                        allowClear
                    />
                    <Input
                        style={{width: 240}}
                        placeholder="搜索番号、标题..."
                        prefix={<SearchOutlined/>}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onPressEnter={() => loadMovies()}
                        allowClear
                    />
                    <Select
                        mode="tags"
                        style={{width: 200}}
                        placeholder="筛选演员"
                        value={selectedActors}
                        onChange={setSelectedActors}
                        options={actorOptions}
                        loading={filtersLoading}
                        maxTagCount="responsive"
                        allowClear
                    />
                    <Select
                        mode="tags"
                        style={{width: 200}}
                        placeholder="筛选标签"
                        value={selectedTags}
                        onChange={setSelectedTags}
                        options={tagOptions}
                        loading={filtersLoading}
                        maxTagCount="responsive"
                        allowClear
                    />
                    <Select
                        mode="tags"
                        style={{width: 200}}
                        placeholder="筛选导演"
                        value={selectedDirectors}
                        onChange={setSelectedDirectors}
                        options={directorOptions}
                        loading={filtersLoading}
                        maxTagCount="responsive"
                        allowClear
                    />
                    <Select
                        mode="tags"
                        style={{width: 200}}
                        placeholder="筛选片商"
                        value={selectedMakers}
                        onChange={setSelectedMakers}
                        options={makerOptions}
                        loading={filtersLoading}
                        maxTagCount="responsive"
                        allowClear
                    />
                    <Select
                        mode="tags"
                        style={{width: 200}}
                        placeholder="筛选系列"
                        value={selectedSeries}
                        onChange={setSelectedSeries}
                        options={seriesOptions}
                        loading={filtersLoading}
                        maxTagCount="responsive"
                        allowClear
                    />
                    <Select
                        style={{width: 160}}
                        value={storageStatus}
                        onChange={setStorageStatus}
                        placeholder="存储状态筛选"
                        allowClear
                        options={[
                            {value: "completed", label: "已完成"},
                            {value: "missing", label: "文件缺失"},
                            {value: "failed", label: "失败"},
                            {value: "pending", label: "等待中"},
                            {value: "running", label: "运行中"},
                            {value: "waiting_download", label: "等待下载"},
                            {value: "waiting_retry", label: "等待重试"},
                            {value: "retryable", label: "可重试"},
                        ]}
                    />
                    <InputNumber
                        style={{width: 120}}
                        placeholder="最低评分"
                        min={0}
                        max={5}
                        step={0.1}
                        value={ratingMin}
                        onChange={(v) => setRatingMin(v ?? undefined)}
                    />
                    <DatePicker.RangePicker
                        value={dateRange}
                        onChange={(dates) => setDateRange(dates ?? [null, null])}
                        placeholder={["开始日期", "结束日期"]}
                        style={{width: 240}}
                    />
                    <Select
                        style={{width: 140}}
                        value={`${sortBy}:${sortOrder}`}
                        onChange={(v) => {
                            const [by, order] = v.split(":");
                            setSortBy(by);
                            setSortOrder(Number(order));
                        }}
                        options={[
                            {value: "code:1", label: "番号 ↑"},
                            {value: "code:-1", label: "番号 ↓"},
                            {value: "release_date:-1", label: "发行日期 ↓"},
                            {value: "release_date:1", label: "发行日期 ↑"},
                            {value: "rating:-1", label: "评分 ↓"},
                            {value: "rating:1", label: "评分 ↑"},
                            {value: "created_at:-1", label: "抓取时间 ↓"},
                            {value: "created_at:1", label: "抓取时间 ↑"},
                        ]}
                    />
                    <Button type="primary" onClick={() => loadMovies()}>
                        搜索
                    </Button>
                    <Button icon={<ReloadOutlined/>} onClick={() => {
                        setSearch("");
                        setRatingMin(undefined);
                        setSortBy("code");
                        setSortOrder(-1);
                        setSelectedActors([]);
                        setSelectedTags([]);
                        setSelectedDirectors([]);
                        setSelectedMakers([]);
                        setSelectedSeries([]);
                        setDateRange([null, null]);
                        setStorageStatus(undefined);
                        loadMovies(1);
                    }}>
                        刷新
                    </Button>
                    <Button
                        icon={<DownloadOutlined/>}
                        onClick={handleExportMagnets}
                    >
                        导出磁力{selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length})` : ""}
                    </Button>
                    {selectedRowKeys.length > 0 && (
                        <Button
                            icon={<CloudUploadOutlined/>}
                            onClick={handleOpenBatchPush}
                        >
                            批量推送存储 ({selectedRowKeys.length})
                        </Button>
                    )}
                    {selectedRowKeys.length > 0 && (
                        <Button
                            icon={<SyncOutlined/>}
                            loading={batchSyncLoading}
                            onClick={handleBatchSync}
                        >
                            批量同步 ({selectedRowKeys.length})
                        </Button>
                    )}
                    {selectedRowKeys.length > 0 && (
                        <Popconfirm
                            title={`确认删除选中的 ${selectedRowKeys.length} 条影片？`}
                            description="删除后不可恢复"
                            onConfirm={handleBatchDelete}
                            okText="删除"
                            cancelText="取消"
                            okButtonProps={{danger: true}}
                        >
                            <Button danger icon={<DeleteOutlined/>}>
                                批量删除 ({selectedRowKeys.length})
                            </Button>
                        </Popconfirm>
                    )}
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
                            setSortBy("code");
                            setSortOrder(-1);
                        }
                    }
                }}
                scroll={{x: 1100}}
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
                        <Descriptions.Item
                            label="标题">{(detail.source_name as string) || "-"}</Descriptions.Item>
                        <Descriptions.Item label="发行日期">{detail.release_date as string}</Descriptions.Item>
                        <Descriptions.Item
                            label="时长">{detail.duration != null ? `${detail.duration}分` : "-"}</Descriptions.Item>
                        <Descriptions.Item
                            label="评分">{detail.rating != null ? (detail.rating as number).toFixed(2) : "-"}</Descriptions.Item>
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
                        <Descriptions.Item label="中文字幕">{detailHasChineseSub ? "是" : "否"}</Descriptions.Item>
                        <Descriptions.Item label="大小">{detailSizeText}</Descriptions.Item>
                        <Descriptions.Item label="封面">
                            {detail.cover as string ? (
                                <Image src={detail.cover as string} width={200} referrerPolicy="no-referrer"/>
                            ) : "-"}
                        </Descriptions.Item>
                        <Descriptions.Item label="最佳磁力">
                            {(() => {
                                const selectedKey = detail.selected_magnet_dedupe_key as string | undefined;
                                if (!selectedKey) return <Typography.Text type="secondary">未选择</Typography.Text>;
                                const selectedMagnet = detailMagnets.find((m) => m.dedupe_key === selectedKey);
                                if (!selectedMagnet) return <Typography.Text type="secondary">未找到</Typography.Text>;
                                const m = selectedMagnet;
                                const displayName = m.name || m.title || "-";
                                const displaySize = getMagnetSizeText(m);
                                const displaySub = m.has_chinese_sub ? "是" : "否";
                                const displayWeight = m.weight != null ? ` · 权重: ${m.weight}` : "";
                                return (
                                    <Space direction="vertical" size={2}>
                                        <Typography.Text strong>{displayName}</Typography.Text>
                                        <Typography.Text type="secondary">
                                            {displaySize ? `大小: ${displaySize}` : ""}
                                            {m.file_text ? ` · ${m.file_text}` : ""}
                                            {` · 中字: ${displaySub}`}
                                            {displayWeight}
                                        </Typography.Text>
                                        {m.magnet && (
                                            <Typography.Paragraph copyable={{text: m.magnet}} style={{marginBottom: 0, fontSize: 12, wordBreak: "break-all"}}>
                                                {m.magnet}
                                            </Typography.Paragraph>
                                        )}
                                    </Space>
                                );
                            })()}
                        </Descriptions.Item>
                        <Descriptions.Item label="磁力链接">
                            {detailMagnetLinks.length > 0 ? (
                                <Space direction="vertical" size={4} style={{width: "100%"}}>
                                    {detailMagnetLinks.map((magnet, index) => (
                                        <Typography.Paragraph
                                            key={`${magnet.magnet}-${index}`}
                                            copyable={{text: magnet.magnet}}
                                            style={{marginBottom: 0, whiteSpace: "pre-wrap", wordBreak: "break-all"}}
                                        >
                                            {getMagnetDisplayText(magnet)}
                                        </Typography.Paragraph>
                                    ))}
                                </Space>
                            ) : detail.magnet as string ? (
                                <Typography.Paragraph copyable style={{marginBottom: 0, wordBreak: "break-all"}}>
                                    {detail.magnet as string}
                                </Typography.Paragraph>
                            ) : "-"}
                        </Descriptions.Item>
                        <Descriptions.Item label="来源URL">
                            <Typography.Link href={detail.source_url as string} target="_blank">
                                {detail.source_url as string}
                            </Typography.Link>
                        </Descriptions.Item>
                        {(() => {
                            const storageSummary = detail.storage_summary as Record<string, unknown> | undefined;
                            const locations = storageSummary?.locations as { path: string; target_folder: string; exists?: boolean }[] | undefined;
                            if (!locations || locations.length === 0) return null;
                            return (
                                <Descriptions.Item label="存储位置">
                                    <Space direction="vertical" size={4} style={{width: "100%"}}>
                                        {locations.map((loc, index) => (
                                            <div key={`${loc.path}-${index}`} style={{display: "flex", alignItems: "center", gap: 8}}>
                                                <Tag color={loc.exists ? "success" : "error"}>
                                                    {loc.exists ? "存在" : "缺失"}
                                                </Tag>
                                                <Typography.Text copyable={{text: loc.path}} style={{fontSize: 12, wordBreak: "break-all"}}>
                                                    {loc.path}
                                                </Typography.Text>
                                                <Typography.Text type="secondary" style={{fontSize: 12}}>
                                                    ({loc.target_folder})
                                                </Typography.Text>
                                            </div>
                                        ))}
                                    </Space>
                                </Descriptions.Item>
                            );
                        })()}
                        {(() => {
                            const storageSummary = detail.storage_summary as Record<string, unknown> | undefined;
                            const syncedAt = storageSummary?.synced_at as string | undefined;
                            if (!syncedAt) return null;
                            return (
                                <Descriptions.Item label="最后同步时间">
                                    {syncedAt}
                                </Descriptions.Item>
                            );
                        })()}
                    </Descriptions>
                )}
            </Drawer>

            {/* Single push modal */}
            <Modal
                title="推送存储"
                open={pushModalOpen}
                onCancel={() => setPushModalOpen(false)}
                onOk={handleConfirmPush}
                okText="确认推送"
                cancelText="取消"
                confirmLoading={pushLoading}
                okButtonProps={{disabled: !pushMagnet}}
            >
                {pushMovie && (
                    <Descriptions column={1} size="small" bordered style={{marginBottom: 16}}>
                        <Descriptions.Item label="番号">{pushMovie.code}</Descriptions.Item>
                        <Descriptions.Item
                            label="标题">{pushMovie.source_name || "-"}</Descriptions.Item>
                    </Descriptions>
                )}
                <div style={{marginBottom: 12}}>
                    <Typography.Text strong>选择磁力链接</Typography.Text>
                    <Select
                        style={{width: "100%", marginTop: 4}}
                        placeholder="选择磁力链接"
                        value={pushMagnet}
                        onChange={setPushMagnet}
                        options={pushMovie ? getMagnetOptions(pushMovie) : []}
                        showSearch
                        optionFilterProp="label"
                    />
                </div>
                {pushMagnet && (
                    <Typography.Paragraph type="secondary"
                                          style={{fontSize: 12, wordBreak: "break-all", marginBottom: 0}}>
                        {pushMagnet}
                    </Typography.Paragraph>
                )}
            </Modal>

            {/* Batch push modal */}
            <Modal
                title="批量推送存储"
                open={batchPushOpen}
                onCancel={() => {
                    setBatchPushOpen(false);
                    setBatchResult(null);
                }}
                onOk={batchResult ? () => {
                    setBatchPushOpen(false);
                    setBatchResult(null);
                    setSelectedRowKeys([]);
                } : handleConfirmBatchPush}
                okText={batchResult ? "完成" : "确认推送"}
                cancelText={batchResult ? undefined : "取消"}
                cancelButtonProps={batchResult ? {style: {display: "none"}} : undefined}
                confirmLoading={batchPushLoading}
            >
                {!batchResult ? (
                    <>
                        <Descriptions column={1} size="small" bordered style={{marginBottom: 16}}>
                            <Descriptions.Item label="选中影片">{selectedRowKeys.length} 部</Descriptions.Item>
                        </Descriptions>
                        <Space direction="vertical" style={{width: "100%"}}>
                            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                                <Typography.Text>跳过运行中的任务</Typography.Text>
                                <Switch checked={batchSkipRunning} onChange={setBatchSkipRunning}/>
                            </div>
                            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                                <Typography.Text>跳过已完成的任务</Typography.Text>
                                <Switch checked={batchSkipCompleted} onChange={setBatchSkipCompleted}/>
                            </div>
                            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                                <Typography.Text>重试失败的任务</Typography.Text>
                                <Switch checked={batchRetryFailed} onChange={setBatchRetryFailed}/>
                            </div>
                        </Space>
                    </>
                ) : (
                    <>
                        <Row gutter={16} style={{marginBottom: 16}}>
                            <Col span={8}>
                                <Statistic title="选中" value={batchResult.requested}/>
                            </Col>
                            <Col span={8}>
                                <Statistic title="创建/重试" value={batchResult.created}
                                           valueStyle={{color: "#3f8600"}}/>
                            </Col>
                            <Col span={8}>
                                <Statistic title="跳过" value={batchResult.skipped} valueStyle={{color: "#999"}}/>
                            </Col>
                        </Row>
                        {batchResult.items.filter((i) => i.result === "skipped").length > 0 && (
                            <Typography.Paragraph type="secondary"
                                                  style={{fontSize: 12, maxHeight: 200, overflow: "auto"}}>
                                跳过详情：
                                {batchResult.items
                                    .filter((i) => i.result === "skipped")
                                    .map((i) => (
                                        <div key={i.movie_id}>{i.movie_id} — {i.reason}</div>
                                    ))}
                            </Typography.Paragraph>
                        )}
                    </>
                )}
            </Modal>

            {/* Batch sync result modal */}
            <Modal
                title="批量同步结果"
                open={batchSyncResult !== null}
                onCancel={() => setBatchSyncResult(null)}
                footer={
                    <Button type="primary" onClick={() => setBatchSyncResult(null)}>
                        完成
                    </Button>
                }
            >
                {batchSyncResult && (
                    <>
                        <Row gutter={16} style={{marginBottom: 16}}>
                            <Col span={12}>
                                <Statistic title="总数" value={batchSyncResult.total}/>
                            </Col>
                            <Col span={12}>
                                <Statistic
                                    title="成功"
                                    value={batchSyncResult.results.filter((r) => r.synced).length}
                                    valueStyle={{color: "#3f8600"}}
                                />
                            </Col>
                        </Row>
                        {batchSyncResult.results.filter((r) => !r.synced).length > 0 && (
                            <Typography.Paragraph type="secondary" style={{fontSize: 12, maxHeight: 200, overflow: "auto"}}>
                                未同步详情：
                                {batchSyncResult.results
                                    .filter((r) => !r.synced)
                                    .map((r) => (
                                        <div key={r.movie_id}>{r.movie_id}</div>
                                    ))}
                            </Typography.Paragraph>
                        )}
                    </>
                )}
            </Modal>

            {/* Magnet selection modal */}
            <Modal
                title={`选择最佳磁力 - ${selectMagnetMovie?.code || ""}`}
                open={selectMagnetOpen}
                onCancel={() => setSelectMagnetOpen(false)}
                footer={null}
                width={800}
            >
                {selectMagnetMovie && (
                    <Table
                        dataSource={(selectMagnetMovie.magnets ?? [])
                            .filter((m) => Boolean(m.magnet?.trim()))
                            .sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0))}
                        rowKey={(m) => (m as MovieMagnet).magnet}
                        pagination={false}
                        size="small"
                        columns={[
                            {
                                title: "名称",
                                dataIndex: "name",
                                key: "name",
                                render: (_: unknown, record: MovieMagnet) => record.name || record.title || "-",
                            },
                            {
                                title: "大小",
                                dataIndex: "size_text",
                                key: "size",
                                width: 120,
                                render: (_: unknown, record: MovieMagnet) => getMagnetSizeText(record) || "-",
                            },
                            {
                                title: "中字",
                                dataIndex: "has_chinese_sub",
                                key: "has_chinese_sub",
                                width: 60,
                                render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
                            },
                            {
                                title: "文件数",
                                dataIndex: "file_count",
                                key: "file_count",
                                width: 80,
                                render: (_: unknown, record: MovieMagnet) => record.file_text || (record.file_count != null ? String(record.file_count) : "-"),
                            },
                            {
                                title: "标签",
                                dataIndex: "tags",
                                key: "tags",
                                render: (tags: string[]) =>
                                    Array.isArray(tags) && tags.length > 0
                                        ? <Space size={[0, 4]} wrap>{tags.map((t) => <Tag key={t}>{t}</Tag>)}</Space>
                                        : "-",
                            },
                            {
                                title: "权重",
                                dataIndex: "weight",
                                key: "weight",
                                width: 80,
                                sorter: (a: MovieMagnet, b: MovieMagnet) => (a.weight ?? 0) - (b.weight ?? 0),
                                defaultSortOrder: "descend" as const,
                                render: (v: number) => v != null ? v : "-",
                            },
                            {
                                title: "操作",
                                key: "action",
                                width: 80,
                                render: (_: unknown, record: MovieMagnet) => {
                                    const dedupeKey = record.dedupe_key as string | undefined;
                                    const isSelected = dedupeKey && selectMagnetMovie.selected_magnet_dedupe_key === dedupeKey;
                                    if (isSelected) {
                                        return <Typography.Text type="success">当前</Typography.Text>;
                                    }
                                    return (
                                        <Button
                                            type="primary"
                                            size="small"
                                            loading={selectMagnetLoading}
                                            onClick={() => dedupeKey && handleSelectMagnet(dedupeKey)}
                                        >
                                            选择
                                        </Button>
                                    );
                                },
                            },
                        ]}
                    />
                )}
            </Modal>
        </div>
    );
}
