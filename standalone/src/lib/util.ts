import { useEffect, useState } from "react";

/** Trigger a client-side text download — no backend needed. */
export function downloadText(filename: string, text: string, mime = "text/plain"): void {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Evidence score (0–4) → cell background + label. */
const SCORE_COLORS = ["#f1f3f5", "#dbeafe", "#9ec5fe", "#5b8def", "#1f4ed8"];
const SCORE_LABELS = ["No data", "Weak", "Limited", "Moderate", "Strong"];

export function scoreColor(score: number): string {
  return SCORE_COLORS[Math.max(0, Math.min(4, score))];
}
export function scoreLabel(score: number): string {
  return SCORE_LABELS[Math.max(0, Math.min(4, score))];
}
export function scoreTextColor(score: number): string {
  return score >= 3 ? "#fff" : "#1a1a2e";
}

/** Tiny hash-based router so the bundle needs no routing dependency. */
export function useHashRoute(): [string[], (path: string) => void] {
  const parse = () => window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [parts, setParts] = useState<string[]>(parse);
  useEffect(() => {
    const onChange = () => {
      setParts(parse());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const navigate = (path: string) => {
    window.location.hash = path;
  };
  return [parts, navigate];
}

export function href(path: string): string {
  return `#/${path}`;
}
