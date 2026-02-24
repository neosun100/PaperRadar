import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
    Brain, Search, Download, Trash2, BookOpen, Network, FileJson, FileText as FileTextIcon, GraduationCap, Loader2, CheckCircle, AlertCircle, Clock, Sparkles, MessageCircle, GitCompareArrows, FolderPlus, Folder, PenTool, Copy, X, Plus, Map,
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
    summary: string;
    tldr: string;
    created_at: string | null;
}

interface Collection {
    id: string;
    name: string;
    description: string;
    color: string;
    paper_ids: string[];
    paper_count: number;
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
    const [selectedForCompare, setSelectedForCompare] = useState<Set<string>>(new Set());
    const [comparison, setComparison] = useState<string | null>(null);
    const [compareLoading, setCompareLoading] = useState(false);
    // Extraction table
    const [extractTable, setExtractTable] = useState<{ columns: string[]; rows: any[] } | null>(null);
    const [extractLoading, setExtractLoading] = useState(false);
    const [searchResults, setSearchResults] = useState<any[] | null>(null);
    const [searching, setSearching] = useState(false);
    // Collections
    const [collections, setCollections] = useState<Collection[]>([]);
    const [activeCollection, setActiveCollection] = useState<string | null>(null);
    const [showNewCollection, setShowNewCollection] = useState(false);
    const [newColName, setNewColName] = useState("");
    // Writing Assistant
    const [showWriting, setShowWriting] = useState(false);
    const [writingTopic, setWritingTopic] = useState("");
    const [writingStyle, setWritingStyle] = useState("ieee");
    const [writingResult, setWritingResult] = useState("");
    const [writingLoading, setWritingLoading] = useState(false);
    // Zotero Import
    const [showZotero, setShowZotero] = useState(false);
    const [zoteroKey, setZoteroKey] = useState("");
    const [zoteroLibId, setZoteroLibId] = useState("");
    const [zoteroImporting, setZoteroImporting] = useState(false);
    const [sortBy, setSortBy] = useState<"date" | "year" | "title">("date");
    const navigate = useNavigate();

    const fetchPapers = useCallback(async () => {
        try { const response = await api.get("/api/knowledge/papers"); setPapers(response.data); } catch { /* silently fail */ }
    }, []);

    const fetchDueCount = useCallback(async () => {
        try { const response = await api.get("/api/knowledge/flashcards/due?limit=100"); setDueCount(response.data.length); } catch { /* silently fail */ }
    }, []);

    useEffect(() => { fetchPapers(); fetchDueCount(); fetchCollections(); }, [fetchPapers, fetchDueCount]);

    const fetchCollections = async () => {
        try { const r = await api.get("/api/knowledge/collections"); setCollections(r.data); } catch {}
    };

    const handleCreateCollection = async () => {
        if (!newColName.trim()) return;
        try {
            await api.post("/api/knowledge/collections", { name: newColName.trim() });
            toast.success(t("knowledge.collectionCreated"));
            setNewColName(""); setShowNewCollection(false);
            fetchCollections();
        } catch {}
    };

    const handleDeleteCollection = async (colId: string) => {
        try { await api.delete(`/api/knowledge/collections/${colId}`); toast.success(t("knowledge.collectionDeleted")); fetchCollections(); if (activeCollection === colId) setActiveCollection(null); } catch {}
    };

    const handleAddToCollection = async (colId: string, paperId: string) => {
        try { await api.post(`/api/knowledge/collections/${colId}/papers`, { paper_id: paperId }); toast.success(t("knowledge.paperAdded")); fetchCollections(); } catch {}
    };

    const handleRemoveFromCollection = async (colId: string, paperId: string) => {
        try { await api.delete(`/api/knowledge/collections/${colId}/papers/${paperId}`); fetchCollections(); } catch {}
    };

    const handleGenerateRelatedWork = async () => {
        const ids = selectedForCompare.size > 0 ? Array.from(selectedForCompare) : (activeCollection ? collections.find(c => c.id === activeCollection)?.paper_ids || [] : papers.filter(p => p.extraction_status === "completed").map(p => p.id));
        if (ids.length < 2) return;
        setWritingLoading(true);
        try {
            const r = await api.post("/api/knowledge/writing/related-work", { paper_ids: ids, topic: writingTopic, style: writingStyle });
            setWritingResult(r.data.related_work);
            toast.success(t("knowledge.relatedWorkGenerated"));
        } catch { toast.error(t("knowledge.relatedWorkFailed")); }
        finally { setWritingLoading(false); }
    };

