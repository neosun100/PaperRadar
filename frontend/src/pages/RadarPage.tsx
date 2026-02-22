import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Radar, Loader2, Play, Clock, ExternalLink, TrendingUp, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

const RadarPage = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [status, setStatus] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [scanning, setScanning] = useState(false);
    const [selectedPaper, setSelectedPaper] = useState<number | null>(null);
    const [trending, setTrending] = useState<any>(null);
    const [trendingDays, setTrendingDays] = useState(7);
    const [trendingLoading, setTrendingLoading] = useState(false);

    const fetchStatus = useCallback(async () => {
        try { const r = await api.get("/api/radar/status"); setStatus(r.data); }
        catch { /* ignore */ }
        finally { setLoading(false); }
    }, []);

    const fetchTrending = useCallback(async (days: number) => {
        setTrendingLoading(true);
        try { const r = await api.get(`/api/radar/trending?days=${days}`); setTrending(r.data); }
        catch { /* ignore */ }
        finally { setTrendingLoading(false); }
    }, []);

    useEffect(() => { fetchStatus(); const id = setInterval(fetchStatus, 5000); return () => clearInterval(id); }, [fetchStatus]);
    useEffect(() => { fetchTrending(trendingDays); }, [fetchTrending, trendingDays]);

    const handleScan = async () => {
        setScanning(true);
        try {
            const r = await api.post("/api/radar/scan");
            toast.success(`Scan complete: ${r.data.found} papers found`);
            fetchStatus();
        } catch (e: any) { toast.error(e.response?.data?.detail || "Scan failed"); }
        finally { setScanning(false); }
    };

    if (loading) return <div className="flex h-[calc(100vh-8rem)] items-center justify-center"><Loader2 className="h-12 w-12 animate-spin text-primary" /></div>;

    const PaperCard = ({ p, i, showDate }: { p: any; i: number; showDate?: boolean }) => (
        <Card className="group hover:shadow-md transition-all cursor-pointer" onClick={() => setSelectedPaper(selectedPaper === i ? null : i)}>
            <CardContent className="p-4">
                <div className="flex items-start gap-3">
                    <div className="shrink-0 text-center">
                        <span className="text-amber-500 font-bold text-sm">⬆{p.upvotes || 0}</span>
                        {p.score && <p className={cn("text-[10px] font-mono mt-0.5 rounded px-1",
                            p.score >= 0.9 ? "text-emerald-600" : "text-blue-600"
                        )}>{Math.round(p.score * 100)}%</p>}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium leading-tight line-clamp-2">{p.title}</p>
                        <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground flex-wrap">
                            <span>{p.authors?.slice(0, 2).join(", ")}</span>
                            {p.source && <span className="bg-muted px-1.5 py-0.5 rounded">{p.source}</span>}
                            {showDate && p.date && <span className="bg-muted px-1.5 py-0.5 rounded">{p.date}</span>}
                            {p.pdf_url && (
                                <a href={p.pdf_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 hover:text-primary" onClick={(e) => e.stopPropagation()}>
                                    PDF <ExternalLink className="h-2.5 w-2.5" />
                                </a>
                            )}
                            {!p.task_id && !p.status && p.pdf_url && (
                                <button onClick={async (e) => {
                                    e.stopPropagation();
                                    try { await api.post("/api/upload-url", { url: p.arxiv_id, mode: "translate", highlight: true }); toast.success("Processing started"); }
                                    catch { toast.error("Failed"); }
                                }} className="inline-flex items-center gap-0.5 hover:text-primary font-medium text-emerald-600">Process →</button>
                            )}
                        </div>
                        {selectedPaper === i && p.abstract && (
                            <p className="text-xs text-muted-foreground mt-2 leading-relaxed border-t pt-2 animate-in fade-in duration-200">{p.abstract}</p>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-500/5 via-teal-500/10 to-transparent p-8 md:p-12 border border-teal-500/10 shadow-sm">
                <div className="relative z-10 mx-auto max-w-2xl text-center space-y-4">
                    <div className="flex justify-center">
                        <div className={cn("relative flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500", status?.running && "animate-pulse")}>
                            <Radar className={cn("h-8 w-8 text-white", status?.running && "animate-spin")} />
                            {status?.running && <span className="absolute inset-0 rounded-full border-2 border-emerald-400 animate-ping" />}
                        </div>
                    </div>
                    <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">{t("radar.title")}</h1>
                    <p className="text-lg text-muted-foreground">
                        {status?.enabled ? (status?.running ? t("radar.scanning") : t("radar.idle")) : "Radar disabled"}
                    </p>
                    <div className="flex justify-center gap-3 pt-2">
                        <Button variant="outline" onClick={() => navigate("/dashboard")}><ArrowLeft className="mr-2 h-4 w-4" />Dashboard</Button>
                        <Button onClick={handleScan} disabled={scanning || status?.running} className="gap-2">
                            {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                            {t("radar.scanNow")}
                        </Button>
                    </div>
                </div>
            </section>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-5">
                <Card><CardContent className="p-4 text-center">
                    <p className="text-3xl font-bold text-emerald-600">{status?.scan_count || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("radar.scans")}</p>
                </CardContent></Card>
                <Card><CardContent className="p-4 text-center">
                    <p className="text-3xl font-bold text-blue-600">{status?.papers_found || 0}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("radar.found")}</p>
                </CardContent></Card>
                <Card><CardContent className="p-4 text-center">
                    <p className="text-sm font-medium">{status?.categories?.join(", ") || "-"}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("radar.categories")}</p>
                </CardContent></Card>
                <Card><CardContent className="p-4 text-center">
                    <p className="text-sm font-medium">{status?.last_scan ? new Date(status.last_scan).toLocaleString() : "-"}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("radar.lastScan")}</p>
                </CardContent></Card>
                <Card><CardContent className="p-4 text-center">
                    <p className="text-sm font-medium">{status?.next_scan ? new Date(status.next_scan).toLocaleTimeString() : "-"}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("radar.nextScan")}</p>
                </CardContent></Card>
            </div>

            {/* Tabs: Discoveries + Trending */}
            <Tabs defaultValue="discoveries" className="space-y-4">
                <TabsList className="grid w-full grid-cols-2 lg:w-auto lg:inline-grid">
                    <TabsTrigger value="discoveries" className="gap-1.5"><Zap className="h-3.5 w-3.5" />{t("radar.recentDiscoveries")}</TabsTrigger>
                    <TabsTrigger value="trending" className="gap-1.5"><TrendingUp className="h-3.5 w-3.5" />Trending</TabsTrigger>
                </TabsList>

                <TabsContent value="discoveries" className="space-y-3">
                    {status?.recent_papers?.length > 0 ? (
                        <div className="grid gap-3 md:grid-cols-2">
                            {status.recent_papers.slice().reverse().map((p: any, i: number) => (
                                <PaperCard key={i} p={p} i={i} />
                            ))}
                        </div>
                    ) : (
                        <div className="py-12 text-center text-muted-foreground bg-muted/50 rounded-xl border border-dashed">
                            <Radar className="h-12 w-12 mx-auto mb-3 text-muted-foreground/50" />
                            <p>{t("radar.noDiscoveries")}</p>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="trending" className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        {[7, 14, 30].map(d => (
                            <Button key={d} variant={trendingDays === d ? "default" : "outline"} size="sm"
                                onClick={() => setTrendingDays(d)}>{d}d</Button>
                        ))}
                        {trendingLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                        {trending && <span className="text-xs text-muted-foreground ml-2">{trending.total} papers</span>}
                    </div>
                    {trending?.papers?.length > 0 ? (
                        <div className="grid gap-3 md:grid-cols-2">
                            {trending.papers.map((p: any, i: number) => (
                                <PaperCard key={i} p={p} i={i + 1000} showDate />
                            ))}
                        </div>
                    ) : (
                        <div className="py-8 text-center text-muted-foreground">No trending data</div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default RadarPage;
