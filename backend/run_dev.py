#!/usr/bin/env python3
"""
开发环境启动脚本

功能:
1. 自动加载 settings.yaml 配置
2. 支持热重载
3. 可配置端口和主机

使用方式:
    # 直接运行
    python run_dev.py
    
    # 指定端口
    python run_dev.py --port 8080
    
    # 关闭热重载
    python run_dev.py --no-reload
    
    # Debug 模式 (配合 VS Code debugger)
    python run_dev.py --debug
"""

import argparse
import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="LavenderSentinel Backend Dev Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload (default: True)")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debugpy for VS Code debugging")
    parser.add_argument("--debug-port", type=int, default=5678, help="Debugpy port (default: 5678)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Log level")
    
    args = parser.parse_args()
    
    # Debug 模式: 启动 debugpy
    if args.debug:
        try:
            import debugpy
            debugpy.listen((args.host, args.debug_port))
            print(f"🐛 Debugpy listening on {args.host}:{args.debug_port}")
            print("   Waiting for debugger to attach...")
            # 如果需要等待调试器连接后再启动，取消下面这行注释
            # debugpy.wait_for_client()
        except ImportError:
            print("⚠️  debugpy not installed. Run: pip install debugpy")
            sys.exit(1)
    
    # 启动 uvicorn
    import uvicorn
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              🪻 LavenderSentinel Backend                     ║
╠══════════════════════════════════════════════════════════════╣
║  Host:     {args.host:<48} ║
║  Port:     {args.port:<48} ║
║  Reload:   {str(args.reload):<48} ║
║  Debug:    {str(args.debug):<48} ║
║  Log:      {args.log_level:<48} ║
╠══════════════════════════════════════════════════════════════╣
║  API Docs: http://{args.host}:{args.port}/docs{' ' * 28}║
║  ReDoc:    http://{args.host}:{args.port}/redoc{' ' * 27}║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload and not args.debug,  # Debug 模式下禁用 reload
        log_level=args.log_level,
        reload_dirs=["app"] if args.reload and not args.debug else None,
    )


if __name__ == "__main__":
    main()

