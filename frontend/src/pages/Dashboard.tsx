import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, ArrowRight, Clock, CheckCircle, AlertCircle, Languages, BookOpen, Trash2, Search, Highlighter, Brain, Settings, Radar, Link as LinkIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api, { getLLMConfig } from "@/lib/api";
import LLMSettings from "@/components/LLMSettings";

interface Task {
    task_id: string;
    filename: string;
    status: "pending" | "processing" | "parsing" | "rewriting" | "rendering" | "highlighting" | "completed" | "failed";
    created_at: string;
    percent?: number;
    message?: string;
    mode?: "translate" | "simplify" | "zh2en";
    highlight?: boolean;
}

const Dashboard = () => {
    const { t } = useTranslation();
    const [tasks, setTasks] = useState<Task[]>([]);
    const [mode, setMode] = useState<"translate" | "simplify" | "zh2en">("translate");
    const [search, setSearch] = useState("");
    const [highlight, setHighlight] = useState(false);
    const [uploadProgress, setUploadProgress] = useState<number | null>(null);
    const [dragging, setDragging] = useState(false);
    const [queueInfo, setQueueInfo] = useState<{ processing: number; queued: number } | null>(null);
    const [radarStatus, setRadarStatus] = useState<any>(null);
    const [urlInput, setUrlInput] = useState("");
    const [kbSearch, setKbSearch] = useState("");
    const [kbResults, setKbResults] = useState<any[]>([]);
    const navigate = useNavigate();
    const abortRef = useRef<AbortController | null>(null);
    const pollIntervalRef = useRef<number>(2000);
    const [showSetup, setShowSetup] = useState(false);
    const hasLLMConfig = !!getLLMConfig();

    const fetchTasks = useCallback(async () => {
        try {
            abortRef.current?.abort();
            abortRef.current = new AbortController();
            const [tasksRes, queueRes, radarRes] = await Promise.all([
                api.get("/api/tasks", { signal: abortRef.current.signal }),
                api.get("/api/queue", { signal: abortRef.current.signal }),
                api.get("/api/radar/status", { signal: abortRef.current.signal }).catch(() => null),
            ]);
            setTasks(tasksRes.data);
            setQueueInfo(queueRes.data);
            if (radarRes) setRadarStatus(radarRes.data);
        } catch (error: any) {
            if (error.name === "CanceledError") return;
        }
    }, []);

    useEffect(() => {
        fetchTasks();

        const tick = () => {
            const hasActive = tasks.some((t) =>
                ["pending", "processing", "parsing", "rewriting", "rendering", "highlighting"].includes(t.status)
            );
            pollIntervalRef.current = hasActive ? 2000 : 15000;
        };
        tick();

        const id = setInterval(() => {
            tick();
            fetchTasks();
        }, pollIntervalRef.current);

        return () => {
            clearInterval(id);
            abortRef.current?.abort();
        };
    }, [fetchTasks, tasks.length, tasks.map((t) => t.status).join(",")]);

    const validateFile = (file: File): boolean => {
        if (file.type !== "application/pdf") {
            toast.error(t("dashboard.onlyPdf"));
            return false;
        }
        return true;
    };

    const uploadFile = async (file: File) => {
        if (!validateFile(file)) return;

        const formData = new FormData();
        formData.append("file", file);
        formData.append("mode", mode);
        formData.append("highlight", String(highlight));

        setUploadProgress(0);
        try {
            await api.post("/api/upload", formData, {
                onUploadProgress: (e) => {
                    if (e.total) {
                        setUploadProgress(Math.round((e.loaded / e.total) * 100));
                    }
                },
            });
            toast.success(t("dashboard.uploadSuccess", { name: file.name }));
            fetchTasks();
        } catch (error: any) {
            const msg = error.response?.data?.detail || t("dashboard.uploadFailed");
            toast.error(msg);
        } finally {
            setUploadProgress(null);
        }
    };

    const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        const file = e.target.files[0];
        e.target.value = "";
        uploadFile(file);
    };

    const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragging(true); };
    const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setDragging(false); };
    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) uploadFile(file);
    };

    const handleDelete = async (taskId: string) => {
        try {
            await api.delete(`/api/tasks/${taskId}`);
            setTasks((prev) => prev.filter((t) => t.task_id !== taskId));
            toast.success(t("dashboard.taskDeleted"));
        } catch {
            toast.error(t("dashboard.taskDeleteFailed"));
        }
    };

    const handleUrlUpload = async () => {
        if (!urlInput.trim()) return;
        try {
            await api.post("/api/upload-url", { url: urlInput.trim(), mode, highlight });
            toast.success(t("dashboard.urlFetched"));
            setUrlInput("");
            fetchTasks();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || t("dashboard.urlFetchFailed"));
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case "completed": return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/40 border-green-200 dark:border-green-800";
            case "processing": case "parsing": case "rewriting": case "rendering": case "highlighting":
                return "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800";
            case "failed": return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800";
            default: return "text-muted-foreground bg-muted border-border";
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "completed": return <CheckCircle className="h-4 w-4" />;
            case "processing": case "parsing": case "rewriting": case "rendering": case "highlighting":
                return <Clock className="h-4 w-4 animate-pulse" />;
            case "failed": return <AlertCircle className="h-4 w-4" />;
            default: return <Clock className="h-4 w-4" />;
        }
    };

    const filteredTasks = search
        ? tasks.filter((t) => t.filename.toLowerCase().includes(search.toLowerCase()))
        : tasks;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {!hasLLMConfig && (
                <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 p-6 text-center space-y-3">
                    <h2 className="text-lg font-semibold">{t("dashboard.welcome")}</h2>
                    <p className="text-sm text-muted-foreground">{t("dashboard.welcomeDesc")}</p>
                    <div className="flex items-center justify-center gap-3">
                        <Button onClick={() => setShowSetup(true)} className="gap-2">
                            <Settings className="h-4 w-4" /> {t("dashboard.setupKey")}
                        </Button>
                        <a href="https://github.com/neosun100/PaperRadar" target="_blank" rel="noopener noreferrer">
                            <Button variant="outline" className="gap-2">{t("dashboard.starOnGithub")}</Button>
                        </a>
                    </div>
                </div>
            )}
            <LLMSettings open={showSetup} onOpenChange={setShowSetup} />

            {/* Radar Status Panel */}
            {/* Stats Overview */}
            {(tasks.length > 0 || radarStatus?.papers_found > 0) && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <div className="rounded-xl border bg-card p-4 text-center">
                        <p className="text-2xl font-bold text-primary">{tasks.length}</p>
                        <p className="text-xs text-muted-foreground">{t("dashboard.recentDocs")}</p>
                    </div>
                    <div className="rounded-xl border bg-card p-4 text-center">
                        <p className="text-2xl font-bold text-green-600">{tasks.filter(t => t.status === "completed").length}</p>
                        <p className="text-xs text-muted-foreground">{t("dashboard.completed")}</p>
                    </div>
                    <div className="rounded-xl border bg-card p-4 text-center cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate("/knowledge")}>
                        <p className="text-2xl font-bold text-violet-600">{radarStatus?.papers_found || 0}</p>
                        <p className="text-xs text-muted-foreground">{t("radar.found")}</p>
                    </div>
                    <div className="rounded-xl border bg-card p-4 text-center cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate("/radar")}>
                        <p className="text-2xl font-bold text-emerald-600">{radarStatus?.scan_count || 0}</p>
                        <p className="text-xs text-muted-foreground">{t("radar.scans")}</p>
                    </div>
                    <div className="rounded-xl border bg-card p-4 text-center cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate("/knowledge")}>
                        <p className="text-2xl font-bold text-blue-600">🔍</p>
                        <p className="text-xs text-muted-foreground">Semantic Search</p>
                    </div>
                </div>
            )}

            {radarStatus?.enabled && (
                <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 p-5 space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={cn("relative flex h-10 w-10 items-center justify-center rounded-full", radarStatus.running ? "bg-emerald-500" : "bg-emerald-600/80")}>
                                <Radar className={cn("h-5 w-5 text-white", radarStatus.running && "animate-spin")} />
                                {radarStatus.running && <span className="absolute inset-0 rounded-full border-2 border-emerald-400 animate-ping" />}
                            </div>
                            <div>
                                <h3 className="font-semibold text-sm">{t("radar.title")}</h3>
                                <p className="text-xs text-muted-foreground">
                                    {radarStatus.running ? t("radar.scanning") : t("radar.idle")}
                                    {radarStatus.scan_count > 0 && ` · ${radarStatus.scan_count} ${t("radar.scans")}`}
                                    {radarStatus.papers_found > 0 && ` · ${radarStatus.papers_found} ${t("radar.found")}`}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            {radarStatus.last_scan && <span>{t("radar.lastScan")}: {new Date(radarStatus.last_scan).toLocaleTimeString()}</span>}
                            <span className="text-[10px] bg-muted px-2 py-0.5 rounded-full">{radarStatus.categories?.join(", ")}</span>
                            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={() => navigate("/radar")}>
                                {t("radar.title")} →
                            </Button>
                        </div>
                    </div>
                    {radarStatus.recent_papers?.length > 0 && (
                        <div className="space-y-1.5">
                            <p className="text-xs font-medium text-muted-foreground">{t("radar.recentDiscoveries")}:</p>
                            <div className="grid gap-1.5 md:grid-cols-2 lg:grid-cols-3">
                                {radarStatus.recent_papers.slice(-6).reverse().map((p: any, i: number) => (
                                    <div key={i} className="flex items-start gap-2 rounded-lg bg-white/60 dark:bg-white/5 border border-border p-2.5">
                                        <span className={cn("shrink-0 mt-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-mono font-bold",
                                            p.score >= 0.9 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" :
                                            p.score >= 0.8 ? "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300" :
                                            "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                                        )}>{Math.round(p.score * 100)}%</span>
                                        <div className="min-w-0">
                                            <p className="text-xs font-medium leading-tight line-clamp-2">{p.title}</p>
                                            <p className="text-[10px] text-muted-foreground mt-0.5">
                                                {p.authors?.slice(0, 2).join(", ")}
                                                {p.source && <span className="ml-1.5 bg-muted px-1 py-0.5 rounded text-[9px]">{p.source}</span>}
                                                {p.upvotes > 0 && <span className="ml-1 text-amber-500">⬆{p.upvotes}</span>}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            <section
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={cn(
                    "relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary/5 via-primary/10 to-transparent p-8 md:p-12 text-center border shadow-sm transition-all",
                    dragging ? "border-primary border-dashed border-2 bg-primary/5 scale-[1.01]" : "border-primary/10"
                )}
            >
                <div className="relative z-10 mx-auto max-w-2xl space-y-6">
                    <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">{t("dashboard.title")}</h1>
                    <p className="text-lg text-muted-foreground">{t("dashboard.subtitle")}</p>

                    <div className="flex flex-wrap justify-center gap-3">
                        <button onClick={() => setMode("translate")} className={cn("flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all", mode === "translate" ? "bg-primary text-primary-foreground shadow-md" : "bg-white/80 dark:bg-white/5 text-muted-foreground border border-border hover:bg-accent")}>
                            <Languages className="h-4 w-4" /> {t("dashboard.translateToChinese")}
                        </button>
                        <button onClick={() => setMode("zh2en")} className={cn("flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all", mode === "zh2en" ? "bg-primary text-primary-foreground shadow-md" : "bg-white/80 dark:bg-white/5 text-muted-foreground border border-border hover:bg-accent")}>
                            <Languages className="h-4 w-4" /> {t("dashboard.translateToEnglish")}
                        </button>
                        <button onClick={() => setMode("simplify")} className={cn("flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all", mode === "simplify" ? "bg-primary text-primary-foreground shadow-md" : "bg-white/80 dark:bg-white/5 text-muted-foreground border border-border hover:bg-accent")}>
                            <BookOpen className="h-4 w-4" /> {t("dashboard.simplifyEnglish")}
                        </button>
                        <button onClick={() => setHighlight(!highlight)} className={cn("flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all", highlight ? "bg-amber-500 text-white shadow-md" : "bg-white/80 dark:bg-white/5 text-muted-foreground border border-border hover:bg-accent")}>
                            <Highlighter className="h-4 w-4" /> {t("dashboard.aiHighlights")}
                        </button>
                    </div>

                    <div className="flex flex-col items-center gap-3 pt-2">
                        {dragging ? (
                            <p className="text-primary font-medium text-lg">{t("dashboard.dropPdfHere")}</p>
                        ) : (
                            <Label htmlFor="file-upload" className={cn("group relative flex cursor-pointer items-center justify-center gap-3 rounded-full bg-primary px-8 py-4 text-lg font-medium text-primary-foreground shadow-lg transition-all hover:bg-primary/90 hover:shadow-xl hover:scale-105 active:scale-95")}>
                                <Upload className="h-5 w-5" />
                                <span>{t("dashboard.uploadPdf")}</span>
                                <Input id="file-upload" type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
                            </Label>
                        )}
                        <p className="text-xs text-muted-foreground">{t("dashboard.dragHint")}</p>
                        {/* URL Upload */}
                        <div className="flex items-center gap-2 w-full max-w-md">
                            <Input
                                placeholder={t("dashboard.urlPlaceholder")}
                                value={urlInput}
                                onChange={(e) => setUrlInput(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter") handleUrlUpload(); }}
                                className="h-9 text-sm"
                            />
                            <Button size="sm" onClick={handleUrlUpload} disabled={!urlInput.trim()} className="shrink-0 gap-1.5">
                                <LinkIcon className="h-3.5 w-3.5" /> {t("dashboard.fetchPdf")}
                            </Button>
                        </div>
                        {/* Knowledge Search */}
                        <div className="flex items-center gap-2 w-full max-w-md">
                            <Input
                                placeholder="🔍 Search knowledge base... (semantic)"
                                value={kbSearch}
                                onChange={(e) => setKbSearch(e.target.value)}
                                onKeyDown={async (e) => {
                                    if (e.key === "Enter" && kbSearch.trim()) {
                                        try {
                                            const r = await api.get(`/api/knowledge/search?q=${encodeURIComponent(kbSearch)}&n=5`);
                                            setKbResults(r.data.results);
                                        } catch { setKbResults([]); }
                                    }
                                }}
                                className="h-9 text-sm"
                            />
                        </div>
                        {kbResults.length > 0 && (
                            <div className="w-full max-w-md space-y-1.5 text-left">
                                {kbResults.map((r: any, i: number) => (
                                    <div key={i} className="flex items-start gap-2 rounded-lg bg-white/60 dark:bg-white/5 border p-2 text-xs">
                                        <span className="shrink-0 text-emerald-600 font-mono">{(r.score * 100).toFixed(0)}%</span>
                                        <span className="line-clamp-2">{r.text}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                        {uploadProgress !== null && (
                            <div className="w-full max-w-xs space-y-1">
                                <div className="flex justify-between text-xs text-muted-foreground">
                                    <span>{t("dashboard.uploading")}</span>
                                    <span>{uploadProgress}%</span>
                                </div>
                                <Progress value={uploadProgress} className="h-2" />
                            </div>
                        )}
                    </div>
                </div>
                <div className="absolute top-0 left-0 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full bg-blue-200/30 dark:bg-blue-500/10 blur-3xl" />
                <div className="absolute bottom-0 right-0 translate-x-1/2 translate-y-1/2 h-64 w-64 rounded-full bg-purple-200/30 dark:bg-purple-500/10 blur-3xl" />
            </section>

            <section className="space-y-4">
                <div className="flex items-center justify-between gap-4 px-2">
                    <div className="flex items-center gap-3 shrink-0">
                        <h2 className="text-2xl font-semibold tracking-tight">{t("dashboard.recentDocs")}</h2>
                        {queueInfo && (queueInfo.processing > 0 || queueInfo.queued > 0) && (
                            <div className="flex items-center gap-2">
                                {queueInfo.processing > 0 && (
                                    <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 px-2.5 py-0.5 text-xs font-medium text-blue-600 dark:text-blue-400">
                                        <Clock className="h-3 w-3 animate-pulse" />
                                        {t("dashboard.processingCount", { count: queueInfo.processing })}
                                    </span>
                                )}
                                {queueInfo.queued > 0 && (
                                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
                                        {t("dashboard.queuedCount", { count: queueInfo.queued })}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                    {tasks.length > 0 && (
                        <div className="relative max-w-xs w-full">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input placeholder={t("dashboard.searchDocs")} value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 h-9" />
                        </div>
                    )}
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {filteredTasks.map((task) => (
                        <Card key={task.task_id} className="group relative overflow-hidden transition-all hover:shadow-md border-border">
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                                            <FileText className="h-5 w-5" />
                                        </div>
                                        <div className="space-y-1">
                                            <CardTitle className="text-base font-medium leading-none line-clamp-1" title={task.filename}>{task.filename}</CardTitle>
                                            <CardDescription className="text-xs flex items-center gap-1.5">
                                                {new Date(task.created_at).toLocaleDateString()}
                                                <span className="inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                                                    {task.mode === "simplify" ? t("dashboard.simplify") : task.mode === "zh2en" ? "ZH→EN" : t("dashboard.translate")}
                                                </span>
                                                {task.highlight && (
                                                    <span className="inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-600">{t("dashboard.highlighted")}</span>
                                                )}
                                            </CardDescription>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        <div className={cn("flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border", getStatusColor(task.status))}>
                                            {getStatusIcon(task.status)}
                                            <span className="capitalize">{task.status}</span>
                                        </div>
                                        <Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-red-600" onClick={() => handleDelete(task.task_id)}>
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {["processing", "parsing", "rewriting", "rendering", "highlighting"].includes(task.status) && (
                                        <div className="space-y-1.5">
                                            <div className="flex justify-between text-xs text-muted-foreground">
                                                <span>{task.message || t("dashboard.processing")}</span>
                                                <span>{task.percent || 0}%</span>
                                            </div>
                                            <Progress value={task.percent || 0} className="h-1.5" />
                                        </div>
                                    )}
                                    {task.status === "completed" && (
                                        <div className="flex gap-2">
                                            <Button className="flex-1 gap-2 group-hover:bg-primary group-hover:text-primary-foreground" variant="outline" onClick={() => navigate(`/reader/${task.task_id}`)}>
                                                {t("dashboard.read")}
                                                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                                            </Button>
                                            <Button
                                                variant="outline" size="icon"
                                                className="shrink-0 text-violet-600 dark:text-violet-400 hover:bg-violet-50 dark:hover:bg-violet-950/40 hover:text-violet-700 dark:hover:text-violet-300 border-violet-200 dark:border-violet-800"
                                                title={t("dashboard.extractKnowledge")}
                                                onClick={async (e) => {
                                                    e.stopPropagation();
                                                    try {
                                                        await api.post(`/api/knowledge/extract/${task.task_id}`);
                                                        toast.success(t("dashboard.extractionStarted"));
                                                    } catch {
                                                        toast.error(t("dashboard.extractionFailed"));
                                                    }
                                                }}
                                            >
                                                <Brain className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    )}
                                    {task.status === "pending" && (
                                        <p className="text-xs text-muted-foreground">{task.message || "Queued for processing..."}</p>
                                    )}
                                    {task.status === "failed" && (
                                        <p className="text-xs text-red-500">{task.message || "Processing failed"}</p>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))}

                    {filteredTasks.length === 0 && (
                        <div className="col-span-full py-12 text-center text-muted-foreground bg-muted/50 rounded-xl border border-dashed">
                            <p>{search ? t("dashboard.noDocsMatch") : t("dashboard.noDocs")}</p>
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
};

export default Dashboard;
