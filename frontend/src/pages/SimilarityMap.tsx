import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, Loader2, Map } from "lucide-react";
import api from "@/lib/api";

interface MapPoint {
    paper_id: string;
    title: string;
    x: number;
    y: number;
}

const COLORS = ["#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"];

const SimilarityMap = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [points, setPoints] = useState<MapPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [hovered, setHovered] = useState<MapPoint | null>(null);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    useEffect(() => {
        (async () => {
            try {
                const r = await api.get("/api/knowledge/similarity-map");
                setPoints(r.data.points || []);
            } catch {}
            finally { setLoading(false); }
        })();
    }, []);

    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas || points.length === 0) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const W = canvas.width, H = canvas.height;
        const pad = 60;
        ctx.clearRect(0, 0, W, H);
        // Background
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--background") || "#fff";
        ctx.fillRect(0, 0, W, H);
        // Draw points
        points.forEach((p, i) => {
            const px = pad + p.x * (W - 2 * pad);
            const py = pad + p.y * (H - 2 * pad);
            const r = hovered?.paper_id === p.paper_id ? 10 : 7;
            ctx.beginPath();
            ctx.arc(px, py, r, 0, Math.PI * 2);
            ctx.fillStyle = COLORS[i % COLORS.length];
            ctx.fill();
            ctx.strokeStyle = hovered?.paper_id === p.paper_id ? "#000" : "rgba(0,0,0,0.2)";
            ctx.lineWidth = hovered?.paper_id === p.paper_id ? 2 : 1;
            ctx.stroke();
        });
    }, [points, hovered]);

    useEffect(() => { draw(); }, [draw]);

    const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
        const my = (e.clientY - rect.top) * (canvas.height / rect.height);
        setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
        const pad = 60;
        let closest: MapPoint | null = null;
        let minDist = 20;
        points.forEach((p) => {
            const px = pad + p.x * (canvas.width - 2 * pad);
            const py = pad + p.y * (canvas.height - 2 * pad);
            const d = Math.sqrt((mx - px) ** 2 + (my - py) ** 2);
            if (d < minDist) { minDist = d; closest = p; }
        });
        setHovered(closest);
    };

    const handleClick = () => {
        if (hovered) navigate(`/knowledge/paper/${hovered.paper_id}`);
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={() => navigate("/knowledge")}><ArrowLeft className="h-4 w-4 mr-1" />{t("knowledge.title")}</Button>
                <h1 className="text-xl font-bold flex items-center gap-2"><Map className="h-5 w-5" /> Paper Similarity Map</h1>
                <span className="text-sm text-muted-foreground">{points.length} papers</span>
            </div>
            {loading && <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin mr-2" />Loading embeddings...</div>}
            {!loading && points.length < 2 && <p className="text-center text-muted-foreground py-20">Need at least 2 papers with vector embeddings to generate the map.</p>}
            {!loading && points.length >= 2 && (
                <Card className="relative">
                    <CardContent className="p-2">
                        <canvas
                            ref={canvasRef}
                            width={900}
                            height={600}
                            className="w-full rounded cursor-pointer"
                            style={{ maxHeight: "70vh" }}
                            onMouseMove={handleMouseMove}
                            onClick={handleClick}
                            onMouseLeave={() => setHovered(null)}
                        />
                        {hovered && (
                            <div
                                className="absolute bg-popover border border-border rounded-md shadow-lg px-3 py-2 text-sm pointer-events-none z-10 max-w-xs"
                                style={{ left: mousePos.x + 12, top: mousePos.y - 10 }}
                            >
                                <p className="font-medium">{hovered.title}</p>
                                <p className="text-xs text-muted-foreground mt-0.5">Click to open</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
};

export default SimilarityMap;
