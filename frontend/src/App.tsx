import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import Dashboard from "./pages/Dashboard";
import Reader from "./pages/Reader";
import KnowledgeBase from "./pages/KnowledgeBase";
import PaperDetail from "./pages/PaperDetail";
import FlashcardReview from "./pages/FlashcardReview";
import KnowledgeGraph from "./pages/KnowledgeGraph";
import ResearchInsights from "./pages/ResearchInsights";
import Layout from "./components/Layout";

function App() {
  return (
    <Router>
      <Toaster richColors position="top-center" />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/reader/:taskId" element={<Reader />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/knowledge/paper/:paperId" element={<PaperDetail />} />
          <Route path="/knowledge/review" element={<FlashcardReview />} />
          <Route path="/knowledge/graph" element={<KnowledgeGraph />} />
          <Route path="/knowledge/insights" element={<ResearchInsights />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" />} />
      </Routes>
    </Router>
  );
}

export default App;
