"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import CopyTextButton from "@/components/CopyTextButton";
import MessageInput from "@/components/MessageInput";
import { useAdminAuth } from "@/context/AdminAuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];

const SUGGESTIONS = [
  "What services does the company offer?",
  "Tell me about the company portfolio",
  "What technologies do you specialize in?",
  "How can I get started with your platform?",
];

const LLM_OUTPUT_TEXT = "LLM OUTPUT DATA";

type ReplaceStatus = "idle" | "uploading" | "success" | "error";

export default function Home() {
  const { isAdmin, token } = useAdminAuth();
  const [lastQuery, setLastQuery] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusVariant, setStatusVariant] = useState<"info" | "success" | "error">("info");
  const [isListening, setIsListening] = useState(false);
  const [message, setMessage] = useState("");
  const [replaceFile, setReplaceFile] = useState<File | null>(null);
  const [replaceStatus, setReplaceStatus] = useState<ReplaceStatus>("idle");
  const [replaceError, setReplaceError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sendQuery = useCallback(async (query: string, mode: "send" | "retry") => {
    setIsRetrying(mode === "retry");
    setIsSending(true);
    setStatusVariant("info");
    setStatusMessage(mode === "retry" ? "Retrying your previous query..." : "Processing your message...");

    try {
      const response = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        const message = response.status === 501
          ? "This endpoint is not implemented yet."
          : `${response.status} ${response.statusText}`;
        throw new Error(errorText || message);
      }

      setStatusVariant("success");
      setStatusMessage(mode === "retry" ? "The query was resent successfully." : "The query was sent successfully.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error.";
      setStatusVariant("error");
      setStatusMessage(
        mode === "retry"
          ? `Unable to resend the last query. ${detail}`
          : `Unable to send the query. ${detail}`,
      );
    } finally {
      setIsRetrying(false);
      setIsSending(false);
    }
  }, []);

  const handleMessageSent = useCallback((event: Event) => {
    const detail = (event as CustomEvent<string>).detail;
    if (!detail) return;

    setLastQuery(detail);
    setStatusVariant("info");
    setStatusMessage("Processing your message...");
    void sendQuery(detail, "send");
  }, [sendQuery]);

  useEffect(() => {
    window.addEventListener("messageSent", handleMessageSent as EventListener);
    return () => {
      window.removeEventListener("messageSent", handleMessageSent as EventListener);
    };
  }, [handleMessageSent]);

  const handleRetry = useCallback(() => {
    if (!lastQuery || isRetrying || isSending) return;
    void sendQuery(lastQuery, "retry");
  }, [isRetrying, isSending, lastQuery, sendQuery]);

  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setReplaceFile(file);
    setReplaceStatus("idle");
    setReplaceError("");
  };

  const handleReplaceSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!replaceFile || !token) return;

    const ext = replaceFile.name.slice(replaceFile.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setReplaceStatus("error");
      setReplaceError(`Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`);
      return;
    }

    if (replaceFile.size > MAX_FILE_BYTES) {
      setReplaceStatus("error");
      setReplaceError("File exceeds the 10 MB limit.");
      return;
    }

    setReplaceStatus("uploading");
    setReplaceError("");

    try {
      const formData = new FormData();
      formData.append("file", replaceFile);

      const res = await fetch(`${API_BASE_URL}/documents`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({})) as { detail?: string };
        throw new Error(data.detail ?? "Upload failed");
      }

      setReplaceStatus("success");
      setReplaceFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setReplaceStatus("error");
      setReplaceError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  return (
    <main className="page-root">
      {isAdmin && (
        <section className="doc-replace-panel" aria-label="Replace company document">
          <h2 className="doc-replace-title">Replace Company Document</h2>
          <form className="doc-replace-form" onSubmit={handleReplaceSubmit}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="doc-replace-input"
              onChange={handleFileChange}
              aria-label="Select document to upload"
            />
            <button
              type="submit"
              className="doc-replace-btn"
              disabled={!replaceFile || replaceStatus === "uploading"}
            >
              {replaceStatus === "uploading" ? "Uploading..." : "Upload"}
            </button>
          </form>
          {replaceStatus === "success" && (
            <p className="doc-replace-success" role="status">
              Document replaced successfully. RAG index updated.
            </p>
          )}
          {replaceStatus === "error" && (
            <p className="doc-replace-error" role="alert">
              {replaceError}
            </p>
          )}
        </section>
      )}

      <section className="prompt-suggestions" aria-label="Suggested prompts">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            className="prompt-suggestion"
            onClick={() => handleSuggestionClick(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </section>

      <MessageInput
        message={message}
        onMessageChange={setMessage}
        isListening={isListening}
        setIsListening={setIsListening}
        canRetry={Boolean(lastQuery) && !isSending}
        isRetrying={isRetrying}
        onRetry={handleRetry}
      />

      {statusMessage ? (
        <p className={`status-text ${statusVariant}`} role="status">
          {statusMessage}
        </p>
      ) : null}

      <div className="copy-button-wrapper">
        <CopyTextButton textToCopy={LLM_OUTPUT_TEXT} />
      </div>
    </main>
  );
}
