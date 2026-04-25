"use client";
import { useEffect, useRef, useState } from "react";
import { AsciiSpinner } from "@/components/ui/AsciiSpinner";
import { Btn } from "@/components/ui/Btn";
import { Chip } from "@/components/ui/Chip";
import { Panel } from "@/components/ui/Panel";
import { api, type SourceIngestResponse } from "@/lib/api";

type Props = {
  open: boolean;
  onClose: () => void;
  onIngested: (result: SourceIngestResponse) => void;
};

export function AddSourceModal({ open, onClose, onIngested }: Props) {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Reset state on open and focus the input.
  useEffect(() => {
    if (open) {
      setUrl("");
      setError(null);
      setSubmitting(false);
      const t = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, submitting, onClose]);

  if (!open) return null;

  async function handleSubmit() {
    const trimmed = url.trim();
    if (!trimmed) {
      setError("URL is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.ingestSource({ url: trimmed });
      onIngested(result);
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "ingest failed";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
      onClick={() => {
        if (!submitting) onClose();
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: 480, maxWidth: "90vw" }}
      >
        <Panel id="11·INGEST" title="Ingest URL" sub="// fetch · normalize · persist">
          <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
            <label
              className="tt-up muted"
              style={{ fontSize: 9, letterSpacing: "0.06em" }}
              htmlFor="ingest-url"
            >
              URL
            </label>
            <input
              ref={inputRef}
              id="ingest-url"
              type="url"
              placeholder="https://example.com/article"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !submitting) handleSubmit();
              }}
              disabled={submitting}
              spellCheck={false}
              autoComplete="off"
              style={{
                background: "var(--bg-1)",
                border: "1px solid var(--line-2)",
                color: "var(--ink-0)",
                padding: "8px 10px",
                fontSize: 12,
                fontFamily: "var(--font-mono, monospace)",
                outline: "none",
              }}
            />
            <div
              className="muted"
              style={{ fontSize: 10, lineHeight: 1.4 }}
            >
              Synchronous fetch (~15s timeout). HTML pages are stripped of nav/footer/script
              before hashing. Duplicates are detected by content hash.
            </div>
            {error && (
              <div>
                <Chip tone="red">{error}</Chip>
              </div>
            )}
            <div className="row gap-2" style={{ marginTop: 4, justifyContent: "flex-end" }}>
              <Btn ghost onClick={onClose} disabled={submitting}>
                CANCEL
              </Btn>
              <Btn primary onClick={handleSubmit} disabled={submitting || !url.trim()}>
                {submitting ? (
                  <span className="row gap-2" style={{ alignItems: "center" }}>
                    <AsciiSpinner /> INGESTING
                  </span>
                ) : (
                  "INGEST"
                )}
              </Btn>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
