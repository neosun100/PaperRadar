import { useState, useEffect, useRef, useCallback } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Radar, Brain, Moon, Sun, Settings, Github, Star, Globe, Menu, X, Home, Search, Loader2 } from "lucide-react";
import LLMSettings from "@/components/LLMSettings";
import { useTheme } from "@/lib/useTheme";
import { cn } from "@/lib/utils";
import api from "@/lib/api";

const GITHUB_URL = "https://github.com/neosun100/PaperRadar";

const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { t, i18n } = useTranslation();
    const [dark, setDark] = useTheme();
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    // Cmd+K search
    const [searchOpen, setSearchOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [searching, setSearching] = useState(false);
    const searchRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                setSearchOpen(prev => !prev);
            }
            if (e.key === "Escape") setSearchOpen(false);
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, []);

    useEffect(() => {
        if (searchOpen && searchRef.current) searchRef.current.focus();
    }, [searchOpen]);

    const doSearch = useCallback(async (q: string) => {
        if (!q.trim()) { setSearchResults([]); return; }
        setSearching(true);
        try {
            const r = await api.get(`/api/knowledge/search?q=${encodeURIComponent(q)}&n=8`);
            setSearchResults(r.data.results || []);
        } catch { setSearchResults([]); }
        finally { setSearching(false); }
    }, []);

    const toggleLang = () => i18n.changeLanguage(i18n.language === "zh" ? "en" : "zh");

    const highlightMatch = (text: string, query: string): string => {
        if (!query.trim()) return text;
        const words = query.trim().split(/\s+/).filter(w => w.length > 1);
        if (!words.length) return text;
        const escaped = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
        const regex = new RegExp(`(${escaped.join("|")})`, "gi");
        return text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800/60 rounded px-0.5">$1</mark>');
    };

    const navTo = (path: string) => { navigate(path); setMobileMenuOpen(false); };

    const isActive = (path: string) => location.pathname.startsWith(path);

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 font-sans text-gray-900 dark:text-gray-100 transition-colors">
            <header className="sticky top-0 z-50 w-full border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md">
                <div className="container mx-auto flex h-14 sm:h-16 items-center justify-between px-4">
                    <div className="flex items-center gap-2 cursor-pointer" onClick={() => navTo("/dashboard")}>
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
                            <Radar className="h-5 w-5" />
                        </div>
                        <span className="text-lg font-semibold tracking-tight hidden xs:inline">PaperRadar</span>
                    </div>

                    {/* Desktop nav */}
                    <div className="hidden sm:flex items-center gap-1">
                        <Button variant="ghost" size="sm" className={cn("gap-2", isActive("/dashboard") && "text-blue-600 dark:text-blue-400")} onClick={() => navTo("/dashboard")}>
                            <Home className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" className={cn("gap-2", isActive("/knowledge") && "text-blue-600 dark:text-blue-400")} onClick={() => navTo("/knowledge")}>
                            <Brain className="h-4 w-4" />{t("nav.knowledgeBase")}
                        </Button>
                        <Button variant="ghost" size="sm" className={cn("gap-2", isActive("/radar") && "text-emerald-600 dark:text-emerald-400")} onClick={() => navTo("/radar")}>
                            <Radar className="h-4 w-4" />{t("radar.title")}
                        </Button>
                        <Button variant="ghost" size="sm" className={cn("gap-2", isActive("/research") && "text-amber-600 dark:text-amber-400")} onClick={() => navTo("/research")}>
                            <Search className="h-4 w-4" />Research
                        </Button>
                        <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-muted-foreground hover:text-yellow-500 transition-colors">
                            <Github className="h-4 w-4" /><Star className="h-3.5 w-3.5" /><span className="text-xs">{t("nav.star")}</span>
                        </a>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={toggleLang} title={i18n.language === "zh" ? "English" : "中文"}><Globe className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setDark(!dark)}>{dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</Button>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setSettingsOpen(true)}><Settings className="h-4 w-4" /></Button>
                    </div>

                    {/* Mobile: compact actions + hamburger */}
                    <div className="flex sm:hidden items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setSettingsOpen(true)}><Settings className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
                            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                        </Button>
                    </div>
                </div>

                {/* Mobile dropdown menu */}
                {mobileMenuOpen && (
                    <div className="sm:hidden border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3 space-y-1">
                        <button onClick={() => navTo("/dashboard")} className={cn("flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm", isActive("/dashboard") ? "bg-blue-50 dark:bg-blue-950/40 text-blue-600" : "text-muted-foreground")}>
                            <Home className="h-4 w-4" /> Dashboard
                        </button>
                        <button onClick={() => navTo("/knowledge")} className={cn("flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm", isActive("/knowledge") ? "bg-blue-50 dark:bg-blue-950/40 text-blue-600" : "text-muted-foreground")}>
                            <Brain className="h-4 w-4" /> {t("nav.knowledgeBase")}
                        </button>
                        <button onClick={() => navTo("/radar")} className={cn("flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm", isActive("/radar") ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600" : "text-muted-foreground")}>
                            <Radar className="h-4 w-4" /> {t("radar.title")}
                        </button>
                        <button onClick={() => navTo("/research")} className={cn("flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm", isActive("/research") ? "bg-amber-50 dark:bg-amber-950/40 text-amber-600" : "text-muted-foreground")}>
                            <Search className="h-4 w-4" /> Research
                        </button>
                        <div className="flex items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                            <Button variant="ghost" size="sm" onClick={toggleLang} className="gap-2"><Globe className="h-4 w-4" />{i18n.language === "zh" ? "English" : "中文"}</Button>
                            <Button variant="ghost" size="sm" onClick={() => setDark(!dark)} className="gap-2">{dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}{dark ? "Light" : "Dark"}</Button>
                            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground">
                                <Github className="h-4 w-4" /><Star className="h-3.5 w-3.5" />
                            </a>
                        </div>
                    </div>
                )}
            </header>

            <main className="container mx-auto py-4 sm:py-6 px-3 sm:px-4">
                <Outlet />
            </main>

            <LLMSettings open={settingsOpen} onOpenChange={setSettingsOpen} />

            {/* Cmd+K Search Overlay */}
            {searchOpen && (
                <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" onClick={() => setSearchOpen(false)}>
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
                    <div className="relative w-full max-w-lg rounded-xl border bg-card shadow-2xl" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-3 border-b px-4 py-3">
                            <Search className="h-5 w-5 text-muted-foreground shrink-0" />
                            <Input ref={searchRef} value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); doSearch(e.target.value); }}
                                placeholder="Search knowledge base... (⌘K)" className="border-0 shadow-none focus-visible:ring-0 text-base h-auto p-0" />
                            {searching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground shrink-0" />}
                            <kbd className="hidden sm:inline-flex h-5 items-center rounded border bg-muted px-1.5 text-[10px] text-muted-foreground">ESC</kbd>
                        </div>
                        {searchResults.length > 0 && (
                            <div className="max-h-[300px] overflow-y-auto p-2 space-y-1">
                                {searchResults.map((r, i) => (
                                    <button key={i} className="w-full text-left rounded-lg px-3 py-2 text-sm hover:bg-muted transition-colors"
                                        onClick={() => {
                                            if (r.metadata?.paper_id) { navigate(`/knowledge/paper/${r.metadata.paper_id}`); setSearchOpen(false); }
                                        }}>
                                        <p className="line-clamp-2 text-foreground" dangerouslySetInnerHTML={{ __html: highlightMatch(r.text, searchQuery) }} />
                                        <span className="text-[10px] text-muted-foreground">{r.metadata?.type} · {(r.score * 100).toFixed(0)}%</span>
                                    </button>
                                ))}
                            </div>
                        )}
                        {searchQuery && !searching && searchResults.length === 0 && (
                            <div className="p-6 text-center text-sm text-muted-foreground">No results found</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Layout;