    const handleCrossChat = async () => {
        if (!chatInput.trim()) return;
        const msg = chatInput.trim();
        setChatInput("");
        setChatHistory(prev => [...prev, { role: "user", content: msg }]);
        setChatLoading(true);
        try {
            const resp = await api.post("/api/knowledge/expert-chat", { message: msg, history: chatHistory, topic: "" });
            let reply = resp.data.reply;
            const sources = resp.data.sources || [];
            if (sources.length > 0) {
                reply += `\n\n📚 Sources: ${sources.slice(0, 5).map((s: any) => `[${s.index}] ${s.type}`).join(", ")}`;
            }
            setChatHistory(prev => [...prev, { role: "assistant", content: reply }]);
        } catch { toast.error("Chat failed"); }
        finally { setChatLoading(false); }
    };

    const handleCompare = async () => {
        if (selectedForCompare.size < 2) return;
        setCompareLoading(true);
        try {
            const resp = await api.post("/api/knowledge/compare", { paper_ids: Array.from(selectedForCompare) });
            setComparison(resp.data.comparison);
        } catch (e: any) { toast.error(e.response?.data?.detail || "Compare failed"); }
        finally { setCompareLoading(false); }
    };

    const handleExtractTable = async () => {
        const ids = selectedForCompare.size > 0 ? Array.from(selectedForCompare) : (activeCollection ? collections.find(c => c.id === activeCollection)?.paper_ids || [] : papers.filter(p => p.extraction_status === "completed").map(p => p.id));
        if (ids.length < 2) return;
        setExtractLoading(true);
        try {
            const r = await api.post("/api/knowledge/extract-table", { paper_ids: ids });
            setExtractTable(r.data);
        } catch { toast.error("Failed to extract table"); }
        finally { setExtractLoading(false); }
    };

