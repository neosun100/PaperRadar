import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Reader from "./pages/Reader";

// Simple auth guard - 临时跳过认证
const PrivateRoute = ({ children }: { children: JSX.Element }) => {
  return children; // TODO: 测试完成后恢复认证检查
  // const token = localStorage.getItem("token");
  // return token ? children : <Navigate to="/login" />;
};

import Layout from "./components/Layout";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected Routes with Layout */}
        <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/reader/:taskId" element={<Reader />} />
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </Router>
  );
}

export default App;
