import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Generator from "./pages/Generator";
import History from "./pages/History";
import Settings from "./pages/Settings";
import Executions from "./pages/Executions";
import ExecutionDetail from "./pages/ExecutionDetail";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout/>}>
        <Route path="/" element={<Dashboard/>}/>
        <Route path="/generator" element={<Generator/>}/>
        <Route path="/executions" element={<Executions/>}/>
        <Route path="/executions/:execId" element={<ExecutionDetail/>}/>
        <Route path="/history" element={<History/>}/>
        <Route path="/settings" element={<Settings/>}/>
      </Route>
    </Routes>
  );
}
