import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Download, Brain, Lightbulb, Link2, FlaskConical, Database, GraduationCap, StickyNote, Plus, Loader2, MessageCircle, Send, Headphones, Play, Pause, RotateCcw } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";
import { biText } from "@/lib/biText";

interface PaperKnowledge {
    id: string;
    metadata: { title: any; authors: { name: string; affiliation?: string }[]; year?: number; doi?: string; venue?: string; abstract?: any; keywords?: any[] };
    entities: { id: string; name: any; type: string; definition?: any; importance: number }[];
    relationships: { id: string; source_entity_id: string; target_entity_id: string; type: string; description?: any; source?: string; target?: string }[];
    findings: { id: string; type: string; statement: any; evidence?: any }[];
    methods: { name: any; description: any }[];
    datasets: { name: any; description: any; usage?: any }[];
    flashcards: { id: string; front: any; back: any; tags: string[]; difficulty: number }[];
    annotations: { id: string; type: string; content: string; created_at?: string }[];
    structure?: { sections: { id: string; title: any; level: number; summary?: any }[] };
}

const TYPE_COLORS: Record<string, string> = {
    method: "bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300",
    model: "bg-purple-100 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300",
    dataset: "bg-green-100 dark:bg-green-950/40 text-green-700 dark:text-green-300",
    metric: "bg-amber-100 text-amber-700",
    concept: "bg-muted text-muted-foreground",
    task: "bg-rose-100 text-rose-700",
    person: "bg-cyan-100 text-cyan-700",
    organization: "bg-orange-100 text-orange-700",
};

