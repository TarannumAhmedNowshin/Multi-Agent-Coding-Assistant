import type { TaskStatus, StepStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const taskColors: Record<TaskStatus, string> = {
  pending: "bg-muted-foreground/20 text-muted-foreground",
  planning: "bg-warning/20 text-warning",
  in_progress: "bg-primary/20 text-primary",
  reviewing: "bg-accent/20 text-accent",
  completed: "bg-success/20 text-success",
  failed: "bg-destructive/20 text-destructive",
  cancelled: "bg-muted-foreground/20 text-muted-foreground",
};

const stepColors: Record<StepStatus, string> = {
  pending: "bg-muted-foreground/20 text-muted-foreground",
  generating: "bg-primary/20 text-primary",
  reviewing: "bg-accent/20 text-accent",
  executing: "bg-warning/20 text-warning",
  passed: "bg-success/20 text-success",
  failed: "bg-destructive/20 text-destructive",
  skipped: "bg-muted-foreground/20 text-muted-foreground",
};

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        taskColors[status] ?? "bg-muted text-muted-foreground",
      )}
    >
      {status.replace("_", " ")}
    </span>
  );
}

export function StepStatusBadge({ status }: { status: StepStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        stepColors[status] ?? "bg-muted text-muted-foreground",
      )}
    >
      {status}
    </span>
  );
}
