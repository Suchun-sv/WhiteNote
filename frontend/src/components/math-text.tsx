"use client";

import { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

interface Segment {
  type: "text" | "math";
  content: string;
  display: boolean;
}

/**
 * Parse text containing LaTeX math delimiters into segments.
 * Supports: $$...$$, $...$, \(...\), \[...\]
 */
function parseMathSegments(text: string): Segment[] {
  const segments: Segment[] = [];
  // Match $$...$$ first (greedy over $), then $...$ (non-greedy, no leading/trailing space),
  // then \(...\) and \[...\]
  const regex =
    /(\$\$[\s\S]*?\$\$|\$(?!\s)(?:[^$\\]|\\.)+?\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\])/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({
        type: "text",
        content: text.slice(lastIndex, match.index),
        display: false,
      });
    }

    const raw = match[0];
    let latex: string;
    let display: boolean;

    if (raw.startsWith("$$")) {
      latex = raw.slice(2, -2);
      display = true;
    } else if (raw.startsWith("$")) {
      latex = raw.slice(1, -1);
      display = false;
    } else if (raw.startsWith("\\(")) {
      latex = raw.slice(2, -2);
      display = false;
    } else {
      // \[...\]
      latex = raw.slice(2, -2);
      display = true;
    }

    segments.push({ type: "math", content: latex, display });
    lastIndex = match.index + raw.length;
  }

  if (lastIndex < text.length) {
    segments.push({
      type: "text",
      content: text.slice(lastIndex),
      display: false,
    });
  }

  return segments;
}

interface MathTextProps {
  text: string;
  className?: string;
}

export function MathText({ text, className }: MathTextProps) {
  const segments = useMemo(() => parseMathSegments(text), [text]);

  // If no math found, render as plain text (avoids extra spans)
  if (segments.length === 1 && segments[0].type === "text") {
    return <span className={className}>{text}</span>;
  }

  return (
    <span className={className}>
      {segments.map((seg, i) => {
        if (seg.type === "text") {
          return <span key={i}>{seg.content}</span>;
        }
        try {
          const html = katex.renderToString(seg.content, {
            displayMode: seg.display,
            throwOnError: false,
          });
          return (
            <span key={i} dangerouslySetInnerHTML={{ __html: html }} />
          );
        } catch {
          // Fallback: show raw LaTeX on parse error
          return <code key={i}>{seg.content}</code>;
        }
      })}
    </span>
  );
}
