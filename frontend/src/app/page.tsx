"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import { createTask, getTask } from "@/lib/api";
import { useTaskProgress } from "@/hooks/use-task-progress";
import { ProgressPanel } from "@/components/progress-panel";
import { CodeBlock } from "@/components/code-block";
import type { TaskDetail } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  taskId?: string;
}

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [taskDetail, setTaskDetail] = useState<TaskDetail | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const progress = useTaskProgress(activeTaskId);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, progress]);

  // When task is done, fetch full details
  useEffect(() => {
    if (progress.done && activeTaskId) {
      getTask(activeTaskId)
        .then((detail) => {
          setTaskDetail(detail);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: detail.result_summary ?? `Task ${detail.status}.`,
              taskId: detail.id,
            },
          ]);
        })
        .catch(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: progress.error ?? "Task finished.",
            },
          ]);
        })
        .finally(() => setActiveTaskId(null));
    }
  }, [progress.done, activeTaskId, progress.error]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || submitting) return;

    setInput("");
    setSubmitting(true);
    setTaskDetail(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      const task = await createTask({ description: text });
      setActiveTaskId(task.id);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Failed to create task"}`,
        },
      ]);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Welcome message */}
          {messages.length === 0 && !activeTaskId && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <Bot className="w-12 h-12 text-primary mb-4" />
              <h1 className="text-2xl font-semibold mb-2">
                Agentic Developer
              </h1>
              <p className="text-muted-foreground max-w-md">
                Describe a coding task and I&apos;ll plan it, generate code,
                review for quality &amp; security, and run tests — all
                automatically.
              </p>
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                {[
                  "Add JWT authentication to the user service",
                  "Write unit tests for the payment module",
                  "Refactor the database layer to use async/await",
                  "Add rate limiting middleware to all API endpoints",
                ].map((example) => (
                  <button
                    key={example}
                    onClick={() => setInput(example)}
                    className="text-left px-4 py-3 rounded-lg border border-border hover:border-primary/50 hover:bg-card transition-colors"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
            >
              {msg.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
              )}
              <div
                className={`max-w-2xl rounded-lg px-4 py-3 text-sm ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-card border border-border"
                }`}
              >
                {msg.content}
              </div>
              {msg.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                  <User className="w-4 h-4 text-muted-foreground" />
                </div>
              )}
            </div>
          ))}

          {/* Live progress */}
          {activeTaskId && (
            <div className="bg-card border border-border rounded-lg p-4">
              <ProgressPanel progress={progress} />
            </div>
          )}

          {/* Code artifacts from completed task */}
          {taskDetail &&
            taskDetail.steps.map((step) =>
              step.code_artifacts.map((artifact) => (
                <CodeBlock
                  key={artifact.id}
                  code={artifact.content}
                  language={artifact.language}
                  filePath={artifact.file_path}
                />
              )),
            )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-border bg-card px-6 py-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe a coding task..."
            disabled={submitting || !!activeTaskId}
            className="flex-1 bg-background border border-border rounded-lg px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || submitting || !!activeTaskId}
            className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
