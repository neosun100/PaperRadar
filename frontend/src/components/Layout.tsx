import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Radar, Brain, Moon, Sun, Settings, Github, Star, Globe } from "lucide-react";
import LLMSettings from "@/components/LLMSettings";
import { useTheme } from "@/lib/useTheme";

const GITHUB_URL = "https://github.com/neosun100/PaperRadar";

const Layout = () => {
    const navigate = useNavigate();
    const { t, i18n } = useTranslation();
    const [dark, setDark] = useTheme();
    const [settingsOpen, setSettingsOpen] = useState(false);

    const toggleLang = () => {
        i18n.changeLanguage(i18n.language === "zh" ? "en" : "zh");
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 font-sans text-gray-900 dark:text-gray-100 transition-colors">
            <header className="sticky top-0 z-50 w-full border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md">
                <div className="container mx-auto flex h-16 items-center justify-between px-4">
                    <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate("/dashboard")}>
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
                            <Radar className="h-5 w-5" />
                        </div>
                        <span className="text-lg font-semibold tracking-tight">PaperRadar</span>
                    </div>

                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-blue-600 dark:hover:text-blue-400" onClick={() => navigate("/knowledge")}>
                            <Brain className="h-4 w-4" />
                            <span className="hidden sm:inline">{t("nav.knowledgeBase")}</span>
                        </Button>
                        <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-emerald-600 dark:hover:text-emerald-400" onClick={() => navigate("/radar")}>
                            <Radar className="h-4 w-4" />
                            <span className="hidden sm:inline">{t("radar.title")}</span>
                        </Button>
                        <a
                            href={GITHUB_URL}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-muted-foreground hover:text-yellow-500 dark:hover:text-yellow-400 transition-colors"
                            title="Star us on GitHub!"
                        >
                            <Github className="h-4 w-4" />
                            <Star className="h-3.5 w-3.5" />
                            <span className="hidden sm:inline text-xs">{t("nav.star")}</span>
                        </a>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={toggleLang} aria-label={t("nav.language")} title={i18n.language === "zh" ? "English" : "中文"}>
                            <Globe className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setDark(!dark)} aria-label={t("nav.toggleDark")}>
                            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setSettingsOpen(true)} aria-label={t("nav.llmSettings")}>
                            <Settings className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </header>

            <main className="container mx-auto py-6 px-4">
                <Outlet />
            </main>

            <LLMSettings open={settingsOpen} onOpenChange={setSettingsOpen} />
        </div>
    );
};

export default Layout;
