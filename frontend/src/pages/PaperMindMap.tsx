import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2, Download } from "lucide-react";
import api from "@/lib/api";

interface MindMapNode { id: string; label: string; type: string; level: number; importance?: number; }
interface MindMapEdge { source: string; target: string; label?: string; dashed?: boolean; }

const TYPE_COLORS: Record<string, string> = {
  paper: "#3b82f6", category: "#8b5cf6", method: "#2563eb", model: "#7c3aed",
  dataset: "#16a34a", metric: "#d97706", concept: "#6b7280", task: "#e11d48",
  finding: "#f59e0b", person: "#06b6d4", organization: "#ea580c",
};

const PaperMindMap = () => {
  const { t } = useTranslation();
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [nodes, setNodes] = useState<MindMapNode[]>([]);
  const [edges, setEdges] = useState<MindMapEdge[]>([]);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const positionsRef = useRef<Record<string, { x: number; y: number }>>({});

  useEffect(() => {
    api.get(`/api/knowledge/papers/${paperId}/mindmap`).then(r => {
      setNodes(r.data.nodes || []); setEdges(r.data.edges || []); setTitle(r.data.title || "");
    }).catch(() => {}).finally(() => setLoading(false));
  }, [paperId]);

  useEffect(() => {
    if (!nodes.length || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const W = canvas.width = canvas.offsetWidth * 2;
    const H = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const w = W / 2, h = H / 2;
    const cx = w / 2, cy = h / 2;

    // Layout: radial from center
    const pos: Record<string, { x: number; y: number }> = {};
    const level1 = nodes.filter(n => n.level === 1);
    const level2 = nodes.filter(n => n.level === 2);

    // Center node
    pos["center"] = { x: cx, y: cy };

    // Level 1 nodes in a circle
    level1.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / level1.length - Math.PI / 2;
      pos[n.id] = { x: cx + Math.cos(angle) * 150, y: cy + Math.sin(angle) * 150 };
    });

    // Level 2 nodes around their parent
    const parentChildren: Record<string, MindMapNode[]> = {};
    edges.forEach(e => {
      const child = level2.find(n => n.id === e.target);
      if (child && pos[e.source]) {
        parentChildren[e.source] = parentChildren[e.source] || [];
        parentChildren[e.source].push(child);
      }
    });
    Object.entries(parentChildren).forEach(([pid, children]) => {
      const parent = pos[pid];
      if (!parent) return;
      const baseAngle = Math.atan2(parent.y - cy, parent.x - cx);
      children.forEach((c, i) => {
        const spread = Math.PI * 0.6;
        const angle = baseAngle - spread / 2 + (spread * i) / Math.max(children.length - 1, 1);
        pos[c.id] = { x: parent.x + Math.cos(angle) * 100, y: parent.y + Math.sin(angle) * 100 };
      });
    });

    // Assign remaining nodes
    nodes.forEach(n => { if (!pos[n.id]) pos[n.id] = { x: cx + (Math.random() - 0.5) * 300, y: cy + (Math.random() - 0.5) * 300 }; });
    positionsRef.current = pos;

    // Draw
    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      // Edges
      edges.forEach(e => {
        const s = pos[e.source], t = pos[e.target];
        if (!s || !t) return;
        ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y);
        ctx.strokeStyle = e.dashed ? "#d1d5db" : "#9ca3af";
        ctx.lineWidth = e.dashed ? 0.5 : 1;
        if (e.dashed) ctx.setLineDash([4, 4]); else ctx.setLineDash([]);
        ctx.stroke();
      });
      // Nodes
      nodes.forEach(n => {
        const p = pos[n.id]; if (!p) return;
        const r = n.level === 0 ? 30 : n.level === 1 ? 20 : 12;
        const color = TYPE_COLORS[n.type] || "#6b7280";
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color + "33"; ctx.fill();
        ctx.strokeStyle = color; ctx.lineWidth = n.level === 0 ? 2 : 1; ctx.setLineDash([]); ctx.stroke();
        // Label
        ctx.fillStyle = document.documentElement.classList.contains("dark") ? "#e5e7eb" : "#1f2937";
        ctx.font = n.level === 0 ? "bold 11px sans-serif" : n.level === 1 ? "bold 9px sans-serif" : "8px sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        const label = n.label.length > 25 ? n.label.slice(0, 25) + "…" : n.label;
        ctx.fillText(label, p.x, p.y + r + 10);
      });
    };
    draw();
  }, [nodes, edges]);

  if (loading) return <div className="flex h-[50vh] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(`/knowledge/paper/${paperId}`)}><ArrowLeft className="h-4 w-4 mr-1" /> Back</Button>
        <h1 className="text-lg font-semibold">🧠 Mind Map: {title}</h1>
        <span className="text-xs text-muted-foreground">{nodes.length} nodes · {edges.length} edges</span>
      </div>
      <div className="rounded-xl border bg-card overflow-hidden" style={{ height: "70vh" }}>
        <canvas ref={canvasRef} className="w-full h-full" />
      </div>
      <div className="flex flex-wrap gap-2">
        {Object.entries(TYPE_COLORS).slice(0, 8).map(([type, color]) => (
          <span key={type} className="inline-flex items-center gap-1.5 text-xs">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
            {type}
          </span>
        ))}
      </div>
    </div>
  );
};

export default PaperMindMap;
