import { useState, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Loader2, Search, Brain, Send, Sparkles, FileText, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

const DeepResearch = () => {
    const { t } = useTranslation();
    const [topic, setTopic] = useState("");
    const [researching, setResearching] = useState(false);
    const [result, setResult] = useState<any>(null);
    // Expert chat
    const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const [chatSources, setChatSources] = useState<any[]>([]);
    // History
    const [history, setHistory] = useState<{ topic: string; date: string; papers: number }[]>(() => {
        try { return JSON.parse(localStorage.getItem("pr_research_history") || "[]"); } catch { return []; }
    });
    const chatEndRef = useRef<HTMLDivElement>(null);

    const handleResearch = async () => {
        if (!topic.trim()) return;
        setResearching(true);
        setResult(null);
        setChatHistory([]);
        try {
            const r = await api.post("/api/knowledge/deep-research", { topic: topic.trim(), max_papers: 10 });
            setResult(r.data);
            if (r.data.synthesis) {
                setChatHistory([{ role: "assistant", content: `## Deep Research: ${topic}\n\n${r.data.synthesis}` }]);
            }
            // Save to history
            const entry = { topic: topic.trim(), date: new Date().toISOString(), papers: r.data.papers_found || 0 };
            const newHistory = [entry, ...history.filter(h => h.topic !== entry.topic)].slice(0, 20);
            setHistory(newHistory);
            localStorage.setItem("pr_research_history", JSON.stringify(newHistory));
        } catch (e: any) {
            toast.error(e.response?.data?.detail || "Research failed");
        } finally {
            setResearching(false);
        }
    };

    const handleChat = useCallback(async () => {
        if (!chatInput.trim()) return;
        const msg = chatInput.trim();
        setChatInput("");
        setChatHistory(prev => [...prev, { role: "user", content: msg }]);
        setChatLoading(true);
        try {
            const r = await api.post("/api/knowledge/expert-chat", {
                message: msg, topic: topic || "", history: chatHistory.slice(-6),
            });
            setChatHistory(prev => [...prev, { role: "assistant", content: r.data.reply }]);
            setChatSources(r.data.sources || []);
            setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
        } catch { toast.error("Chat failed"); }
        finally { setChatLoading(false); }
    }, [chatInput, topic, chatHistory]);

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Hero */}
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-amber-500/5 via-orange-500/10 to-transparent p-8 md:p-12 border border-orange-500/10 shadow-sm">
                <div className="relative z-10 mx-auto max-w-2xl text-center space-y-4">
                    <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">🔬 Deep Research</h1>
                    <p className="text-lg text-muted-foreground">Enter a topic. AI searches the latest papers, reads them all, and gives you expert-level analysis.</p>
                    <div className="flex gap-2 max-w-lg mx-auto">
                        <Input value={topic} onChange={e => setTopic(e.target.value)} placeholder="e.g. LLM reasoning, RLHF alternatives, efficient inference..."
                            className="h-12 text-base" onKeyDown={e => { if (e.key === "Enter") handleResearch(); }} />
                        <Button onClick={handleResearch} disabled={researching || !topic.trim()} className="h-12 px-6 gap-2">
                            {researching ? <Loader2 className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
                            {researching ? "Researching..." : "Research"}
                        </Button>
                    </div>
                    {researching && (
                        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Searching Semantic Scholar → Gathering knowledge → Synthesizing expert analysis...
                        </div>
                    )}
                </div>
            </section>

            {/* Results: Papers Found */}
            {!result && history.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    <span className="text-xs text-muted-foreground self-center">Recent:</span>
                    {history.slice(0, 8).map((h, i) => (
                        <button key={i} onClick={() => { setTopic(h.topic); }} className="inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1 text-xs hover:bg-muted transition-colors">
                            {h.topic} <span className="text-muted-foreground">({h.papers})</span>
                        </button>
                    ))}
                </div>
            )}

            {result && (
                <div className="grid gap-4 md:grid-cols-3">
                    <Card><CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold">{result.papers_found}</p>
                        <p className="text-xs text-muted-foreground">Papers Found</p>
                    </CardContent></Card>
                    <Card><CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-emerald-600">{result.papers_in_kb}</p>
                        <p className="text-xs text-muted-foreground">Already in KB</p>
                    </CardContent></Card>
                    <Card><CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-blue-600">{result.papers_queued}</p>
                        <p className="text-xs text-muted-foreground">Queued for Processing</p>
                    </CardContent></Card>
                </div>
            )}

            {/* Expert Chat */}
            {chatHistory.length > 0 && (
                <Card>
                    <CardContent className="p-4 space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-medium flex items-center gap-2"><Brain className="h-4 w-4" /> Expert Chat — {topic}</h3>
                            {result?.synthesis && (
                                <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={() => { navigator.clipboard.writeText(result.synthesis); toast.success("Copied!"); }}>
                                    <Copy className="h-3 w-3" /> Copy Report
                                </Button>
                            )}
                        </div>
                        <div className="max-h-[600px] overflow-y-auto space-y-4 pr-2">
                            {chatHistory.map((msg, i) => (
                                <div key={i} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
                                    <div className={cn("rounded-xl px-4 py-3 max-w-[90%] text-sm whitespace-pre-wrap",
                                        msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted")}>
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                            {chatLoading && <div className="flex justify-start"><div className="bg-muted rounded-xl px-4 py-3 text-sm flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Analyzing papers...</div></div>}
                            <div ref={chatEndRef} />
                        </div>

                        {/* Sources */}
                        {chatSources.length > 0 && (
                            <div className="border-t pt-3">
                                <p className="text-xs font-medium text-muted-foreground mb-2">Sources ({chatSources.length})</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {chatSources.slice(0, 10).map((s, i) => (
                                        <span key={i} className="inline-flex items-center rounded border bg-muted/50 px-2 py-0.5 text-[10px]">
                                            [{s.index}] {s.type} · {(s.score * 100).toFixed(0)}%
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-2">
                            <Input value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Ask a follow-up question as an expert..."
                                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleChat(); } }} />
                            <Button onClick={handleChat} disabled={chatLoading || !chatInput.trim()} size="icon" className="shrink-0">
                                <Send className="h-4 w-4" />
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Paper List */}
            {result?.papers && result.papers.length > 0 && (
                <Card>
                    <CardContent className="p-4">
                        <h3 className="text-sm font-medium mb-3 flex items-center gap-2"><FileText className="h-4 w-4" /> Papers Analyzed ({result.papers.length})</h3>
                        <div className="space-y-2">
                            {result.papers.map((p: any, i: number) => (
                                <div key={i} className="flex items-start gap-3 text-sm py-1.5 border-b last:border-0">
                                    <span className="text-xs text-muted-foreground shrink-0 w-6">{i + 1}.</span>
                                    <div className="min-w-0 flex-1">
                                        <p className="font-medium leading-tight">{p.title}</p>
                                        <p className="text-xs text-muted-foreground">{p.year || "?"} · {p.citations} cites{p.arxiv_id ? ` · arXiv:${p.arxiv_id}` : ""}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
};

export default DeepResearch;
