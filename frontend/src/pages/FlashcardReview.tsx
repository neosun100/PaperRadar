import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, RotateCcw, CheckCircle, Brain, GraduationCap } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";
import { biText } from "@/lib/biText";

interface FlashcardData {
    id: string;
    paper_id: string;
    front: any;
    back: any;
    tags: string[];
    difficulty: number;
    srs: { interval_days: number; ease_factor: number; repetitions: number; next_review: string | null };
}

const FlashcardReview = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const [cards, setCards] = useState<FlashcardData[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [loading, setLoading] = useState(true);
    const [reviewed, setReviewed] = useState(0);
    const [sessionDone, setSessionDone] = useState(false);
    // Force re-render on language change
    const [, setLang] = useState(i18n.language);
    useEffect(() => {
        const cb = (lng: string) => setLang(lng);
        i18n.on("languageChanged", cb);
        return () => { i18n.off("languageChanged", cb); };
    }, [i18n]);

    const QUALITY_OPTIONS = [
        { value: 0, label: t("flashcard.forgot"), color: "bg-red-500 hover:bg-red-600" },
        { value: 1, label: t("flashcard.hard"), color: "bg-orange-500 hover:bg-orange-600" },
        { value: 3, label: t("flashcard.good"), color: "bg-blue-500 hover:bg-blue-600" },
        { value: 4, label: t("flashcard.easy"), color: "bg-green-500 hover:bg-green-600" },
        { value: 5, label: t("flashcard.perfect"), color: "bg-emerald-500 hover:bg-emerald-600" },
    ];

    const fetchDueCards = useCallback(async () => {
        try {
            const response = await api.get("/api/knowledge/flashcards/due?limit=20");
            setCards(response.data);
            if (response.data.length === 0) setSessionDone(true);
        } catch { toast.error(t("flashcard.loadFailed")); }
        finally { setLoading(false); }
    }, [t]);

    useEffect(() => { fetchDueCards(); }, [fetchDueCards]);

    const handleReview = async (quality: number) => {
        const card = cards[currentIndex];
        if (!card) return;
        try {
            await api.post(`/api/knowledge/flashcards/${card.id}/review`, null, { params: { quality } });
            setReviewed((prev) => prev + 1);
            setFlipped(false);
            if (currentIndex + 1 < cards.length) setCurrentIndex((prev) => prev + 1);
            else setSessionDone(true);
        } catch { toast.error(t("flashcard.reviewFailed")); }
    };

    if (loading) return <div className="flex h-[calc(100vh-8rem)] items-center justify-center"><Brain className="h-12 w-12 animate-pulse text-primary" /></div>;

    if (sessionDone) {
        return (
            <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center space-y-6">
                <div className="rounded-full bg-green-100 dark:bg-green-950/40 p-6"><CheckCircle className="h-12 w-12 text-green-600" /></div>
                <div className="text-center space-y-2">
                    <h2 className="text-2xl font-bold">{t("flashcard.sessionComplete")}</h2>
                    <p className="text-muted-foreground">{reviewed > 0 ? t("flashcard.reviewedCards", { count: reviewed }) : t("flashcard.noCardsDue")}</p>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" onClick={() => navigate("/knowledge")}><ArrowLeft className="mr-2 h-4 w-4" />{t("flashcard.knowledgeBase")}</Button>
                    <Button onClick={() => { setSessionDone(false); setCurrentIndex(0); setReviewed(0); setLoading(true); fetchDueCards(); }}>
                        <RotateCcw className="mr-2 h-4 w-4" />{t("flashcard.newSession")}
                    </Button>
                </div>
            </div>
        );
    }

    const currentCard = cards[currentIndex];
    if (!currentCard) return null;

    return (
        <div className="mx-auto max-w-2xl space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={() => navigate("/knowledge")}><ArrowLeft className="mr-2 h-4 w-4" />{t("flashcard.knowledgeBase")}</Button>
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <GraduationCap className="h-4 w-4" />
                    <span>{currentIndex + 1} / {cards.length}</span>
                    <span className="text-green-600">({reviewed} {t("flashcard.reviewed")})</span>
                </div>
            </div>

            <div className="h-1.5 rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${((currentIndex + 1) / cards.length) * 100}%` }} />
            </div>

            <div className="perspective-1000">
                <Card className={cn("min-h-[300px] cursor-pointer transition-all duration-300", flipped ? "bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border-green-200 dark:border-green-800" : "bg-card")} onClick={() => setFlipped(!flipped)}>
                    <CardContent className="flex min-h-[300px] flex-col items-center justify-center p-8 text-center">
                        {!flipped ? (
                            <>
                                <div className="mb-4 rounded-full bg-primary/10 p-3"><Brain className="h-6 w-6 text-primary" /></div>
                                <p className="text-lg font-medium leading-relaxed">{biText(currentCard.front)}</p>
                                <p className="mt-6 text-xs text-muted-foreground">{t("flashcard.clickToReveal")}</p>
                            </>
                        ) : (
                            <>
                                <div className="mb-4 rounded-full bg-green-100 dark:bg-green-950/40 p-3"><CheckCircle className="h-6 w-6 text-green-600" /></div>
                                <p className="text-lg leading-relaxed">{biText(currentCard.back)}</p>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>

            {currentCard.tags.length > 0 && (
                <div className="flex justify-center gap-1.5">
                    {currentCard.tags.map((tag) => <span key={tag} className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">{tag}</span>)}
                </div>
            )}

            {flipped && (
                <div className="space-y-3 animate-in slide-in-from-bottom-4 duration-300">
                    <p className="text-center text-sm text-muted-foreground">{t("flashcard.howWellRecall")}</p>
                    <div className="flex justify-center gap-2">
                        {QUALITY_OPTIONS.map((opt) => (
                            <Button key={opt.value} className={cn("flex-1 max-w-[120px] text-white", opt.color)} onClick={() => handleReview(opt.value)}>
                                <div className="text-center"><div className="text-sm font-medium">{opt.label}</div></div>
                            </Button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default FlashcardReview;
