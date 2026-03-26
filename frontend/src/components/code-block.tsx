"use client";

import { useEffect, useRef, useState } from "react";

export function CodeBlock({
  code,
  language,
  filePath,
}: {
  code: string;
  language?: string | null;
  filePath?: string;
}) {
  const [copied, setCopied] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (copied) {
      const t = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(t);
    }
  }, [copied]);

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => setCopied(true));
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden bg-[#0d1117]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-card border-b border-border text-xs">
        <span className="text-muted-foreground font-mono">
          {filePath ?? language ?? "code"}
        </span>
        <button
          onClick={handleCopy}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      {/* Code */}
      <pre
        ref={preRef}
        className="p-4 overflow-x-auto text-sm leading-relaxed font-mono text-foreground"
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}
