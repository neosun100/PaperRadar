import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
    Brain, Search, Download, Trash2, BookOpen, Network, FileJson, FileText as FileTextIcon, GraduationCap, Loader2, CheckCircle, AlertCircle, Clock, Sparkles, MessageCircle,
} from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

interface Paper {
    id: string;
    task_id: string | null;
    title: string;
    doi: string | null;
    year: number | null;
    venue: string | null;
    extraction_status: string;
    created_at: string | null;
}

const KnowledgeBase = () => {
    const { t } = useTranslation();
    const [papers, setPapers] = useState<Paper[]>([]);
    const [search, setSearch] = useState("");
    const [dueCount, setDueCount] = useState(0);
    const [showChat, setShowChat] = useState(false);
    const [chatInput, setChatInput] = useState("");
    const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
    const [chatLoading, setChatLoading] = useState(false);
    const navigate = useNavigate();

    const fetchPapers = useCallback(async () => {
        try { const response = await api.get("/api/knowledge/papers"); setPapers(response.data); } catch { /* silently fail */ }
    }, []);

    const fetchDueCount = useCallback(async () => {
        try { const response = await api.get("/api/knowledge/flashcards/due?limit=100"); setDueCount(response.data.length); } catch { /* silently fail */ }
    }, []);

    useEffect(() => { fetchPapers(); fetchDueCount(); }, [fetchPapers, fetchDueCount]);

    const handleCrossChat = async () => {
        if (!chatInput.trim()) return;
        const msg = chatInput.trim();
        setChatInput("");
        setChatHistory(prev => [...prev, { role: "user", content: msg }]);
        setChatLoading(true);
        try {
            const resp = await api.post("/api/knowledge/chat", { message: msg, history: chatHistory });
            setChatHistory(prev => [...prev, { role: "assistant", content: resp.data.reply }]);
        } catch { toast.error("Chat failed"); }
        finally { setChatLoading(false); }
    };

    const handleDelete = async (paperId: string) => {
        try { await api.delete(`/api/knowledge/papers/${paperId}`); setPapers((prev) => prev.filter((p) => p.id !== paperId)); toast.success(t("knowledge.paperDeleted")); }
        catch { toast.error(t("knowledge.paperDeleteFailed")); }
    };

    const handleExport = async (format: string) => {
        try {
            let url = "", filename = "";
            switch (format) {
                case "json": url = "/api/knowledge/export/json"; filename = "paperradar_knowledge.json"; break;
                case "bibtex": url = "/api/knowledge/export/bibtex"; filename = "paperradar_references.bib"; break;
                case "obsidian": url = "/api/knowledge/export/obsidian"; filename = "paperradar_vault.zip"; break;
                case "csv": url = "/api/knowledge/export/csv"; filename = "paperradar_csv.zip"; break;
                case "csl": url = "/api/knowledge/export/csl-json"; filename = "paperradar_references.json"; break;
                default: return;
            }
            const response = await api.get(url, { responseType: "blob" });
            const blob = new Blob([response.data]);
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            URL.revokeObjectURL(link.href);
            toast.success(t("knowledge.exportedAs", { format: format.toUpperCase() }));
        } catch { toast.error(t("knowledge.exportFailed")); }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "completed": return <CheckCircle className="h-4 w-4 text-green-600" />;
            case "extracting": return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
            case "error": return <AlertCircle className="h-4 w-4 text-red-600" />;
            default: return <Clock className="h-4 w-4 text-gray-400" />;
        }
    };

    const filteredPapers = search ? papers.filter((p) => p.title.toLowerCase().includes(search.toLowerCase())) : papers;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-violet-500/5 via-purple-500/10 to-transparent p-8 md:p-12 border border-purple-500/10 shadow-sm">
                <div className="relative z-10 mx-auto max-w-2xl text-center space-y-4">
                    <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">{t("knowledge.title")}</h1>
                    <p className="text-lg text-muted-foreground">{t("knowledge.subtitle")}</p>
                    {papers.length > 0 && (
                        <p className="text-sm text-muted-foreground">{papers.length} {t("knowledge.papers").toLowerCase()} · {papers.filter(p => p.extraction_status === "completed").length} {t("dashboard.completed").toLowerCase()}</p>
                    )}
                    <div className="flex flex-wrap justify-center gap-3 pt-2">
                        <Button variant="outline" className="gap-2" onClick={() => navigate("/knowledge/insights")}>
                            <Sparkles className="h-4 w-4" /> {t("insights.title")}
                        </Button>
                        <Button variant="outline" className="gap-2" onClick={() => setShowChat(!showChat)}>
                            <MessageCircle className="h-4 w-4" /> {t("knowledge.askAll")}
                        </Button>
                        <Button variant="outline" className="gap-2" onClick={() => navigate("/knowledge/graph")}>
                            <Network className="h-4 w-4" /> {t("knowledge.knowledgeGraph")}
                        </Button>
                        <Button variant="outline" className="gap-2 text-muted-foreground" onClick={() => navigate("/knowledge/review")}>
                            <GraduationCap className="h-4 w-4" /> {t("knowledge.reviewFlashcards")}
                            {dueCount > 0 && <span className="ml-1 inline-flex items-center justify-center rounded-full bg-red-500 px-2 py-0.5 text-xs font-medium text-white">{dueCount}</span>}
                        </Button>
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="outline" className="gap-2"><Download className="h-4 w-4" /> {t("knowledge.export")}</Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent>
                                <DropdownMenuItem onClick={() => handleExport("json")}><FileJson className="mr-2 h-4 w-4" />{t("knowledge.exportJson")}</DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleExport("obsidian")}><BookOpen className="mr-2 h-4 w-4" />{t("knowledge.exportObsidian")}</DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleExport("bibtex")}><FileTextIcon className="mr-2 h-4 w-4" />{t("knowledge.exportBibtex")}</DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleExport("csl")}><FileJson className="mr-2 h-4 w-4" />{t("knowledge.exportCsl")}</DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleExport("csv")}><FileTextIcon className="mr-2 h-4 w-4" />{t("knowledge.exportCsv")}</DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>
                <div className="absolute top-0 left-0 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full bg-violet-200/30 dark:bg-violet-500/10 blur-3xl" />
                <div className="absolute bottom-0 right-0 translate-x-1/2 translate-y-1/2 h-64 w-64 rounded-full bg-purple-200/30 dark:bg-purple-500/10 blur-3xl" />
            </section>

            {/* Cross-Paper Chat */}
            {showChat && (
                <Card><CardContent className="p-4 space-y-3">
                    <div className="max-h-[300px] overflow-y-auto space-y-3">
                        {chatHistory.map((msg, i) => (
                            <div key={i} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
                                <div className={cn("rounded-xl px-4 py-2 max-w-[80%] text-sm whitespace-pre-wrap",
                                    msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted")}>{msg.content}</div>
                            </div>
                        ))}
                        {chatLoading && <div className="flex justify-start"><div className="bg-muted rounded-xl px-4 py-2 text-sm"><Loader2 className="h-4 w-4 animate-spin" /></div></div>}
                    </div>
                    <div className="flex gap-2">
                        <Input placeholder={t("knowledge.chatPlaceholder")} value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleCrossChat(); } }} />
                        <Button size="sm" onClick={handleCrossChat} disabled={chatLoading || !chatInput.trim()} className="shrink-0">{t("knowledge.send")}</Button>
                    </div>
                </CardContent></Card>
            )}

            <section className="space-y-4">
                <div className="flex items-center justify-between gap-4 px-2">
                    <h2 className="text-2xl font-semibold tracking-tight shrink-0">{t("knowledge.papers")}</h2>
                    {papers.length > 0 && (
                        <div className="relative max-w-xs w-full">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input placeholder={t("knowledge.searchPapers")} value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 h-9" />
                        </div>
                    )}
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {filteredPapers.map((paper) => (
                        <Card key={paper.id} className={cn("group relative overflow-hidden transition-all hover:shadow-md border-border", paper.extraction_status === "completed" && "cursor-pointer")}
                            onClick={() => { if (paper.extraction_status === "completed") navigate(`/knowledge/paper/${paper.id}`); }}>
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-100 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400"><Brain className="h-5 w-5" /></div>
                                        <div className="space-y-1 min-w-0 flex-1">
                                            <CardTitle className="text-base font-medium leading-tight line-clamp-2">{paper.title || t("knowledge.untitled")}</CardTitle>
                                            <CardDescription className="text-xs flex items-center gap-1.5">
                                                {paper.year && <span>{paper.year}</span>}
                                                {paper.venue && <span>- {paper.venue}</span>}
                                            </CardDescription>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1.5 shrink-0">
                                        {getStatusIcon(paper.extraction_status)}
                                        <Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-red-600"
                                            onClick={(e) => { e.stopPropagation(); handleDelete(paper.id); }}>
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {paper.doi && <p className="text-xs text-muted-foreground truncate">DOI: {paper.doi}</p>}
                            </CardContent>
                        </Card>
                    ))}

                    {filteredPapers.length === 0 && (
                        <div className="col-span-full py-12 text-center text-muted-foreground bg-muted/50 rounded-xl border border-dashed">
                            <Brain className="h-12 w-12 mx-auto mb-3 text-muted-foreground/50" />
                            <p>{search ? t("knowledge.noPapersMatch") : t("knowledge.noPapers")}</p>
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
};

export default KnowledgeBase;
