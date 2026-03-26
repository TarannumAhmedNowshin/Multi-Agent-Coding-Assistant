"use client";

import { StepStatusBadge, TaskStatusBadge } from "@/components/status-badge";
import type { TaskProgress } from "@/hooks/use-task-progress";
import { Loader2 } from "lucide-react";

export function ProgressPanel({ progress }: { progress: TaskProgress }) {
  const { taskStatus, totalTokens, steps, done, error, resultSummary } =
    progress;

  if (!taskStatus && !error) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm py-3">
        <Loader2 className="w-4 h-4 animate-spin" />
        Connecting...
      </div>
    );
  }

  const sortedSteps = Array.from(steps.entries()).sort(
    ([a], [b]) => a - b,
  );

  const completedSteps = sortedSteps.filter(
    ([, s]) => s.status === "passed",
  ).length;

  return (
    <div className="space-y-4">
      {/* Task-level status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {!done && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
          {taskStatus && <TaskStatusBadge status={taskStatus} />}
        </div>
        {totalTokens > 0 && (
          <span className="text-xs text-muted-foreground">
            {totalTokens.toLocaleString()} tokens
          </span>
        )}
      </div>

      {/* Progress bar */}
      {sortedSteps.length > 0 && (
        <div>
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Progress</span>
            <span>
              {completedSteps} / {sortedSteps.length} steps
            </span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-500"
              style={{
                width: `${sortedSteps.length ? (completedSteps / sortedSteps.length) * 100 : 0}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Step list */}
      {sortedSteps.length > 0 && (
        <div className="space-y-2">
          {sortedSteps.map(([order, step]) => (
            <div
              key={order}
              className="flex items-center justify-between py-1.5 px-3 rounded-md bg-background/50 border border-border text-sm"
            >
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground w-5 text-right font-mono text-xs">
                  {order}
                </span>
                <span>{step.title}</span>
              </div>
              <div className="flex items-center gap-2">
                {step.retryCount > 0 && (
                  <span className="text-xs text-warning">
                    retry {step.retryCount}
                  </span>
                )}
                <StepStatusBadge status={step.status} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Result summary */}
      {resultSummary && (
        <div className="p-3 rounded-lg bg-success/10 border border-success/30 text-sm text-foreground">
          {resultSummary}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive">
          {error}
        </div>
      )}
    </div>
  );
}
