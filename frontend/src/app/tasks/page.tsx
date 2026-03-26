"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listTasks } from "@/lib/api";
import { TaskStatusBadge } from "@/components/status-badge";
import type { TaskResponse, TaskStatus, PaginatedTasks } from "@/lib/types";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  Clock,
} from "lucide-react";

const statusFilters: (TaskStatus | "all")[] = [
  "all",
  "pending",
  "planning",
  "in_progress",
  "reviewing",
  "completed",
  "failed",
  "cancelled",
];

export default function TasksPage() {
  const [data, setData] = useState<PaginatedTasks | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listTasks(
        page,
        20,
        statusFilter === "all" ? undefined : statusFilter,
      );
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-semibold mb-6">Task History</h1>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        {statusFilters.map((s) => (
          <button
            key={s}
            onClick={() => {
              setStatusFilter(s);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              statusFilter === s
                ? "bg-primary text-primary-foreground"
                : "bg-card border border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {s === "all" ? "All" : s.replace("_", " ")}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm mb-4">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && !data && (
        <div className="text-muted-foreground text-sm">Loading tasks...</div>
      )}

      {/* Empty */}
      {data && data.items.length === 0 && (
        <div className="flex flex-col items-center py-16 text-muted-foreground">
          <Search className="w-10 h-10 mb-3" />
          <p>No tasks found.</p>
        </div>
      )}

      {/* Task list */}
      {data && data.items.length > 0 && (
        <div className="space-y-2">
          {data.items.map((task: TaskResponse) => (
            <Link
              key={task.id}
              href={`/tasks/${task.id}`}
              className="block p-4 rounded-lg bg-card border border-border hover:border-primary/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {task.description}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    <span>
                      {new Date(task.created_at).toLocaleString()}
                    </span>
                    {task.total_tokens > 0 && (
                      <span>{task.total_tokens.toLocaleString()} tokens</span>
                    )}
                  </div>
                </div>
                <TaskStatusBadge status={task.status} />
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-2 rounded-lg border border-border hover:bg-card disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-2 rounded-lg border border-border hover:bg-card disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
