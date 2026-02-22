import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Search, Loader2, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

interface GraphNode {
    id: string;
    name: string;
    type: string;
    definition?: string;
    importance: number;
    paper_id: string;
}

interface GraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    description?: string;
}

const TYPE_COLORS: Record<string, string> = {
    method: "#3b82f6",
    model: "#8b5cf6",
    dataset: "#22c55e",
    metric: "#f59e0b",
    concept: "#6b7280",
    task: "#f43f5e",
    person: "#06b6d4",
    organization: "#f97316",
};

const KnowledgeGraph = () => {
    const navigate = useNavigate();
    const [nodes, setNodes] = useState<GraphNode[]>([]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [zoom, setZoom] = useState(1);
    const [offset, setOffset] = useState({ x: 0, y: 0 });
    const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});
    const animRef = useRef<number>(0);
    const dragRef = useRef<{ dragging: boolean; startX: number; startY: number; nodeId?: string }>({
        dragging: false,
        startX: 0,
        startY: 0,
    });

    const fetchGraph = useCallback(async () => {
        try {
            const response = await api.get("/api/knowledge/graph");
            setNodes(response.data.nodes);
            setEdges(response.data.edges);
        } catch {
            toast.error("Failed to load knowledge graph.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchGraph();
    }, [fetchGraph]);

    // Initialize positions using force-directed layout
    useEffect(() => {
        if (nodes.length === 0) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const w = canvas.width;
        const h = canvas.height;

        // Initialize random positions
        const positions: Record<string, { x: number; y: number; vx: number; vy: number }> = {};
        nodes.forEach((node) => {
            positions[node.id] = {
                x: w / 2 + (Math.random() - 0.5) * w * 0.6,
                y: h / 2 + (Math.random() - 0.5) * h * 0.6,
                vx: 0,
                vy: 0,
            };
        });

        // Simple force simulation
        let iterations = 0;
        const maxIterations = 200;

        const simulate = () => {
            if (iterations >= maxIterations) {
                const finalPos: Record<string, { x: number; y: number }> = {};
                Object.entries(positions).forEach(([id, p]) => {
                    finalPos[id] = { x: p.x, y: p.y };
                });
                setNodePositions(finalPos);
                return;
            }

            // Repulsion between all nodes
            const nodeIds = Object.keys(positions);
            for (let i = 0; i < nodeIds.length; i++) {
                for (let j = i + 1; j < nodeIds.length; j++) {
                    const a = positions[nodeIds[i]];
                    const b = positions[nodeIds[j]];
                    const dx = b.x - a.x;
                    const dy = b.y - a.y;
                    const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
                    const force = 5000 / (dist * dist);
                    const fx = (dx / dist) * force;
                    const fy = (dy / dist) * force;
                    a.vx -= fx;
                    a.vy -= fy;
                    b.vx += fx;
                    b.vy += fy;
                }
            }

            // Attraction along edges
            edges.forEach((edge) => {
                const a = positions[edge.source];
                const b = positions[edge.target];
                if (!a || !b) return;
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const force = (dist - 120) * 0.01;
                const fx = (dx / Math.max(dist, 1)) * force;
                const fy = (dy / Math.max(dist, 1)) * force;
                a.vx += fx;
                a.vy += fy;
                b.vx -= fx;
                b.vy -= fy;
            });

            // Center gravity
            nodeIds.forEach((id) => {
                const p = positions[id];
                p.vx += (w / 2 - p.x) * 0.001;
                p.vy += (h / 2 - p.y) * 0.001;
                // Damping
                p.vx *= 0.9;
                p.vy *= 0.9;
                p.x += p.vx;
                p.y += p.vy;
                // Bounds
                p.x = Math.max(30, Math.min(w - 30, p.x));
                p.y = Math.max(30, Math.min(h - 30, p.y));
            });

            iterations++;
            animRef.current = requestAnimationFrame(simulate);
        };

        simulate();
        return () => cancelAnimationFrame(animRef.current);
    }, [nodes, edges]);

    // Draw canvas
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || Object.keys(nodePositions).length === 0) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.translate(offset.x, offset.y);
        ctx.scale(zoom, zoom);

        // Draw edges
        edges.forEach((edge) => {
            const from = nodePositions[edge.source];
            const to = nodePositions[edge.target];
            if (!from || !to) return;

            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
            ctx.strokeStyle = "#d1d5db";
            ctx.lineWidth = 1;
            ctx.stroke();

            // Edge label
            const midX = (from.x + to.x) / 2;
            const midY = (from.y + to.y) / 2;
            ctx.font = "9px sans-serif";
            ctx.fillStyle = "#9ca3af";
            ctx.textAlign = "center";
            ctx.fillText(edge.type, midX, midY - 4);
        });

        // Draw nodes
        const filteredLower = search.toLowerCase();
        nodes.forEach((node) => {
            const pos = nodePositions[node.id];
            if (!pos) return;

            const isHighlighted = search && node.name.toLowerCase().includes(filteredLower);
            const isSelected = selectedNode?.id === node.id;
            const radius = 6 + node.importance * 10;

            // Node circle
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
            ctx.fillStyle = TYPE_COLORS[node.type] || "#6b7280";
            if (search && !isHighlighted) {
                ctx.globalAlpha = 0.2;
            }
            ctx.fill();
            ctx.globalAlpha = 1;

            if (isSelected || isHighlighted) {
                ctx.strokeStyle = isSelected ? "#000" : TYPE_COLORS[node.type] || "#6b7280";
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Node label
            ctx.font = isSelected ? "bold 11px sans-serif" : "10px sans-serif";
            ctx.fillStyle = search && !isHighlighted ? "#d1d5db" : "#374151";
            ctx.textAlign = "center";
            ctx.fillText(node.name, pos.x, pos.y + radius + 12);
        });

        ctx.restore();
    }, [nodePositions, edges, nodes, search, selectedNode, zoom, offset]);

    // Canvas click handler
    const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left - offset.x) / zoom;
        const y = (e.clientY - rect.top - offset.y) / zoom;

        const clicked = nodes.find((node) => {
            const pos = nodePositions[node.id];
            if (!pos) return false;
            const radius = 6 + node.importance * 10;
            const dx = pos.x - x;
            const dy = pos.y - y;
            return dx * dx + dy * dy <= radius * radius;
        });

        setSelectedNode(clicked || null);
    };

    // Canvas pan
    const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
        dragRef.current = { dragging: true, startX: e.clientX - offset.x, startY: e.clientY - offset.y };
    };

    const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
        if (!dragRef.current.dragging) return;
        setOffset({
            x: e.clientX - dragRef.current.startX,
            y: e.clientY - dragRef.current.startY,
        });
    };

    const handleMouseUp = () => {
        dragRef.current.dragging = false;
    };

    if (loading) {
        return (
            <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
        );
    }

    if (nodes.length === 0) {
        return (
            <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center space-y-4">
                <p className="text-muted-foreground">
                    No entities in your knowledge graph yet. Extract knowledge from papers to build your graph.
                </p>
                <Button onClick={() => navigate("/knowledge")}>
                    <ArrowLeft className="mr-2 h-4 w-4" /> Knowledge Base
                </Button>
            </div>
        );
    }

    return (
        <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
            {/* Toolbar */}
            <div className="flex items-center justify-between rounded-xl border bg-card p-3 shadow-sm">
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => navigate("/knowledge")}>
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back
                    </Button>
                    <div className="h-4 w-px bg-border mx-2 hidden sm:block" />
                    <h1 className="text-sm font-medium hidden sm:block">Knowledge Graph</h1>
                    <span className="text-xs text-muted-foreground hidden sm:block">
                        ({nodes.length} entities, {edges.length} relationships)
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="relative w-48">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                        <Input
                            placeholder="Search entities..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-8 h-8 text-xs"
                        />
                    </div>
                    <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.min(z + 0.2, 3))}>
                        <ZoomIn className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.max(z - 0.2, 0.3))}>
                        <ZoomOut className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => {
                            setZoom(1);
                            setOffset({ x: 0, y: 0 });
                        }}
                    >
                        <Maximize2 className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </div>

            {/* Graph Canvas */}
            <div className="relative flex-1 rounded-xl border bg-card shadow-sm overflow-hidden">
                <canvas
                    ref={canvasRef}
                    width={1200}
                    height={800}
                    className="w-full h-full cursor-grab active:cursor-grabbing"
                    onClick={handleCanvasClick}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                />

                {/* Legend */}
                <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 rounded-lg bg-card/90 backdrop-blur-sm border p-2 text-xs shadow-sm">
                    {Object.entries(TYPE_COLORS).map(([type, color]) => (
                        <div key={type} className="flex items-center gap-1">
                            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
                            <span className="text-muted-foreground capitalize">{type}</span>
                        </div>
                    ))}
                </div>

                {/* Selected Node Detail */}
                {selectedNode && (
                    <div className="absolute top-4 right-4 w-64 rounded-lg bg-card border shadow-lg p-4 space-y-2">
                        <div className="flex items-center justify-between">
                            <h3 className="font-medium text-sm">{selectedNode.name}</h3>
                            <span
                                className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium text-white")}
                                style={{ backgroundColor: TYPE_COLORS[selectedNode.type] }}
                            >
                                {selectedNode.type}
                            </span>
                        </div>
                        {selectedNode.definition && (
                            <p className="text-xs text-muted-foreground">{selectedNode.definition}</p>
                        )}
                        <p className="text-xs text-muted-foreground">
                            Importance: {Math.round(selectedNode.importance * 100)}%
                        </p>
                        {/* Related edges */}
                        <div className="border-t pt-2 space-y-1">
                            <p className="text-xs font-medium text-muted-foreground">Relationships:</p>
                            {edges
                                .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                                .slice(0, 5)
                                .map((e) => {
                                    const other = e.source === selectedNode.id
                                        ? nodes.find((n) => n.id === e.target)
                                        : nodes.find((n) => n.id === e.source);
                                    const direction = e.source === selectedNode.id ? "→" : "←";
                                    return (
                                        <p key={e.id} className="text-xs text-muted-foreground">
                                            {direction} <span className="font-medium">{e.type}</span>{" "}
                                            {other?.name || "?"}
                                        </p>
                                    );
                                })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default KnowledgeGraph;
