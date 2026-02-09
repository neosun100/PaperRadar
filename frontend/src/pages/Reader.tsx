import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Download, Loader2, FileText, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const Reader = () => {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const [status, setStatus] = useState<string>("loading");
    const [originalPdfUrl, setOriginalPdfUrl] = useState<string | null>(null);
    const [resultPdfUrl, setResultPdfUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [focusMode, setFocusMode] = useState(false);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const token = localStorage.getItem("token");
                const headers = { "Authorization": `Bearer ${token}` };

                const response = await axios.get(`/api/status/${taskId}`, { headers });
                setStatus(response.data.status);

                if (response.data.status === "completed") {
                    // Fetch Original PDF as blob
                    const originalResponse = await axios.get(`/api/original/${taskId}/pdf`, {
                        headers,
                        responseType: 'blob'
                    });
                    const originalBlob = new Blob([originalResponse.data], { type: 'application/pdf' });
                    setOriginalPdfUrl(URL.createObjectURL(originalBlob));

                    // Fetch Result PDF as blob (Replacing HTML preview)
                    const resultResponse = await axios.get(`/api/result/${taskId}/pdf`, {
                        headers,
                        responseType: 'blob'
                    });
                    const resultBlob = new Blob([resultResponse.data], { type: 'application/pdf' });
                    setResultPdfUrl(URL.createObjectURL(resultBlob));

                    setLoading(false);
                } else if (response.data.status === "failed") {
                    setLoading(false);
                } else {
                    if (response.data.status !== "completed") {
                        setTimeout(fetchStatus, 2000);
                    }
                }
            } catch (error) {
                console.error("Error fetching status", error);
                setLoading(false);
                setStatus("error");
            }
        };

        fetchStatus();

        return () => {
            if (originalPdfUrl) URL.revokeObjectURL(originalPdfUrl);
            if (resultPdfUrl) URL.revokeObjectURL(resultPdfUrl);
        };
    }, [taskId]);

    const handleDownload = async () => {
        if (resultPdfUrl) {
            const link = document.createElement('a');
            link.href = resultPdfUrl;
            link.setAttribute('download', `simplified_${taskId}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
        }
    };

    if (loading || status === "processing" || status === "pending") {
        return (
            <div className="flex h-[calc(100vh-4rem)] flex-col items-center justify-center space-y-4">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                <p className="text-lg font-medium text-muted-foreground">
                    {status === "processing" ? "AI is simplifying your document..." : "Loading..."}
                </p>
            </div>
        );
    }

    if (status === "failed" || status === "error") {
        return (
            <div className="flex h-[calc(100vh-4rem)] flex-col items-center justify-center space-y-4">
                <div className="rounded-full bg-red-100 p-4 text-red-600">
                    <FileText className="h-8 w-8" />
                </div>
                <h2 className="text-xl font-semibold">Processing Failed</h2>
                <p className="text-muted-foreground">Something went wrong while processing this document.</p>
                <Button onClick={() => navigate("/dashboard")}>Back to Dashboard</Button>
            </div>
        );
    }

    return (
        <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
            {/* Toolbar */}
            <div className="flex items-center justify-between rounded-xl border bg-white p-3 shadow-sm">
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back
                    </Button>
                    <div className="h-4 w-px bg-gray-200 mx-2" />
                    <h1 className="text-sm font-medium text-gray-900">Document Reader</h1>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setFocusMode(!focusMode)}
                        className={cn("gap-2", focusMode && "bg-primary/10 text-primary border-primary/20")}
                    >
                        <Sparkles className="h-4 w-4" />
                        {focusMode ? "Show Original" : "Focus Mode"}
                    </Button>
                    <Button size="sm" onClick={handleDownload} className="gap-2">
                        <Download className="h-4 w-4" />
                        Download PDF
                    </Button>
                </div>
            </div>

            {/* Split Pane */}
            <ResizablePanelGroup direction="horizontal" className="min-h-0 flex-1 rounded-xl border bg-white shadow-sm overflow-hidden" style={{ direction: 'ltr' }}>
                {/* Left Panel: AI Simplified PDF */}
                <ResizablePanel defaultSize={focusMode ? 100 : 50} minSize={30}>
                    <div className="flex h-full flex-col bg-white">
                        <div className="flex items-center justify-between border-b bg-white px-4 py-2">
                            <div className="flex items-center gap-2">
                                <Sparkles className="h-3 w-3 text-primary" />
                                <span className="text-xs font-medium text-primary uppercase tracking-wider">AI Simplified Result (PDF)</span>
                            </div>
                        </div>
                        <div className="flex-1 bg-gray-100/50">
                            {resultPdfUrl && (
                                <iframe
                                    src={resultPdfUrl}
                                    className="h-full w-full border-none"
                                    title="Simplified PDF"
                                />
                            )}
                        </div>
                    </div>
                </ResizablePanel>

                {/* Right Panel: Original PDF - Hidden in Focus Mode */}
                {!focusMode && (
                    <>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize={50} minSize={30}>
                            <div className="flex h-full flex-col">
                                <div className="flex items-center justify-between border-b bg-gray-50/50 px-4 py-2">
                                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Original Source (PDF)</span>
                                </div>
                                <div className="flex-1 bg-gray-100/50">
                                    {originalPdfUrl && (
                                        <iframe
                                            src={originalPdfUrl}
                                            className="h-full w-full border-none"
                                            title="Original PDF"
                                        />
                                    )}
                                </div>
                            </div>
                        </ResizablePanel>
                    </>
                )}
            </ResizablePanelGroup>
        </div>
    );
};

export default Reader;
