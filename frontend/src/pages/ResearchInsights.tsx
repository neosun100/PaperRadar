import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Sparkles, Loader2, BookOpen, FlaskConical, Clock, AlertTriangle, Network, RefreshCw, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";
import { biText } from "@/lib/biText";

const ResearchInsights = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const [insights, setInsights] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [review, setReview] = useState<string | null>(null);
    const [reviewLoading, setReviewLoading] = useState(false);
    const [gaps, setGaps] = useState<string | null>(null);
    const [gapsLoading, setGapsLoading] = useState(false);
    // Paper Writer
    const [writerSection, setWriterSection] = useState("introduction");
    const [writerTopic, setWriterTopic] = useState("");
    const [writerResult, setWriterResult] = useState("");
    const [writerLoading, setWriterLoading] = useState(false);
    const [, setLang] = useState(i18n.language);
    useEffect(() => { const cb = (l: string) => setLang(l); i18n.on("languageChanged", cb); return () => { i18n.off("languageChanged", cb); }; }, [i18n]);

    const fetchInsights = useCallback(async () => {
        try { const r = await api.get("/api/knowledge/insights"); setInsights(r.data); }
        catch { /* ignore */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchInsights(); }, [fetchInsights]);

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const r = await api.post("/api/knowledge/insights/generate");
            setInsights(r.data);
        } catch (e: any) {
            toast.error(e.response?.data?.detail || t("insights.generateFailed"));
        } finally { setGenerating(false); }
    };

    if (loading) return <div className="flex h-[calc(100vh-8rem)] items-center justify-center"><Loader2 className="h-12 w-12 animate-spin text-primary" /></div>;

    const hasInsights = insights && insights.field_overview;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-500/5 via-teal-500/10 to-transparent p-8 md:p-12 border border-teal-500/10 shadow-sm">
                <div className="relative z-10 mx-auto max-w-2xl text-center space-y-4">
                    <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">{t("insights.title")}</h1>
                    <p className="text-lg text-muted-foreground">{t("insights.subtitle")}</p>
                    <div className="flex justify-center gap-3 pt-2">
                        <Button variant="outline" onClick={() => navigate("/knowledge")}><ArrowLeft className="mr-2 h-4 w-4" />{t("nav.knowledgeBase")}</Button>
                        <Button onClick={handleGenerate} disabled={generating} className="gap-2">
                            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : hasInsights ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                            {generating ? t("insights.generating") : hasInsights ? t("insights.regenerate") : t("insights.generate")}
                        </Button>
                        <Button variant="outline" onClick={async () => {
                            setReviewLoading(true);
                            try { const r = await api.post("/api/knowledge/review/generate", {}); setReview(r.data.review); }
                            catch (e: any) { toast.error(e.response?.data?.detail || "Failed"); }
                            finally { setReviewLoading(false); }
                        }} disabled={reviewLoading} className="gap-2">
                            {reviewLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                            {reviewLoading ? "Writing..." : "Literature Review"}
                        </Button>
                        <Button variant="outline" onClick={async () => {
                            setGapsLoading(true);
                            try { const r = await api.post("/api/knowledge/research-gaps", {}); setGaps(r.data.gaps); }
                            catch (e: any) { toast.error(e.response?.data?.detail || "Failed"); }
                            finally { setGapsLoading(false); }
                        }} disabled={gapsLoading} className="gap-2">
                            {gapsLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <AlertTriangle className="h-4 w-4" />}
                            {gapsLoading ? "Analyzing..." : "Research Gaps"}
                        </Button>
                    </div>
                    {insights?.paper_count && <p className="text-xs text-muted-foreground">{insights.paper_count} papers analyzed</p>}
                </div>
                <div className="absolute top-0 left-0 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full bg-emerald-200/30 dark:bg-emerald-500/10 blur-3xl" />
            </section>

            {/* Literature Review */}
            {review && (
                <Card><CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold flex items-center gap-2"><FileText className="h-5 w-5" /> Literature Review</h2>
                        <Button variant="ghost" size="sm" onClick={() => {
                            const blob = new Blob([review], { type: "text/markdown" });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url; a.download = "literature_review.md"; a.click();
                            URL.revokeObjectURL(url);
                        }}>Download .md</Button>
                    </div>
                    <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap">{review}</div>
                </CardContent></Card>
            )}

            {/* Research Gaps */}
            {gaps && (
                <Card><CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-500" /> Research Gaps Analysis</h2>
                        <Button variant="ghost" size="sm" onClick={() => {
                            const blob = new Blob([gaps], { type: "text/markdown" });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url; a.download = "research_gaps.md"; a.click();
                            URL.revokeObjectURL(url);
                        }}>Download .md</Button>
                    </div>
                    <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap">{gaps}</div>
                </CardContent></Card>
            )}

            {!hasInsights ? (
                <div className="py-16 text-center text-muted-foreground bg-muted/50 rounded-xl border border-dashed">
                    <Sparkles className="h-12 w-12 mx-auto mb-3 text-muted-foreground/50" />
                    <p>{t("insights.noInsights")}</p>
                </div>
            ) : (
                <Tabs defaultValue="overview" className="space-y-4">
                    <TabsList className="grid w-full grid-cols-5 lg:w-auto lg:inline-grid">
                        <TabsTrigger value="overview" className="gap-1.5"><BookOpen className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("insights.fieldOverview")}</span></TabsTrigger>
                        <TabsTrigger value="methods" className="gap-1.5"><FlaskConical className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("insights.methodComparison")}</span></TabsTrigger>
                        <TabsTrigger value="timeline" className="gap-1.5"><Clock className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("insights.timeline")}</span></TabsTrigger>
                        <TabsTrigger value="gaps" className="gap-1.5"><AlertTriangle className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("insights.researchGaps")}</span></TabsTrigger>
                        <TabsTrigger value="connections" className="gap-1.5"><Network className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("insights.paperConnections")}</span></TabsTrigger>
                    </TabsList>

                    {/* Field Overview */}
                    <TabsContent value="overview">
                        <Card><CardContent className="p-6 prose dark:prose-invert max-w-none">
                            <p className="text-sm leading-relaxed whitespace-pre-line">{biText(insights.field_overview)}</p>
                        </CardContent></Card>
                    </TabsContent>

                    {/* Method Comparison */}
                    <TabsContent value="methods" className="space-y-3">
                        <div className="overflow-x-auto rounded-xl border">
                            <table className="w-full text-sm">
                                <thead className="bg-muted/50">
                                    <tr>
                                        {[t("insights.paper"), t("insights.method"), t("insights.coreIdea"), t("insights.strengths"), t("insights.limitations"), t("insights.metrics")].map(h => (
                                            <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y">
                                    {(insights.method_comparison || []).map((m: any, i: number) => (
                                        <tr key={i} className="hover:bg-muted/30">
                                            <td className="px-4 py-3 font-medium max-w-[200px] truncate">{biText(m.paper_title)}</td>
                                            <td className="px-4 py-3">{biText(m.method_name)}</td>
                                            <td className="px-4 py-3 text-muted-foreground max-w-[250px]">{biText(m.core_idea)}</td>
                                            <td className="px-4 py-3 text-green-600 dark:text-green-400 max-w-[200px]">{biText(m.strengths)}</td>
                                            <td className="px-4 py-3 text-amber-600 dark:text-amber-400 max-w-[200px]">{biText(m.limitations)}</td>
                                            <td className="px-4 py-3 text-muted-foreground">{biText(m.metrics)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </TabsContent>

                    {/* Timeline */}
                    <TabsContent value="timeline" className="space-y-3">
                        <div className="relative pl-8 space-y-6">
                            <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-border" />
                            {(insights.timeline || []).map((item: any, i: number) => (
                                <div key={i} className="relative">
                                    <div className="absolute -left-5 top-1 h-4 w-4 rounded-full bg-primary border-2 border-background" />
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">{item.year || "?"}</span>
                                            <span className="font-medium text-sm">{biText(item.paper_title)}</span>
                                        </div>
                                        <p className="text-xs text-muted-foreground">{biText(item.contribution)}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </TabsContent>

                    {/* Research Gaps */}
                    <TabsContent value="gaps" className="space-y-3">
                        {(insights.research_gaps || []).map((g: any, i: number) => (
                            <Card key={i}><CardContent className="p-4 space-y-2">
                                <div className="flex items-start gap-2">
                                    <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                                    <div className="space-y-1">
                                        <p className="text-sm font-medium">{biText(g.gap)}</p>
                                        {g.evidence && <p className="text-xs text-muted-foreground">{t("insights.evidence")}: {biText(g.evidence)}</p>}
                                        {g.suggested_direction && (
                                            <p className="text-xs text-emerald-600 dark:text-emerald-400">→ {biText(g.suggested_direction)}</p>
                                        )}
                                    </div>
                                </div>
                            </CardContent></Card>
                        ))}
                    </TabsContent>

                    {/* Paper Connections */}
                    <TabsContent value="connections" className="space-y-3">
                        {(insights.paper_connections || []).map((c: any, i: number) => (
                            <Card key={i}><CardContent className="p-4">
                                <div className="flex items-center gap-2 text-sm flex-wrap">
                                    <span className="font-medium">{biText(c.source_paper)}</span>
                                    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium",
                                        c.relation_type === "extends" || c.relation_type === "improves" ? "bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300" :
                                        c.relation_type === "contradicts" ? "bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300" :
                                        "bg-muted text-muted-foreground"
                                    )}>{c.relation_type}</span>
                                    <span className="font-medium">{biText(c.target_paper)}</span>
                                </div>
                                {c.description && <p className="text-xs text-muted-foreground mt-1">{biText(c.description)}</p>}
                            </CardContent></Card>
                        ))}
                    </TabsContent>
                </Tabs>
            )}

            {/* AI Paper Writer */}
            <Card>
                <CardContent className="p-6 space-y-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">✍️ {t("paperDetail.paperWriter")}</h3>
                    <p className="text-sm text-muted-foreground">Generate paper sections from your knowledge base papers.</p>
                    <div className="flex flex-wrap gap-2">
                        <input value={writerTopic} onChange={e => setWriterTopic(e.target.value)} placeholder="Topic (optional)" className="h-9 flex-1 min-w-[200px] rounded-md border bg-background px-3 text-sm" />
                        <select value={writerSection} onChange={e => setWriterSection(e.target.value)} className="h-9 rounded-md border bg-background px-3 text-sm">
                            {["introduction", "methodology", "results", "discussion", "conclusion"].map(s => (
                                <option key={s} value={s}>{t(`paperDetail.${s}`)}</option>
                            ))}
                        </select>
                        <Button size="sm" className="h-9 gap-1.5" disabled={writerLoading} onClick={async () => {
                            setWriterLoading(true);
                            try {
                                const papers = await api.get("/api/knowledge/papers");
                                const ids = papers.data.filter((p: any) => p.extraction_status === "completed").map((p: any) => p.id).slice(0, 15);
                                const r = await api.post("/api/knowledge/writing/generate-section", { section: writerSection, paper_ids: ids, topic: writerTopic });
                                setWriterResult(r.data.content);
                            } catch { toast.error("Generation failed"); }
                            finally { setWriterLoading(false); }
                        }}>
                            {writerLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                            {t("paperDetail.generateSection")}
                        </Button>
                    </div>
                    {writerResult && (
                        <div className="space-y-2">
                            <div className="flex justify-end gap-2">
                                <Button variant="ghost" size="sm" className="text-xs" onClick={() => { navigator.clipboard.writeText(writerResult); toast.success("Copied!"); }}>Copy</Button>
                                <Button variant="ghost" size="sm" className="text-xs" onClick={() => {
                                    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([writerResult], { type: "text/markdown" }));
                                    a.download = `${writerSection}.md`; a.click();
                                }}>.md</Button>
                            </div>
                            <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap rounded-lg border bg-muted/50 p-4 max-h-[400px] overflow-y-auto">{writerResult}</div>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default ResearchInsights;
