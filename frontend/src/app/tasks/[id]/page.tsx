"use client";

import { useEffect, useState }  from "react";
import { useParams, useRouter } from "next/navigation";
import { getTask, cancelTask } from "@/lib/api";
import { useTaskProgress } from "@/hooks/use-task-progress";
import { ProgressPanel } from "@/components/progress-panel";
import { CodeBlock } from "@/components/code-block";
import { TaskStatusBadge, StepStatusBadge } from "@/components/status-badge";
import type { TaskDetail } from "@/lib/types";
import {
  ArrowLeft,
  Clock,
  Coins,
  XCircle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export default function TaskDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const taskId = params.id;

  const [task, setTask] = useState<TaskDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [cancelling, setCancelling] = useState(false);

  // If not terminal, subscribe to WebSocket updates
  const isLive = task ? !TERMINAL_STATUSES.has(task.status) : false;
  const progress = useTaskProgress(isLive ? taskId : null);

  // Initial fetch
  useEffect(() => {
    setLoading(true);
    getTask(taskId)
      .then((t) => {
        setTask(t);
        // Auto-expand all steps
        setExpandedSteps(new Set(t.steps.map((s) => s.order)));
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load task"),
      )
      .finally(() => setLoading(false));
  }, [taskId]);

  // Re-fetch when WebSocket says done
  useEffect(() => {
    if (progress.done && isLive) {
      getTask(taskId)
        .then(setTask)
        .catch(() => {});
    }
  }, [progress.done, isLive, taskId]);

  async function handleCancel() {
    setCancelling(true);
    try {
      await cancelTask(taskId);
      const updated = await getTask(taskId);
      setTask(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel");
    } finally {
      setCancelling(false);
    }
  }

  function toggleStep(order: number) {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(order)) next.delete(order);
      else next.add(order);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="p-6 text-muted-foreground text-sm">Loading task...</div>
    );
  }

  if (error || !task) {
    return (
      <div className="p-6">
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">
          {error ?? "Task not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <button
        onClick={() => router.push("/tasks")}
        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to tasks
      </button>

      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-semibold mb-2">{task.description}</h1>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(task.created_at).toLocaleString()}
            </span>
            {task.total_tokens > 0 && (
              <span className="flex items-center gap-1">
                <Coins className="w-3 h-3" />
                {task.total_tokens.toLocaleString()} tokens
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <TaskStatusBadge status={task.status} />
          {isLive && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-destructive/10 text-destructive text-xs font-medium hover:bg-destructive/20 disabled:opacity-50"
            >
              <XCircle className="w-3.5 h-3.5" />
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Live progress */}
      {isLive && (
        <div className="bg-card border border-border rounded-lg p-4 mb-6">
          <ProgressPanel progress={progress} />
        </div>
      )}

      {/* Result summary */}
      {task.result_summary && (
        <div className="p-4 rounded-lg bg-success/10 border border-success/30 text-sm mb-6">
          {task.result_summary}
        </div>
      )}

      {/* Steps */}
      {task.steps.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-medium">Steps</h2>
          {task.steps
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((step) => {
              const isExpanded = expandedSteps.has(step.order);
              return (
                <div
                  key={step.id}
                  className="rounded-lg border border-border overflow-hidden"
                >
                  <button
                    onClick={() => toggleStep(step.order)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-card hover:bg-card/80 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="text-xs text-muted-foreground font-mono">
                        #{step.order}
                      </span>
                      <span className="text-sm font-medium">{step.title}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {step.retry_count > 0 && (
                        <span className="text-xs text-warning">
                          {step.retry_count} retries
                        </span>
                      )}
                      <StepStatusBadge status={step.status} />
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="px-4 py-3 border-t border-border space-y-3">
                      <p className="text-sm text-muted-foreground">
                        {step.description}
                      </p>
                      {step.code_artifacts.length > 0 &&
                        step.code_artifacts.map((artifact) => (
                          <CodeBlock
                            key={artifact.id}
                            code={artifact.content}
                            language={artifact.language}
                            filePath={artifact.file_path}
                          />
                        ))}
                      {step.code_artifacts.length === 0 && (
                        <p className="text-xs text-muted-foreground italic">
                          No code artifacts
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
