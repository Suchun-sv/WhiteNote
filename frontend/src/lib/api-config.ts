/**
 * API 配置工具
 * 处理不同环境下的 API 基础 URL
 */

/**
 * 获取 API 基础 URL
 * 
 * 优先级：
 * 1. NEXT_PUBLIC_API_URL 环境变量
 * 2. 浏览器环境：根据当前主机自动判断（开发环境）
 * 3. 服务端：默认 localhost:8000
 */
export function getApiBase(): string {
  // 如果设置了环境变量，直接使用
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  // 在浏览器环境中
  if (typeof window !== "undefined") {
    // 开发环境：使用当前主机 + 8000 端口（适用于手机访问同一网络下的电脑）
    if (process.env.NODE_ENV === "development") {
      const hostname = window.location.hostname;
      // 如果是 localhost 或 127.0.0.1，保持原样
      if (hostname === "localhost" || hostname === "127.0.0.1") {
        return "http://localhost:8000";
      }
      // 否则使用当前主机（适用于手机访问同一网络下的电脑）
      // 例如：如果前端运行在 192.168.1.100:3000，API 会在 192.168.1.100:8000
      return `http://${hostname}:8000`;
    }
    // 生产环境：使用相对路径，自动使用当前域名
    return ""; // 使用相对路径，自动使用当前域名
  }

  // 服务端渲染时，默认使用 localhost
  return "http://localhost:8000";
}
