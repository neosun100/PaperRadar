import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Download, Loader2, FileText, Sparkles, Palette, Brain, MessageSquare, Lightbulb, Trash2, Send, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

interface HighlightStats {
    core_conclusions: number;
    method_innovations: number;
    key_data: number;
    total: number;
}

interface Annotation {
    id: string;
    type: string;
    content: string;
    color: string;
    target_type: string;
    target_id: string;
    tags: string[];
    created_at: string;
}

const COLORS = [
    { key: "yellow", bg: "bg-yellow-100 dark:bg-yellow-900/40", border: "border-yellow-300 dark:border-yellow-700", dot: "bg-yellow-400" },
    { key: "blue", bg: "bg-blue-100 dark:bg-blue-900/40", border: "border-blue-300 dark:border-blue-700", dot: "bg-blue-400" },
    { key: "green", bg: "bg-green-100 dark:bg-green-900/40", border: "border-green-300 dark:border-green-700", dot: "bg-green-400" },
    { key: "pink", bg: "bg-pink-100 dark:bg-pink-900/40", border: "border-pink-300 dark:border-pink-700", dot: "bg-pink-400" },
];

const Reader = () => {
    const { t } = useTranslation();
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const [status, setStatus] = useState<string>("loading");
    const [originalPdfUrl, setOriginalPdfUrl] = useState<string | null>(null);
    const [resultPdfUrl, setResultPdfUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [focusMode, setFocusMode] = useState(() => window.innerWidth < 768);
    const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768);
    const [highlightStats, setHighlightStats] = useState<HighlightStats | null>(null);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Annotation state
    const [sidePanel, setSidePanel] = useState<"none" | "annotations" | "explain">("none");
    const [paperId, setPaperId] = useState<string | null>(null);
    const [annotations, setAnnotations] = useState<Annotation[]>([]);
    const [newNote, setNewNote] = useState("");
    const [noteColor, setNoteColor] = useState("yellow");
    const [noteType, setNoteType] = useState<"note" | "highlight" | "question">("note");

    // AI Explain state
    const [explainText, setExplainText] = useState("");
    const [explanation, setExplanation] = useState("");
    const [explaining, setExplaining] = useState(false);

    useEffect(() => {
        const onResize = () => {
            const mobile = window.innerWidth < 768;
            setIsMobile(mobile);
            if (mobile) setFocusMode(true);
        };
        window.addEventListener("resize", onResize);
        return () => window.removeEventListener("resize", onResize);
    }, []);

    // Fetch paper_id from task_id + record reading event
    useEffect(() => {
        if (!taskId) return;
        api.get(`/api/knowledge/paper-by-task/${taskId}`)
            .then((r) => {
                setPaperId(r.data.paper_id);
                api.post("/api/knowledge/reading-events", { paper_id: r.data.paper_id, task_id: taskId, event_type: "read" }).catch(() => {});
            })
            .catch(() => {});
    }, [taskId]);

    // Load annotations when paperId is available and panel is open
    const loadAnnotations = useCallback(() => {
        if (!paperId) return;
        api.get(`/api/knowledge/papers/${paperId}/annotations`)
            .then((r) => setAnnotations(r.data))
            .catch(() => {});
    }, [paperId]);

    useEffect(() => {
        if (sidePanel === "annotations" && paperId) loadAnnotations();
    }, [sidePanel, paperId, loadAnnotations]);

    useEffect(() => {
        let cancelled = false;
        const fetchStatus = async () => {
            try {
                const response = await api.get(`/api/status/${taskId}`);
                if (cancelled) return;
                setStatus(response.data.status);
                if (response.data.status === "completed") {
                    if (response.data.highlight_stats) setHighlightStats(response.data.highlight_stats);
                    const [originalResponse, resultResponse] = await Promise.all([
                        api.get(`/api/original/${taskId}/pdf`, { responseType: "blob" }),
                        api.get(`/api/result/${taskId}/pdf`, { responseType: "blob" }),
                    ]);
                    if (cancelled) return;
                    setOriginalPdfUrl(URL.createObjectURL(new Blob([originalResponse.data], { type: "application/pdf" })));
                    setResultPdfUrl(URL.createObjectURL(new Blob([resultResponse.data], { type: "application/pdf" })));
                    setLoading(false);
                } else if (response.data.status === "failed" || response.data.status === "error") {
                    setLoading(false);
                } else {
                    timeoutRef.current = setTimeout(fetchStatus, 2000);
                }
            } catch {
                if (cancelled) return;
                setLoading(false);
                setStatus("error");
            }
        };
        fetchStatus();
        return () => { cancelled = true; if (timeoutRef.current) clearTimeout(timeoutRef.current); };
    }, [taskId]);

    useEffect(() => {
        return () => {
            if (originalPdfUrl) URL.revokeObjectURL(originalPdfUrl);
            if (resultPdfUrl) URL.revokeObjectURL(resultPdfUrl);
        };
    }, [originalPdfUrl, resultPdfUrl]);

    const handleDownload = () => {
        if (resultPdfUrl) {
            const link = document.createElement("a");
            link.href = resultPdfUrl;
            link.setAttribute("download", `simplified_${taskId}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
        }
    };

    const handleAddAnnotation = async () => {
        if (!paperId || !newNote.trim()) return;
        try {
            await api.post(`/api/knowledge/papers/${paperId}/annotations`, {
                type: noteType, content: newNote.trim(), color: noteColor,
                target_type: "paper", target_id: taskId || "",
            });
            toast.success(t("reader.annotationAdded"));
            setNewNote("");
            loadAnnotations();
        } catch {
            toast.error(t("reader.annotationFailed"));
        }
    };

    const handleDeleteAnnotation = async (annId: string) => {
        try {
            await api.delete(`/api/knowledge/annotations/${annId}`);
            toast.success(t("reader.annotationDeleted"));
            setAnnotations((prev) => prev.filter((a) => a.id !== annId));
        } catch {}
    };

    const handleExplain = async () => {
        if (!explainText.trim()) return;
        setExplaining(true);
        setExplanation("");
        try {
            const r = await api.post("/api/knowledge/explain", { text: explainText.trim() });
            setExplanation(r.data.explanation);
        } catch {
            toast.error(t("reader.explainFailed"));
        } finally {
            setExplaining(false);
        }
    };

    if (loading || status === "processing" || status === "pending" || status === "parsing" || status === "rewriting" || status === "rendering" || status === "highlighting") {
        return (
            <div className="flex h-[calc(100vh-4rem)] flex-col items-center justify-center space-y-4">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                <p className="text-lg font-medium text-muted-foreground">
                    {["processing", "parsing", "rewriting", "rendering", "highlighting"].includes(status) ? t("reader.processingDoc") : t("reader.loading")}
                </p>
            </div>
        );
    }

    if (status === "failed" || status === "error") {
        return (
            <div className="flex h-[calc(100vh-4rem)] flex-col items-center justify-center space-y-4">
                <div className="rounded-full bg-red-100 p-4 text-red-600"><FileText className="h-8 w-8" /></div>
                <h2 className="text-xl font-semibold">{t("reader.processingFailed")}</h2>
                <p className="text-muted-foreground">{t("reader.processingFailedDesc")}</p>
                <Button onClick={() => navigate("/dashboard")}>{t("reader.backToDashboard")}</Button>
            </div>
        );
    }

    const sidePanelOpen = sidePanel !== "none";

    return (
        <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
            {/* Toolbar */}
            <div className="flex items-center justify-between rounded-xl border bg-card p-3 shadow-sm">
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
                        <ArrowLeft className="mr-2 h-4 w-4" /> {t("reader.back")}
                    </Button>
                    <div className="h-4 w-px bg-border mx-2 hidden sm:block" />
                    <h1 className="text-sm font-medium text-foreground hidden sm:block">{t("reader.docReader")}</h1>
                </div>
                <div className="flex items-center gap-2">
                    {highlightStats && highlightStats.total > 0 && (
                        <>
                            <div className="hidden md:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-muted border text-xs">
                                <div className="flex items-center gap-1.5">
                                    <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: "rgb(255, 242, 153)" }} />
                                    <span className="text-muted-foreground">{t("reader.conclusions")} ({highlightStats.core_conclusions})</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: "rgb(179, 217, 255)" }} />
                                    <span className="text-muted-foreground">{t("reader.methods")} ({highlightStats.method_innovations})</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: "rgb(179, 255, 179)" }} />
                                    <span className="text-muted-foreground">{t("reader.data")} ({highlightStats.key_data})</span>
                                </div>
                            </div>
                            <Button variant="ghost" size="sm" className="md:hidden" title={`Highlights: ${highlightStats.core_conclusions} conclusions, ${highlightStats.method_innovations} methods, ${highlightStats.key_data} data`}>
                                <Palette className="h-4 w-4 text-amber-500" />
                            </Button>
                        </>
                    )}
                    {/* Annotations toggle */}
                    <Button variant="outline" size="sm"
                        className={cn("gap-2", sidePanel === "annotations" && "bg-amber-50 dark:bg-amber-950/40 text-amber-600 border-amber-200 dark:border-amber-800")}
                        onClick={() => setSidePanel(sidePanel === "annotations" ? "none" : "annotations")}>
                        <MessageSquare className="h-4 w-4" />
                        <span className="hidden sm:inline">{t("reader.annotations")}</span>
                    </Button>
                    {/* AI Explain toggle */}
                    <Button variant="outline" size="sm"
                        className={cn("gap-2", sidePanel === "explain" && "bg-violet-50 dark:bg-violet-950/40 text-violet-600 border-violet-200 dark:border-violet-800")}
                        onClick={() => setSidePanel(sidePanel === "explain" ? "none" : "explain")}>
                        <Lightbulb className="h-4 w-4" />
                        <span className="hidden sm:inline">{t("reader.aiExplain")}</span>
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setFocusMode(!focusMode)} className={cn("gap-2", focusMode && "bg-primary/10 text-primary border-primary/20")}>
                        <Sparkles className="h-4 w-4" />
                        <span className="hidden sm:inline">{focusMode ? t("reader.showOriginal") : t("reader.focusMode")}</span>
                    </Button>
                    <Button variant="outline" size="sm" className="gap-2 text-violet-600 dark:text-violet-400 border-violet-200 dark:border-violet-800 hover:bg-violet-50 dark:hover:bg-violet-950/40"
                        onClick={async () => {
                            try { await api.post(`/api/knowledge/extract/${taskId}`); toast.success(t("reader.extractionStarted")); }
                            catch { toast.error(t("reader.extractionFailed")); }
                        }}>
                        <Brain className="h-4 w-4" />
                        <span className="hidden sm:inline">{t("reader.extractKnowledge")}</span>
                    </Button>
                    <Button size="sm" onClick={handleDownload} className="gap-2">
                        <Download className="h-4 w-4" />
                        <span className="hidden sm:inline">{t("reader.downloadPdf")}</span>
                    </Button>
                </div>
            </div>

            {/* Main content area */}
            <div className="flex min-h-0 flex-1 gap-4">
                {/* PDF panels */}
                <div className={cn("min-h-0 flex-1 rounded-xl border bg-card shadow-sm overflow-hidden", sidePanelOpen && !isMobile && "flex-[3]")}>
                    <ResizablePanelGroup direction={isMobile ? "vertical" : "horizontal"} className="h-full" style={{ direction: "ltr" }}>
                        <ResizablePanel defaultSize={focusMode ? 100 : 50} minSize={30}>
                            <div className="flex h-full flex-col bg-card">
                                <div className="flex items-center justify-between border-b bg-card px-4 py-2">
                                    <div className="flex items-center gap-2">
                                        <Sparkles className="h-3 w-3 text-primary" />
                                        <span className="text-xs font-medium text-primary uppercase tracking-wider">{t("reader.aiResult")}</span>
                                    </div>
                                </div>
                                <div className="flex-1 bg-muted/50">
                                    {resultPdfUrl && <iframe src={resultPdfUrl} className="h-full w-full border-none" title="Simplified PDF" />}
                                </div>
                            </div>
                        </ResizablePanel>
                        {!focusMode && (
                            <>
                                <ResizableHandle withHandle />
                                <ResizablePanel defaultSize={50} minSize={30}>
                                    <div className="flex h-full flex-col">
                                        <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-2">
                                            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{t("reader.originalSource")}</span>
                                        </div>
                                        <div className="flex-1 bg-muted/50">
                                            {originalPdfUrl && <iframe src={originalPdfUrl} className="h-full w-full border-none" title="Original PDF" />}
                                        </div>
                                    </div>
                                </ResizablePanel>
                            </>
                        )}
                    </ResizablePanelGroup>
                </div>

                {/* Side panel: Annotations or AI Explain */}
                {sidePanelOpen && (
                    <div className="flex w-80 min-w-[280px] flex-col rounded-xl border bg-card shadow-sm overflow-hidden">
                        {/* Panel header */}
                        <div className="flex items-center justify-between border-b px-4 py-3">
                            <div className="flex items-center gap-2">
                                {sidePanel === "annotations" ? <MessageSquare className="h-4 w-4 text-amber-500" /> : <Lightbulb className="h-4 w-4 text-violet-500" />}
                                <span className="text-sm font-medium">{sidePanel === "annotations" ? t("reader.annotations") : t("reader.aiExplain")}</span>
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => setSidePanel("none")}><X className="h-4 w-4" /></Button>
                        </div>

                        {/* Annotations panel */}
                        {sidePanel === "annotations" && (
                            <div className="flex flex-1 flex-col overflow-hidden">
                                {/* New annotation input */}
                                <div className="border-b p-3 space-y-2">
                                    <div className="flex gap-1">
                                        {(["note", "highlight", "question"] as const).map((tp) => (
                                            <Button key={tp} variant={noteType === tp ? "default" : "ghost"} size="sm" className="text-xs h-7 px-2"
                                                onClick={() => setNoteType(tp)}>
                                                {t(`reader.${tp}`)}
                                            </Button>
                                        ))}
                                    </div>
                                    <div className="flex gap-1.5">
                                        {COLORS.map((c) => (
                                            <button key={c.key} onClick={() => setNoteColor(c.key)}
                                                className={cn("h-5 w-5 rounded-full border-2 transition-transform", c.dot, noteColor === c.key ? "scale-125 border-foreground" : "border-transparent")} />
                                        ))}
                                    </div>
                                    <div className="flex gap-2">
                                        <textarea value={newNote} onChange={(e) => setNewNote(e.target.value)}
                                            placeholder={t("reader.addAnnotation")}
                                            className="flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm min-h-[60px] focus:outline-none focus:ring-1 focus:ring-primary"
                                            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAddAnnotation(); }} />
                                    </div>
                                    <Button size="sm" className="w-full" disabled={!newNote.trim() || !paperId} onClick={handleAddAnnotation}>
                                        {t("paperDetail.add")}
                                    </Button>
                                </div>
                                {/* Annotation list */}
                                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                                    {!paperId && <p className="text-xs text-muted-foreground text-center py-4">{t("reader.noAnnotations")}</p>}
                                    {paperId && annotations.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">{t("reader.noAnnotations")}</p>}
                                    {annotations.map((ann) => {
                                        const color = COLORS.find((c) => c.key === ann.color) || COLORS[0];
                                        return (
                                            <div key={ann.id} className={cn("rounded-lg border p-3 text-sm", color.bg, color.border)}>
                                                <div className="flex items-start justify-between gap-2">
                                                    <div className="flex-1">
                                                        <span className="text-[10px] uppercase font-medium text-muted-foreground">{ann.type}</span>
                                                        <p className="mt-1 whitespace-pre-wrap">{ann.content}</p>
                                                    </div>
                                                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0 shrink-0 text-muted-foreground hover:text-destructive"
                                                        onClick={() => handleDeleteAnnotation(ann.id)}>
                                                        <Trash2 className="h-3 w-3" />
                                                    </Button>
                                                </div>
                                                {ann.created_at && (
                                                    <p className="mt-1 text-[10px] text-muted-foreground">{new Date(ann.created_at).toLocaleString()}</p>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* AI Explain panel */}
                        {sidePanel === "explain" && (
                            <div className="flex flex-1 flex-col overflow-hidden p-3 space-y-3">
                                <p className="text-xs text-muted-foreground">{t("reader.aiExplainPlaceholder")}</p>
                                <textarea value={explainText} onChange={(e) => setExplainText(e.target.value)}
                                    placeholder={t("reader.aiExplainPlaceholder")}
                                    className="resize-none rounded-md border bg-background px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:ring-1 focus:ring-primary" />
                                <Button size="sm" disabled={!explainText.trim() || explaining} onClick={handleExplain} className="gap-2">
                                    {explaining ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                                    {explaining ? t("reader.explaining") : t("reader.aiExplain")}
                                </Button>
                                {explanation && (
                                    <div className="rounded-lg border bg-violet-50 dark:bg-violet-950/30 border-violet-200 dark:border-violet-800 p-3 text-sm whitespace-pre-wrap">
                                        {explanation}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Reader;
