"use client";

import { useState } from "react";
import { indexProject } from "@/lib/api";
import type { IndexResponse } from "@/lib/types";
import {
  FolderSearch,
  Upload,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

export default function ProjectsPage() {
  const [directory, setDirectory] = useState("");
  const [projectName, setProjectName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IndexResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleIndex(e: React.FormEvent) {
    e.preventDefault();
    if (!directory.trim() || !projectName.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await indexProject({
        directory: directory.trim(),
        project_name: projectName.trim(),
        description: description.trim() || null,
      });
      setResult(res);
      setDirectory("");
      setProjectName("");
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Indexing failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold mb-2">Projects</h1>
      <p className="text-muted-foreground text-sm mb-8">
        Index a codebase to enable RAG-powered context retrieval for your tasks.
      </p>

      {/* Index form */}
      <form
        onSubmit={handleIndex}
        className="bg-card border border-border rounded-lg p-6 space-y-4"
      >
        <div className="flex items-center gap-2 mb-2">
          <FolderSearch className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-medium">Index a Codebase</h2>
        </div>

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">
            Directory Path
          </label>
          <input
            type="text"
            value={directory}
            onChange={(e) => setDirectory(e.target.value)}
            placeholder="/path/to/project"
            required
            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">
            Project Name
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="My Project"
            required
            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of the project..."
            rows={2}
            className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !directory.trim() || !projectName.trim()}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Upload className="w-4 h-4" />
          {loading ? "Indexing..." : "Start Indexing"}
        </button>
      </form>

      {/* Success */}
      {result && (
        <div className="mt-6 p-4 rounded-lg bg-success/10 border border-success/30 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-success">Indexing started</p>
            <p className="text-muted-foreground mt-1">
              Project: <strong>{result.project_name}</strong> — {result.message}
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-6 p-4 rounded-lg bg-destructive/10 border border-destructive/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
          <div className="text-sm text-destructive">{error}</div>
        </div>
      )}
    </div>
  );
}
