"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSMessage, StepStatus, TaskStatus } from "@/lib/types";
import { taskWebSocketUrl } from "@/lib/api";

export interface TaskProgress {
  taskStatus: TaskStatus | null;
  totalTokens: number;
  resultSummary: string | null;
  steps: Map<
    number,
    { title: string; status: StepStatus; retryCount: number }
  >;
  done: boolean;
  error: string | null;
}

export function useTaskProgress(taskId: string | null): TaskProgress {
  const [progress, setProgress] = useState<TaskProgress>({
    taskStatus: null,
    totalTokens: 0,
    resultSummary: null,
    steps: new Map(),
    done: false,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);

  const handleMessage = useCallback((evt: MessageEvent) => {
    let msg: WSMessage;
    try {
      msg = JSON.parse(evt.data);
    } catch {
      return;
    }

    setProgress((prev) => {
      switch (msg.event) {
        case "task_status":
          return {
            ...prev,
            taskStatus: msg.data.status as TaskStatus,
            totalTokens: (msg.data.total_tokens as number) ?? prev.totalTokens,
            resultSummary:
              (msg.data.result_summary as string) ?? prev.resultSummary,
          };

        case "step_status": {
          const steps = new Map(prev.steps);
          steps.set(msg.data.step_order as number, {
            title: msg.data.title as string,
            status: msg.data.status as StepStatus,
            retryCount: msg.data.retry_count as number,
          });
          return { ...prev, steps };
        }

        case "done":
          return {
            ...prev,
            done: true,
            taskStatus: msg.data.final_status as TaskStatus,
            resultSummary:
              (msg.data.result_summary as string) ?? prev.resultSummary,
          };

        case "error":
          return {
            ...prev,
            error: msg.data.message as string,
            done: true,
          };

        default:
          return prev;
      }
    });
  }, []);

  useEffect(() => {
    if (!taskId) return;

    const ws = new WebSocket(taskWebSocketUrl(taskId));
    wsRef.current = ws;

    ws.onmessage = handleMessage;
    ws.onerror = () =>
      setProgress((p) => ({
        ...p,
        error: "WebSocket connection error",
        done: true,
      }));
    ws.onclose = () =>
      setProgress((p) => (p.done ? p : { ...p, done: true }));

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [taskId, handleMessage]);

  return progress;
}
