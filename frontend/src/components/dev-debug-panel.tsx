"use client";

import { useState, useEffect } from "react";

interface DevDebugPanelProps {
  error: Error;
}

export function DevDebugPanel({ error }: DevDebugPanelProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // 只在客户端渲染，避免 hydration 错误
  if (!isMounted || process.env.NODE_ENV !== "development") {
    return null;
  }

  return (
    <details className="mt-2 text-xs">
      <summary className="cursor-pointer text-red-500 hover:text-red-700">
        查看调试信息
      </summary>
      <pre className="mt-2 p-2 bg-red-100 rounded overflow-auto">
        {error.stack || error.message}
      </pre>
    </details>
  );
}