const PaperDetail = () => {
    const { t, i18n } = useTranslation();
    const { paperId } = useParams<{ paperId: string }>();
    const navigate = useNavigate();
    const [paper, setPaper] = useState<PaperKnowledge | null>(null);
    const [loading, setLoading] = useState(true);
    const [newNote, setNewNote] = useState("");
    const [chatInput, setChatInput] = useState("");
    const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
    const [chatLoading, setChatLoading] = useState(false);
    const [audioStatus, setAudioStatus] = useState<"idle" | "generating" | "ready">("idle");
    const [audioUrl, setAudioUrl] = useState<string | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [audioRef] = useState(() => new Audio());
    // Force re-render on language change
    const [, setLang] = useState(i18n.language);
    useEffect(() => {
        const cb = (lng: string) => setLang(lng);
        i18n.on("languageChanged", cb);
        return () => { i18n.off("languageChanged", cb); };
    }, [i18n]);

    useEffect(() => {
        const fetchPaper = async () => {
            try { const response = await api.get(`/api/knowledge/papers/${paperId}`); setPaper(response.data); }
            catch { toast.error(t("paperDetail.loadFailed")); }
            finally { setLoading(false); }
        };
        fetchPaper();
    }, [paperId, t]);

    // Check audio status on mount
    useEffect(() => {
        api.get(`/api/knowledge/papers/${paperId}/audio/status`).then(r => {
            if (r.data.status === "ready") { setAudioStatus("ready"); setAudioUrl(r.data.url); }
        }).catch(() => {});
        return () => { audioRef.pause(); };
    }, [paperId, audioRef]);

    const handleGenerateAudio = async () => {
        setAudioStatus("generating");
        try {
            const r = await api.post(`/api/knowledge/papers/${paperId}/audio`);
            if (r.data.status === "ready") { setAudioStatus("ready"); setAudioUrl(r.data.url); return; }
            // Poll for completion
            const poll = setInterval(async () => {
                try {
                    const s = await api.get(`/api/knowledge/papers/${paperId}/audio/status`);
                    if (s.data.status === "ready") { clearInterval(poll); setAudioStatus("ready"); setAudioUrl(s.data.url); }
                } catch { /* keep polling */ }
            }, 3000);
            setTimeout(() => clearInterval(poll), 120000); // stop after 2min
        } catch { toast.error(t("paperDetail.audioFailed")); setAudioStatus("idle"); }
    };

    const togglePlayback = () => {
        if (!audioUrl) return;
        if (isPlaying) { audioRef.pause(); setIsPlaying(false); }
        else {
            audioRef.src = audioUrl;
            audioRef.onended = () => setIsPlaying(false);
            audioRef.play(); setIsPlaying(true);
        }
    };

    const handleRegenerateAudio = async () => {
        audioRef.pause(); setIsPlaying(false);
        await api.delete(`/api/knowledge/papers/${paperId}/audio`).catch(() => {});
        setAudioStatus("idle"); setAudioUrl(null);
        handleGenerateAudio();
    };

    const handleExport = async () => {
        try {
            const response = await api.get(`/api/knowledge/export/paper/${paperId}`, { responseType: "blob" });
            const blob = new Blob([response.data], { type: "application/json" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `${biText(paper?.metadata.title) || "paper"}.epaper.json`;
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            toast.success(t("paperDetail.exportedEpaper"));
        } catch { toast.error(t("paperDetail.exportFailed")); }
    };

    const handleAddNote = async () => {
        if (!newNote.trim()) return;
        try {
            await api.post(`/api/knowledge/papers/${paperId}/annotations`, null, { params: { type: "note", content: newNote } });
            setNewNote("");
            const response = await api.get(`/api/knowledge/papers/${paperId}`);
            setPaper(response.data);
            toast.success(t("paperDetail.noteAdded"));
        } catch { toast.error(t("paperDetail.noteAddFailed")); }
    };

    const handleChat = async () => {
        if (!chatInput.trim()) return;
        const msg = chatInput.trim();
        setChatInput("");
        setChatHistory(prev => [...prev, { role: "user", content: msg }]);
        setChatLoading(true);
        try {
            const resp = await api.post(`/api/knowledge/papers/${paperId}/chat`, { message: msg, history: chatHistory });
            setChatHistory(prev => [...prev, { role: "assistant", content: resp.data.reply }]);
        } catch { toast.error("Chat failed"); }
        finally { setChatLoading(false); }
    };

    if (loading) return <div className="flex h-[calc(100vh-8rem)] items-center justify-center"><Loader2 className="h-12 w-12 animate-spin text-primary" /></div>;

    if (!paper) return (
        <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center space-y-4">
            <p className="text-muted-foreground">{t("paperDetail.paperNotFound")}</p>
            <Button onClick={() => navigate("/knowledge")}>{t("paperDetail.knowledgeBase")}</Button>
        </div>
    );

    const { metadata, entities, relationships, findings, methods, datasets, flashcards, annotations } = paper;
    const entityMap: Record<string, string> = {};
    entities.forEach((e) => { entityMap[e.id] = biText(e.name); });

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-start justify-between gap-4">
                <div className="space-y-2">
                    <Button variant="ghost" size="sm" onClick={() => navigate("/knowledge")}><ArrowLeft className="mr-2 h-4 w-4" />{t("paperDetail.knowledgeBase")}</Button>
                    <h1 className="text-2xl font-bold tracking-tight">{biText(metadata.title)}</h1>
                    <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                        <span>{metadata.authors?.map((a) => a.name).join(", ")}</span>
                        {metadata.year && <span>({metadata.year})</span>}
                        {metadata.venue && <span>- {metadata.venue}</span>}
                    </div>
                    {metadata.keywords && metadata.keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                            {metadata.keywords.map((kw, i) => <span key={i} className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">{biText(kw)}</span>)}
                        </div>
                    )}
                </div>
                <Button variant="outline" size="sm" className="gap-2 shrink-0" onClick={handleExport}><Download className="h-4 w-4" />.epaper.json</Button>
            </div>

            {metadata.abstract && (
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">{t("paperDetail.abstract")}</CardTitle></CardHeader>
                    <CardContent><p className="text-sm leading-relaxed">{biText(metadata.abstract)}</p></CardContent>
                </Card>
            )}

            <Tabs defaultValue="chat" className="space-y-4">
                <TabsList className="grid w-full grid-cols-7 lg:w-auto lg:inline-grid">
                    <TabsTrigger value="chat" className="gap-1.5"><MessageCircle className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("paperDetail.chat")}</span></TabsTrigger>
                    <TabsTrigger value="audio" className="gap-1.5"><Headphones className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("paperDetail.audio")}</span></TabsTrigger>
                    <TabsTrigger value="entities" className="gap-1.5"><Brain className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("paperDetail.entities")} ({entities.length})</span><span className="sm:hidden">{entities.length}</span></TabsTrigger>
                    <TabsTrigger value="findings" className="gap-1.5"><Lightbulb className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("paperDetail.findings")} ({findings.length})</span><span className="sm:hidden">{findings.length}</span></TabsTrigger>
                    <TabsTrigger value="relations" className="gap-1.5"><Link2 className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("paperDetail.relations")} ({relationships.length})</span><span className="sm:hidden">{relationships.length}</span></TabsTrigger>
                    <TabsTrigger value="flashcards" className="gap-1.5"><GraduationCap className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("paperDetail.cards")} ({flashcards.length})</span><span className="sm:hidden">{flashcards.length}</span></TabsTrigger>
                    <TabsTrigger value="notes" className="gap-1.5"><StickyNote className="h-3.5 w-3.5" /><span className="hidden sm:inline">{t("paperDetail.notes")}</span></TabsTrigger>
                </TabsList>

                {/* Chat Tab */}
                <TabsContent value="chat" className="space-y-3">
                    <Card><CardContent className="p-4 space-y-3">
                        <div className="max-h-[400px] overflow-y-auto space-y-3">
                            {chatHistory.map((msg, i) => (
                                <div key={i} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
                                    <div className={cn("rounded-xl px-4 py-2 max-w-[80%] text-sm whitespace-pre-wrap",
                                        msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted")}>
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                            {chatLoading && <div className="flex justify-start"><div className="bg-muted rounded-xl px-4 py-2 text-sm"><Loader2 className="h-4 w-4 animate-spin" /></div></div>}
                        </div>
                        <div className="flex gap-2">
                            <Input placeholder={t("paperDetail.chatPlaceholder")} value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleChat(); } }} />
                            <Button size="sm" onClick={handleChat} disabled={chatLoading || !chatInput.trim()} className="shrink-0">
                                <Send className="h-4 w-4" />
                            </Button>
                        </div>
                    </CardContent></Card>
                </TabsContent>

                {/* Audio Summary Tab */}
                <TabsContent value="audio" className="space-y-3">
                    <Card><CardContent className="p-6 flex flex-col items-center gap-4">
                        {audioStatus === "idle" && (
                            <>
                                <Headphones className="h-12 w-12 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground text-center">{t("paperDetail.audioDesc")}</p>
                                <Button onClick={handleGenerateAudio} className="gap-2"><Headphones className="h-4 w-4" />{t("paperDetail.generateAudio")}</Button>
                            </>
                        )}
                        {audioStatus === "generating" && (
                            <>
                                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                                <p className="text-sm text-muted-foreground">{t("paperDetail.audioGenerating")}</p>
                            </>
                        )}
                        {audioStatus === "ready" && (
                            <>
                                <div className="flex items-center gap-3">
                                    <Button size="lg" variant={isPlaying ? "secondary" : "default"} onClick={togglePlayback} className="gap-2 rounded-full h-14 w-14 p-0">
                                        {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6 ml-0.5" />}
                                    </Button>
                                </div>
                                <p className="text-sm font-medium">{t("paperDetail.audioReady")}</p>
                                <Button variant="ghost" size="sm" onClick={handleRegenerateAudio} className="gap-1.5 text-muted-foreground">
                                    <RotateCcw className="h-3.5 w-3.5" />{t("paperDetail.regenerateAudio")}
                                </Button>
                            </>
                        )}
                    </CardContent></Card>
                </TabsContent>

                <TabsContent value="entities" className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-2">
                        {entities.map((ent) => (
                            <Card key={ent.id} className="border-border"><CardContent className="p-4">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium text-sm">{biText(ent.name)}</span>
                                            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", TYPE_COLORS[ent.type] || "bg-muted text-muted-foreground")}>{ent.type}</span>
                                        </div>
                                        {ent.definition && <p className="text-xs text-muted-foreground leading-relaxed">{biText(ent.definition)}</p>}
                                    </div>
                                    <div className="text-xs text-muted-foreground shrink-0">{Math.round(ent.importance * 100)}%</div>
                                </div>
                            </CardContent></Card>
                        ))}
                    </div>
                </TabsContent>

                <TabsContent value="findings" className="space-y-3">
                    {findings.map((f) => (
                        <Card key={f.id} className="border-border"><CardContent className="p-4">
                            <div className="flex items-start gap-3">
                                <div className={cn("shrink-0 mt-0.5 rounded-full px-2 py-0.5 text-[10px] font-medium",
                                    f.type === "result" ? "bg-green-100 dark:bg-green-950/40 text-green-700 dark:text-green-300" :
                                    f.type === "limitation" ? "bg-amber-100 text-amber-700" : "bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300"
                                )}>{f.type}</div>
                                <div className="space-y-1">
                                    <p className="text-sm">{biText(f.statement)}</p>
                                    {f.evidence && <p className="text-xs text-muted-foreground">{t("paperDetail.evidence")}: {biText(f.evidence)}</p>}
                                </div>
                            </div>
                        </CardContent></Card>
                    ))}
                    {methods.length > 0 && (
                        <div className="space-y-3 pt-4">
                            <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2"><FlaskConical className="h-4 w-4" /> {t("paperDetail.methodsSection")}</h3>
                            {methods.map((m, i) => <Card key={i} className="border-border"><CardContent className="p-4"><p className="text-sm font-medium">{biText(m.name)}</p><p className="text-xs text-muted-foreground mt-1">{biText(m.description)}</p></CardContent></Card>)}
                        </div>
                    )}
                    {datasets.length > 0 && (
                        <div className="space-y-3 pt-4">
                            <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2"><Database className="h-4 w-4" /> {t("paperDetail.datasetsSection")}</h3>
                            {datasets.map((d, i) => <Card key={i} className="border-border"><CardContent className="p-4"><p className="text-sm font-medium">{biText(d.name)}</p><p className="text-xs text-muted-foreground mt-1">{biText(d.description)}</p>{d.usage && <p className="text-xs text-muted-foreground">{t("paperDetail.usage")}: {biText(d.usage)}</p>}</CardContent></Card>)}
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="flashcards" className="space-y-3">
                    {flashcards.map((fc) => (
                        <Card key={fc.id} className="border-border"><CardContent className="p-4 space-y-2">
                            <p className="text-sm font-medium">Q: {biText(fc.front)}</p>
                            <p className="text-sm text-muted-foreground">A: {biText(fc.back)}</p>
                            <div className="flex items-center gap-2">
                                {fc.tags.map((tag) => <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">{tag}</span>)}
                                <span className="text-[10px] text-muted-foreground ml-auto">{t("paperDetail.difficulty")}: {fc.difficulty}/5</span>
                            </div>
                        </CardContent></Card>
                    ))}
                </TabsContent>

                <TabsContent value="relations" className="space-y-3">
                    {relationships.map((rel) => (
                        <Card key={rel.id} className="border-border"><CardContent className="p-4">
                            <div className="flex items-center gap-2 text-sm">
                                <span className="font-medium">{entityMap[rel.source_entity_id] || rel.source || "?"}</span>
                                <span className="rounded-full bg-primary/10 text-primary px-2.5 py-0.5 text-xs font-medium">{rel.type}</span>
                                <span className="font-medium">{entityMap[rel.target_entity_id] || rel.target || "?"}</span>
                            </div>
                            {rel.description && <p className="text-xs text-muted-foreground mt-1">{biText(rel.description)}</p>}
                        </CardContent></Card>
                    ))}
                </TabsContent>

                <TabsContent value="notes" className="space-y-3">
                    <div className="flex gap-2">
                        <Input placeholder={t("paperDetail.addNote")} value={newNote} onChange={(e) => setNewNote(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAddNote()} />
                        <Button size="sm" onClick={handleAddNote} className="gap-1 shrink-0"><Plus className="h-4 w-4" />{t("paperDetail.add")}</Button>
                    </div>
                    {annotations?.map((ann) => (
                        <Card key={ann.id} className="border-border"><CardContent className="p-4">
                            <p className="text-sm">{ann.content}</p>
                            {ann.created_at && <p className="text-xs text-muted-foreground mt-1">{new Date(ann.created_at).toLocaleString()}</p>}
                        </CardContent></Card>
                    ))}
                    {(!annotations || annotations.length === 0) && !newNote && <p className="text-sm text-muted-foreground text-center py-8">{t("paperDetail.noNotes")}</p>}
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default PaperDetail;
