"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${apiUrl}/api/health`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "ok") {
          setStatus("ok");
        } else {
          setStatus("error");
        }
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">WhiteNote</h1>
        {status === "loading" && <p className="text-gray-500">正在连接 API...</p>}
        {status === "ok" && (
          <p className="text-green-600 font-semibold">API 连接成功</p>
        )}
        {status === "error" && (
          <p className="text-red-600 font-semibold">API 连接失败</p>
        )}
      </div>
    </div>
  );
}
