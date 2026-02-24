import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

const biText = (val: any): string => {
  if (typeof val === "object" && val !== null) return val.en || val.zh || "";
  return String(val || "");
};

const SharedPaper = () => {
  const { token } = useParams<{ token: string }>();
  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    axios.get(`/api/share/${token}`).then(r => setPaper(r.data)).catch(e => setError(e.response?.status === 404 ? "Paper not found" : "Failed to load")).finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center"><div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" /></div>;
  if (error || !paper) return <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center text-center"><div><h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{error || "Not found"}</h1><p className="text-gray-500">This shared paper doesn't exist or has been removed.</p></div></div>;

  const authors = (paper.authors || []).map((a: any) => a.name || a).join(", ");

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div className="text-center space-y-1">
          <div className="inline-flex items-center gap-2 text-blue-600 font-bold text-lg">🛰️ PaperRadar</div>
          <p className="text-xs text-gray-500">Shared Paper</p>
        </div>

        <div className="rounded-2xl border bg-white dark:bg-gray-900 p-6 space-y-5 shadow-sm">
          <h1 className="text-xl font-bold leading-tight">{biText(paper.title)}</h1>
          {paper.tldr && <p className="text-sm font-medium text-blue-600 dark:text-blue-400">💡 {biText(paper.tldr)}</p>}
          {authors && <p className="text-sm text-gray-500">{authors}{paper.year ? ` (${paper.year})` : ""}</p>}
          {paper.abstract && <div><h3 className="text-xs font-semibold uppercase text-gray-400 mb-1">Abstract</h3><p className="text-sm leading-relaxed">{biText(paper.abstract)}</p></div>}

          {paper.findings?.length > 0 && (
            <div><h3 className="text-xs font-semibold uppercase text-gray-400 mb-2">Key Findings</h3>
              <ul className="space-y-1.5">{paper.findings.map((f: any, i: number) => (
                <li key={i} className="text-sm flex gap-2"><span className="shrink-0 text-xs rounded px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">{f.type || "finding"}</span><span>{biText(f.statement)}</span></li>
              ))}</ul>
            </div>
          )}

          {paper.methods?.length > 0 && (
            <div><h3 className="text-xs font-semibold uppercase text-gray-400 mb-2">Methods</h3>
              <ul className="space-y-1">{paper.methods.map((m: any, i: number) => (
                <li key={i} className="text-sm"><span className="font-medium">{biText(m.name)}</span>: {biText(m.description)}</li>
              ))}</ul>
            </div>
          )}

          {paper.entities?.length > 0 && (
            <div><h3 className="text-xs font-semibold uppercase text-gray-400 mb-2">Key Concepts</h3>
              <div className="flex flex-wrap gap-1.5">{paper.entities.map((e: any, i: number) => (
                <span key={i} className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs">{biText(e.name)}</span>
              ))}</div>
            </div>
          )}
        </div>

        <p className="text-center text-xs text-gray-400">Powered by <a href="https://github.com/neosun100/PaperRadar" className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer">PaperRadar</a> — AI-powered research platform</p>
      </div>
    </div>
  );
};

export default SharedPaper;
