import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getLLMConfig, saveLLMConfig, type LLMConfig } from "@/lib/api";
import { Settings, CheckCircle, AlertCircle, Loader2, Lock } from "lucide-react";
import api from "@/lib/api";

const PRESETS: { label: string; baseUrl: string }[] = [
    { label: "OpenAI", baseUrl: "https://api.openai.com/v1" },
    { label: "Anthropic (OpenAI-compat)", baseUrl: "https://api.anthropic.com/v1" },
    { label: "OpenRouter", baseUrl: "https://openrouter.ai/api/v1" },
    { label: "Custom", baseUrl: "" },
];

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export default function LLMSettings({ open, onOpenChange }: Props) {
    const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
    const [apiKey, setApiKey] = useState("");
    const [model, setModel] = useState("gpt-4o");
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ status: string; model?: string; latency_ms?: number; detail?: string } | null>(null);

    useEffect(() => {
        if (open) {
            const cfg = getLLMConfig();
            if (cfg) {
                setBaseUrl(cfg.baseUrl || "https://api.openai.com/v1");
                setApiKey(cfg.apiKey || "");
                setModel(cfg.model || "gpt-4o");
            }
            setTestResult(null);
        }
    }, [open]);

    const handleSave = () => {
        saveLLMConfig({ baseUrl, apiKey, model });
        onOpenChange(false);
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const resp = await api.post("/api/test-connection", { base_url: baseUrl, api_key: apiKey, model });
            setTestResult(resp.data);
        } catch (e: any) {
            setTestResult({ status: "error", detail: e.message || "Connection failed" });
        } finally {
            setTesting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Settings className="h-5 w-5" /> LLM Settings
                    </DialogTitle>
                    <DialogDescription>
                        Configure your LLM API to use EasyPaper.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Preset selector */}
                    <div>
                        <Label>Provider Preset</Label>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                            {PRESETS.map((p) => (
                                <button
                                    key={p.label}
                                    onClick={() => { if (p.baseUrl) setBaseUrl(p.baseUrl); }}
                                    className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                                        baseUrl === p.baseUrl
                                            ? "bg-blue-600 text-white border-blue-600"
                                            : "border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                                    }`}
                                >
                                    {p.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <Label htmlFor="base-url">API Endpoint</Label>
                        <Input id="base-url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" className="mt-1" />
                    </div>

                    <div>
                        <Label htmlFor="api-key">API Key</Label>
                        <Input id="api-key" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." className="mt-1" />
                    </div>

                    <div>
                        <Label htmlFor="model">Model</Label>
                        <Input id="model" value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4o" className="mt-1" />
                    </div>

                    {/* Security notice */}
                    <div className="flex items-start gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 text-xs text-green-800 dark:text-green-300">
                        <Lock className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                        <span>Your API key is stored only in your browser's localStorage. It is never saved on our server. Each API request sends your key directly from the browser to your chosen LLM provider.</span>
                    </div>

                    {/* Test result */}
                    {testResult && (
                        <div className={`flex items-center gap-2 p-2.5 rounded-lg text-sm ${
                            testResult.status === "ok"
                                ? "bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300"
                                : "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300"
                        }`}>
                            {testResult.status === "ok" ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                            {testResult.status === "ok"
                                ? `Connected! Model: ${testResult.model}, Latency: ${testResult.latency_ms}ms`
                                : testResult.detail || "Connection failed"}
                        </div>
                    )}

                    <div className="flex gap-2 pt-2">
                        <Button variant="outline" onClick={handleTest} disabled={!apiKey || testing} className="flex-1">
                            {testing ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                            Test Connection
                        </Button>
                        <Button onClick={handleSave} disabled={!apiKey} className="flex-1">
                            Save
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
