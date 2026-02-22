import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Download, Loader2, FileText, Sparkles, Palette, Brain } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

interface HighlightStats {
    core_conclusions: number;
    method_innovations: number;
    key_data: number;
    total: number;
}

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

    useEffect(() => {
        const onResize = () => {
            const mobile = window.innerWidth < 768;
            setIsMobile(mobile);
            if (mobile) setFocusMode(true);
        };
        window.addEventListener("resize", onResize);
        return () => window.removeEventListener("resize", onResize);
    }, []);

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

    return (
        <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
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

            <ResizablePanelGroup direction={isMobile ? "vertical" : "horizontal"} className="min-h-0 flex-1 rounded-xl border bg-card shadow-sm overflow-hidden" style={{ direction: "ltr" }}>
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
    );
};

export default Reader;
