import { Sparkles, Settings, History, TestTubes, LayoutDashboard } from "lucide-react";
import { Outlet } from "react-router-dom";
import SidebarLink from "./SidebarLink";
import ThemeToggle from "./ThemeToggle";
import { FlaskRound } from "lucide-react";

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-100 text-gray-800 dark:bg-gray-950 dark:text-gray-100">
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside className="w-64 shrink-0 border-r border-black/10 bg-white/70 backdrop-blur-md
                          dark:border-white/10 dark:bg-gray-900/60">
          <div className="flex h-16 items-center gap-2 px-4">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-600" />
            <span className="text-lg font-semibold tracking-tight">TestIQ</span>
          </div>
          <nav className="px-3 py-3 space-y-2">
            <SidebarLink to="/" icon={<LayoutDashboard size={16}/>}>Dashboard</SidebarLink>
            <SidebarLink to="/generator" icon={<Sparkles size={16}/>}>Générateur</SidebarLink>
            <SidebarLink to="/executions" icon={<FlaskRound size={16}/>}>Exécutions</SidebarLink>
            <SidebarLink to="/history" icon={<History size={16}/>}>Historique</SidebarLink>
            <SidebarLink to="/settings" icon={<Settings size={16}/>}>Paramètres</SidebarLink>
          </nav>
          <div className="mt-auto p-4">
            <ThemeToggle/>
          </div>
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl p-6">
            <Outlet/>
          </div>
        </main>
      </div>
    </div>
  );
}