    const toggleCompare = (id: string) => {
        setSelectedForCompare(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else if (next.size < 5) next.add(id);
            return next;
        });
    };

    const handleSemanticSearch = async () => {
        if (!search.trim()) { setSearchResults(null); return; }
        setSearching(true);
        try {
            const r = await api.get(`/api/knowledge/search?q=${encodeURIComponent(search)}&n=10`);
            setSearchResults(r.data.results);
        } catch { setSearchResults(null); }
        finally { setSearching(false); }
    };

    const handleDelete = async (paperId: string) => {
        if (!window.confirm("Delete this paper from knowledge base?")) return;
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

    const activeColPaperIds = activeCollection ? (collections.find(c => c.id === activeCollection)?.paper_ids || []) : null;
    const filteredPapers = papers.filter(p => {
        if (activeColPaperIds && !activeColPaperIds.includes(p.id)) return false;
        if (search && !p.title.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });
    const sortedPapers = [...filteredPapers].sort((a, b) => {
        if (sortBy === "year") return (b.year || 0) - (a.year || 0);
        if (sortBy === "title") return (a.title || "").localeCompare(b.title || "");
        return (b.created_at || "").localeCompare(a.created_at || "");
    });

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
                        <Button variant="outline" className="gap-2" onClick={() => setShowWriting(!showWriting)}>
                            <PenTool className="h-4 w-4" /> {t("knowledge.writingAssistant")}
                        </Button>
                        <Button variant="outline" className="gap-2" onClick={() => setShowChat(!showChat)}>
                            <MessageCircle className="h-4 w-4" /> {t("knowledge.askAll")}
                        </Button>
                        <Button variant="outline" className="gap-2" onClick={() => navigate("/knowledge/graph")}>
                            <Network className="h-4 w-4" /> {t("knowledge.knowledgeGraph")}
                        </Button>
                        <Button variant="outline" className="gap-2" onClick={() => navigate("/knowledge/similarity")}>
                            <Map className="h-4 w-4" /> {t("knowledge.similarityMap")}
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
                        <Button variant="outline" className="gap-2" onClick={() => setShowZotero(!showZotero)}>
                            <BookOpen className="h-4 w-4" /> {t("knowledge.importZotero")}
                        </Button>
                    </div>
                </div>
                <div className="absolute top-0 left-0 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full bg-violet-200/30 dark:bg-violet-500/10 blur-3xl" />
                <div className="absolute bottom-0 right-0 translate-x-1/2 translate-y-1/2 h-64 w-64 rounded-full bg-purple-200/30 dark:bg-purple-500/10 blur-3xl" />
            </section>

            {/* Zotero Import */}
            {showZotero && (
                <Card><CardContent className="p-4 space-y-3">
                    <h3 className="font-semibold text-sm">{t("knowledge.importZotero")}</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <Input placeholder={t("knowledge.zoteroApiKey")} value={zoteroKey} onChange={(e) => setZoteroKey(e.target.value)} type="password" />
                        <Input placeholder={t("knowledge.zoteroLibraryId")} value={zoteroLibId} onChange={(e) => setZoteroLibId(e.target.value)} />
                        <Button disabled={zoteroImporting || !zoteroKey || !zoteroLibId} onClick={async () => {
                            setZoteroImporting(true);
                            try {
                                const r = await api.post("/api/knowledge/import/zotero", { api_key: zoteroKey, library_id: zoteroLibId });
                                toast.success(t("knowledge.zoteroImported", { count: r.data.imported }));
                                fetchPapers();
                            } catch { toast.error(t("knowledge.zoteroFailed")); }
                            finally { setZoteroImporting(false); }
                        }}>
                            {zoteroImporting ? <><Loader2 className="h-4 w-4 animate-spin mr-1" />{t("knowledge.zoteroImporting")}</> : t("knowledge.zoteroImport")}
                        </Button>
                    </div>
                </CardContent></Card>
            )}

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

            {/* Writing Assistant */}
            {showWriting && (
                <Card><CardContent className="p-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-medium flex items-center gap-2"><PenTool className="h-4 w-4" /> {t("knowledge.writingAssistant")}</h3>
                        <Button variant="ghost" size="sm" onClick={() => setShowWriting(false)}><X className="h-4 w-4" /></Button>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        <Input placeholder={t("knowledge.relatedWorkTopic")} value={writingTopic} onChange={(e) => setWritingTopic(e.target.value)} className="flex-1 min-w-[200px] h-9" />
                        <select value={writingStyle} onChange={(e) => setWritingStyle(e.target.value)} className="h-9 rounded-md border bg-background px-3 text-sm">
                            <option value="ieee">IEEE</option>
                            <option value="acm">ACM</option>
                            <option value="apa">APA</option>
                        </select>
                        <Button size="sm" onClick={handleGenerateRelatedWork} disabled={writingLoading} className="gap-1.5 h-9">
                            {writingLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PenTool className="h-3.5 w-3.5" />}
                            {writingLoading ? t("knowledge.generating") : t("knowledge.generateRelatedWork")}
                        </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                        {selectedForCompare.size > 0 ? `Using ${selectedForCompare.size} selected papers` : activeCollection ? `Using collection papers` : `Using all completed papers`}
                    </p>
                    {writingResult && (
                        <div className="space-y-2">
                            <div className="flex justify-end">
                                <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={() => { navigator.clipboard.writeText(writingResult); toast.success(t("knowledge.copied")); }}>
                                    <Copy className="h-3 w-3" /> {t("knowledge.copyToClipboard")}
                                </Button>
                            </div>
                            <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap rounded-lg border bg-muted/50 p-4 max-h-[400px] overflow-y-auto">{writingResult}</div>
                        </div>
                    )}
                </CardContent></Card>
            )}

            {/* Collections Bar */}
            {collections.length > 0 || showNewCollection ? (
                <div className="flex items-center gap-2 flex-wrap">
                    <Button variant={activeCollection === null ? "default" : "outline"} size="sm" className="gap-1.5 h-8" onClick={() => setActiveCollection(null)}>
                        <Folder className="h-3.5 w-3.5" /> {t("knowledge.allPapers")} ({papers.length})
                    </Button>
                    {collections.map(col => (
                        <div key={col.id} className="flex items-center gap-0.5">
                            <Button variant={activeCollection === col.id ? "default" : "outline"} size="sm" className="gap-1.5 h-8" onClick={() => setActiveCollection(activeCollection === col.id ? null : col.id)}>
                                <Folder className="h-3.5 w-3.5" /> {col.name} ({col.paper_count})
                            </Button>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive" onClick={() => handleDeleteCollection(col.id)}>
                                <Trash2 className="h-3 w-3" />
                            </Button>
                        </div>
                    ))}
                    {showNewCollection ? (
                        <div className="flex items-center gap-1.5">
                            <Input value={newColName} onChange={(e) => setNewColName(e.target.value)} placeholder={t("knowledge.collectionName")}
                                className="h-8 w-40 text-sm" onKeyDown={(e) => { if (e.key === "Enter") handleCreateCollection(); }} autoFocus />
                            <Button size="sm" className="h-8" onClick={handleCreateCollection} disabled={!newColName.trim()}>{t("knowledge.createCollection")}</Button>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => setShowNewCollection(false)}><X className="h-3.5 w-3.5" /></Button>
                        </div>
                    ) : (
                        <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-muted-foreground" onClick={() => setShowNewCollection(true)}>
                            <FolderPlus className="h-3.5 w-3.5" /> {t("knowledge.newCollection")}
                        </Button>
                    )}
                </div>
            ) : (
                <div className="flex justify-start">
                    <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground" onClick={() => setShowNewCollection(true)}>
                        <FolderPlus className="h-3.5 w-3.5" /> {t("knowledge.newCollection")}
                    </Button>
                </div>
            )}

            {/* Comparison Result */}
            {comparison && (
                <Card><CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold flex items-center gap-2"><GitCompareArrows className="h-5 w-5" /> Paper Comparison</h2>
                        <Button variant="ghost" size="sm" onClick={() => setComparison(null)}>✕</Button>
                    </div>
                    <div className="prose dark:prose-invert max-w-none text-sm whitespace-pre-wrap">{comparison}</div>
                </CardContent></Card>
            )}

            {/* Extraction Table */}
            {extractTable && extractTable.rows && extractTable.rows.length > 0 && (
                <Card><CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold flex items-center gap-2"><FileTextIcon className="h-5 w-5" /> Data Extraction Table</h2>
                        <div className="flex gap-2">
                            <Button variant="ghost" size="sm" onClick={() => {
                                const header = (extractTable.columns || []).join("\t");
                                const rows = (extractTable.rows || []).map((r: any) => [r.paper, ...(extractTable.columns || []).map((c: string) => r[c] || "-")].join("\t"));
                                navigator.clipboard.writeText([header, ...rows].join("\n"));
                                toast.success(t("knowledge.copied"));
                            }}><Copy className="h-3.5 w-3.5 mr-1" /> TSV</Button>
                            <Button variant="ghost" size="sm" onClick={() => setExtractTable(null)}>✕</Button>
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm border-collapse">
                            <thead>
                                <tr className="border-b">
                                    <th className="text-left p-2 font-medium text-muted-foreground">Paper</th>
                                    {(extractTable.columns || []).map((col: string) => (
                                        <th key={col} className="text-left p-2 font-medium text-muted-foreground capitalize">{col}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {(extractTable.rows || []).map((row: any, i: number) => (
                                    <tr key={i} className="border-b last:border-0 hover:bg-muted/50">
                                        <td className="p-2 font-medium max-w-[200px]">{row.paper}</td>
                                        {(extractTable.columns || []).map((col: string) => (
                                            <td key={col} className="p-2 text-muted-foreground max-w-[250px]">{row[col] || "-"}</td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent></Card>
            )}

            <section className="space-y-4">
                <div className="flex items-center justify-between gap-4 px-2">
                    <div className="flex items-center gap-3 shrink-0">
                        <h2 className="text-2xl font-semibold tracking-tight">{t("knowledge.papers")}</h2>
                        {selectedForCompare.size >= 2 && (
                            <Button size="sm" onClick={handleCompare} disabled={compareLoading} className="gap-1.5">
                                {compareLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <GitCompareArrows className="h-3.5 w-3.5" />}
                                Compare ({selectedForCompare.size})
                            </Button>
                        )}
                        {selectedForCompare.size >= 2 && (
                            <Button size="sm" variant="outline" onClick={handleExtractTable} disabled={extractLoading} className="gap-1.5">
                                {extractLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileTextIcon className="h-3.5 w-3.5" />}
                                Extract Table
                            </Button>
                        )}
                    </div>
                    {papers.length > 0 && (
                        <div className="relative max-w-sm w-full flex gap-1.5">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input placeholder={t("knowledge.searchPapers")} value={search}
                                    onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setSearchResults(null); }}
                                    onKeyDown={(e) => { if (e.key === "Enter") handleSemanticSearch(); }}
                                    className="pl-9 h-9" />
                            </div>
                            {search && (
                                <Button size="sm" variant="outline" onClick={handleSemanticSearch} disabled={searching} className="h-9 shrink-0">
                                    {searching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "AI"}
                                </Button>
                            )}
                            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="h-9 rounded-md border bg-background px-2 text-xs">
                                <option value="date">Newest</option>
                                <option value="year">Year</option>
                                <option value="title">Title</option>
                            </select>
                        </div>
                    )}
                </div>

                {/* Semantic Search Results */}
                {searchResults && searchResults.length > 0 && (
                    <div className="space-y-2 mb-4">
                        <p className="text-xs text-muted-foreground px-1">AI semantic search: {searchResults.length} results</p>
                        <div className="grid gap-2 md:grid-cols-2">
                            {searchResults.map((r, i) => (
                                <div key={i} className="flex items-start gap-2 rounded-lg border bg-card p-3 text-sm">
                                    <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-mono",
                                        r.score >= 0.5 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" :
                                        r.score >= 0.3 ? "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300" :
                                        "bg-muted text-muted-foreground"
                                    )}>{(r.score * 100).toFixed(0)}%</span>
                                    <div className="min-w-0">
                                        <p className="text-xs leading-relaxed line-clamp-2">{r.text}</p>
                                        <span className="text-[10px] text-muted-foreground bg-muted px-1 py-0.5 rounded mt-1 inline-block">{r.metadata?.type}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {sortedPapers.map((paper) => (
                        <Card key={paper.id} className={cn("group relative overflow-hidden transition-all hover:shadow-md border-border",
                            paper.extraction_status === "completed" && "cursor-pointer",
                            selectedForCompare.has(paper.id) && "ring-2 ring-primary")}
                            onClick={() => {
                                if (paper.extraction_status === "completed") navigate(`/knowledge/paper/${paper.id}`);
                            }}>
                            {paper.extraction_status === "completed" && (
                                <button className={cn("absolute top-2 right-2 z-10 h-5 w-5 rounded border-2 flex items-center justify-center text-[10px] transition-colors",
                                    selectedForCompare.has(paper.id) ? "bg-primary border-primary text-primary-foreground" : "border-muted-foreground/30 hover:border-primary")}
                                    onClick={(e) => { e.stopPropagation(); toggleCompare(paper.id); }}>
                                    {selectedForCompare.has(paper.id) && "✓"}
                                </button>
                            )}
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
                                        {collections.length > 0 && paper.extraction_status === "completed" && (
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground"
                                                        onClick={(e) => e.stopPropagation()}>
                                                        <Plus className="h-3.5 w-3.5" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
                                                    {collections.map(col => {
                                                        const inCol = col.paper_ids.includes(paper.id);
                                                        return (
                                                            <DropdownMenuItem key={col.id} onClick={() => inCol ? handleRemoveFromCollection(col.id, paper.id) : handleAddToCollection(col.id, paper.id)}>
                                                                <Folder className="mr-2 h-3.5 w-3.5" />
                                                                {inCol ? `✓ ${col.name}` : col.name}
                                                            </DropdownMenuItem>
                                                        );
                                                    })}
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        )}
                                        <Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-red-600"
                                            onClick={(e) => { e.stopPropagation(); handleDelete(paper.id); }}>
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {paper.tldr && <p className="text-xs font-medium text-foreground/80 line-clamp-2 leading-relaxed mb-1">💡 {paper.tldr}</p>}
                                {!paper.tldr && paper.summary && <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">{paper.summary}</p>}
                                {paper.doi && <p className="text-[10px] text-muted-foreground/60 truncate mt-1">DOI: {paper.doi}</p>}
                            </CardContent>
                        </Card>
                    ))}

                    {sortedPapers.length === 0 && (
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
