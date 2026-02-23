import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import Layout from "./components/Layout";

// Eager load: Dashboard (landing page)
import Dashboard from "./pages/Dashboard";

// Lazy load: all other pages
const Reader = lazy(() => import("./pages/Reader"));
const KnowledgeBase = lazy(() => import("./pages/KnowledgeBase"));
const PaperDetail = lazy(() => import("./pages/PaperDetail"));
const FlashcardReview = lazy(() => import("./pages/FlashcardReview"));
const KnowledgeGraph = lazy(() => import("./pages/KnowledgeGraph"));
const ResearchInsights = lazy(() => import("./pages/ResearchInsights"));
const RadarPage = lazy(() => import("./pages/RadarPage"));

const Loading = () => (
  <div className="flex h-[50vh] items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
  </div>
);

function App() {
  return (
    <Router>
      <Toaster richColors position="top-center" />
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/reader/:taskId" element={<Reader />} />
            <Route path="/knowledge" element={<KnowledgeBase />} />
            <Route path="/knowledge/paper/:paperId" element={<PaperDetail />} />
            <Route path="/knowledge/review" element={<FlashcardReview />} />
            <Route path="/knowledge/graph" element={<KnowledgeGraph />} />
            <Route path="/knowledge/insights" element={<ResearchInsights />} />
            <Route path="/radar" element={<RadarPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </Suspense>
    </Router>
  );
}

export default App;
