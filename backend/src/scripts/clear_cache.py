import os
import shutil
from pathlib import Path

def clear_streamlit_cache():
    """
    清除 Streamlit 的本地磁盘缓存。
    Streamlit 默认缓存路径通常在 ~/.streamlit/cache
    """
    cache_path = Path.home() / ".streamlit" / "cache"
    if cache_path.exists():
        print(f"🧹 正在清理 Streamlit 磁盘缓存: {cache_path}")
        try:
            shutil.rmtree(cache_path)
            print("✅ Streamlit 磁盘缓存已清除")
        except Exception as e:
            print(f"❌ 清理失败: {e}")
    else:
        print("ℹ️ 未发现 Streamlit 磁盘缓存目录")

def clear_project_runtime_cache():
    """
    清除项目中生成的临时文件（如 PDF, 图片缓存）。
    """
    # 假设项目根目录在 scripts 的上两级
    project_root = Path(__file__).parent.parent.parent.parent
    
    # 定义需要清理的目录
    dirs_to_clear = [
        project_root / "backend" / "cache" / "imgs",
        project_root / "backend" / "cache" / "pdfs",
        project_root / "backend" / "logs",
    ]
    
    for d in dirs_to_clear:
        if d.exists():
            print(f"🧹 正在清理项目缓存目录: {d}")
            for item in d.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    print(f"⚠️ 无法删除 {item}: {e}")
            print(f"✅ {d.name} 已清空")

if __name__ == "__main__":
    print("🚀 开始清理缓存...")
    clear_streamlit_cache()
    # clear_project_runtime_cache() # 如果需要清理图片/PDF，可以取消注释
    print("\n💡 提示: 如果是想清除 Streamlit 内存中的 @st.cache，请直接在网页按 'C' 键或重启 Streamlit 进程。")

