import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  TestTubes,
  FlaskRound,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  Sparkles,
  BarChart3,
  Award
} from "lucide-react";
import { apiJson } from "../lib/api";
import StatsCard from "../components/StatsCard";
import { Skeleton } from "../components/Skeleton";
import EmptyState from "../components/EmptyState";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recentExecutions, setRecentExecutions] = useState([]);
  const [recentTests, setRecentTests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      // Fetch recent executions
      const executions = await apiJson("/executions?limit=5");
      setRecentExecutions(Array.isArray(executions) ? executions : []);

      // Fetch recent test cases
      const tests = await apiJson("/test-cases?limit=5");
      setRecentTests(Array.isArray(tests) ? tests : []);

      // Calculate stats
      const allExecs = await apiJson("/executions?limit=100");
      const allTests = await apiJson("/test-cases?limit=100");

      const execs = Array.isArray(allExecs) ? allExecs : [];
      const testCases = Array.isArray(allTests) ? allTests : [];

      const successCount = execs.filter(e => e.status === 'success').length;
      const failedCount = execs.filter(e => e.status === 'failed').length;
      const runningCount = execs.filter(e => e.status === 'running').length;

      setStats({
        totalTests: testCases.length,
        totalExecutions: execs.length,
        successRate: execs.length > 0 ? ((successCount / execs.length) * 100).toFixed(1) : 0,
        successCount,
        failedCount,
        runningCount,
      });
    } catch (err) {
      console.error("Failed to fetch dashboard:", err);
    } finally {
      setLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl border border-black/10 bg-white/70 p-6 backdrop-blur-md dark:border-white/10 dark:bg-gray-900/60"
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Tableau de bord</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Vue d'ensemble de vos tests et exécutions
            </p>
          </div>
          <Link
            to="/generator"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-fuchsia-600 px-4 py-2 text-sm font-medium text-white hover:from-indigo-700 hover:to-fuchsia-700"
          >
            <Sparkles size={16} />
            Générer un test
          </Link>
        </div>
      </motion.div>

      {/* Stats Cards */}
      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} variant="card" />
          ))}
        </div>
      ) : stats ? (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-4"
        >
          <motion.div variants={itemVariants}>
            <StatsCard
              title="Tests générés"
              value={stats.totalTests}
              icon={TestTubes}
              color="indigo"
              description="Total des cas de test créés"
            />
          </motion.div>

          <motion.div variants={itemVariants}>
            <StatsCard
              title="Exécutions"
              value={stats.totalExecutions}
              icon={FlaskRound}
              color="purple"
              description="Total des exécutions lancées"
            />
          </motion.div>

          <motion.div variants={itemVariants}>
            <StatsCard
              title="Taux de succès"
              value={`${stats.successRate}%`}
              icon={TrendingUp}
              color="emerald"
              trend={
                stats.successRate >= 80
                  ? { value: Math.round(stats.successRate - 80), direction: 'up' }
                  : { value: Math.round(80 - stats.successRate), direction: 'down' }
              }
              description={`${stats.successCount} réussies, ${stats.failedCount} échouées`}
            />
          </motion.div>

          <motion.div variants={itemVariants}>
            <StatsCard
              title="En cours"
              value={stats.runningCount}
              icon={Clock}
              color="amber"
              description="Exécutions en cours d'exécution"
            />
          </motion.div>
        </motion.div>
      ) : null}

      {/* Recent Activity Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Executions */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl border border-black/10 bg-white p-6 dark:border-white/10 dark:bg-gray-900"
        >
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Exécutions récentes</h2>
            <Link
              to="/executions"
              className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
            >
              Voir tout →
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : recentExecutions.length === 0 ? (
            <EmptyState
              icon="inbox"
              title="Aucune exécution"
              description="Lancez votre première exécution depuis la page Générateur."
            />
          ) : (
            <div className="space-y-3">
              {recentExecutions.map((exec) => (
                <Link
                  key={exec.id || exec._id}
                  to={`/executions?focus=${exec.id || exec._id}`}
                  className="block rounded-xl border border-black/5 p-4 transition hover:bg-gray-50 dark:border-white/5 dark:hover:bg-gray-800"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">
                          {exec.kind || 'Test'}
                        </span>
                        <StatusBadge status={exec.status} />
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        {exec.language} • {new Date(exec.created_at).toLocaleString()}
                      </p>
                    </div>
                    {exec.status === 'success' ? (
                      <CheckCircle2 size={20} className="text-emerald-600" />
                    ) : exec.status === 'failed' ? (
                      <XCircle size={20} className="text-rose-600" />
                    ) : (
                      <Clock size={20} className="text-amber-600" />
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </motion.div>

        {/* Recent Tests */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-2xl border border-black/10 bg-white p-6 dark:border-white/10 dark:bg-gray-900"
        >
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Tests récents</h2>
            <Link
              to="/history"
              className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
            >
              Voir tout →
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : recentTests.length === 0 ? (
            <EmptyState
              icon="file"
              title="Aucun test"
              description="Générez votre premier cas de test pour commencer."
            />
          ) : (
            <div className="space-y-3">
              {recentTests.map((test) => (
                <div
                  key={test._id}
                  className="rounded-xl border border-black/5 p-4 dark:border-white/5"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">
                          {test.test_type}
                        </span>
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200">
                          {test.status || 'confirmed'}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        {test.language} • {test.provider} • {new Date(test.created_at).toLocaleString()}
                      </p>
                    </div>
                    <TestTubes size={20} className="text-indigo-600" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="rounded-2xl border border-black/10 bg-gradient-to-br from-indigo-50 to-fuchsia-50 p-6 dark:border-white/10 dark:from-indigo-950/30 dark:to-fuchsia-950/30"
      >
        <h2 className="mb-4 text-lg font-semibold">Actions rapides</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Link
            to="/generator"
            className="flex items-center gap-3 rounded-xl border border-black/10 bg-white p-4 transition hover:shadow-md dark:border-white/10 dark:bg-gray-900"
          >
            <div className="rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 p-3 text-white">
              <Sparkles size={20} />
            </div>
            <div>
              <h3 className="font-medium">Générer un test</h3>
              <p className="text-xs text-gray-500">Créer un nouveau cas de test</p>
            </div>
          </Link>

          <Link
            to="/executions"
            className="flex items-center gap-3 rounded-xl border border-black/10 bg-white p-4 transition hover:shadow-md dark:border-white/10 dark:bg-gray-900"
          >
            <div className="rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 p-3 text-white">
              <FlaskRound size={20} />
            </div>
            <div>
              <h3 className="font-medium">Voir les exécutions</h3>
              <p className="text-xs text-gray-500">Suivre les tests en cours</p>
            </div>
          </Link>

          <Link
            to="/history"
            className="flex items-center gap-3 rounded-xl border border-black/10 bg-white p-4 transition hover:shadow-md dark:border-white/10 dark:bg-gray-900"
          >
            <div className="rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 p-3 text-white">
              <BarChart3 size={20} />
            </div>
            <div>
              <h3 className="font-medium">Historique</h3>
              <p className="text-xs text-gray-500">Consulter l'historique complet</p>
            </div>
          </Link>
        </div>
      </motion.div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    queued: "bg-gray-100 text-gray-800 dark:bg-gray-900/40 dark:text-gray-200",
    running: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200",
    success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200",
  };

  const s = String(status || "").toLowerCase();
  const cls = colors[s] || colors.queued;

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {s || "—"}
    </span>
  );
}
