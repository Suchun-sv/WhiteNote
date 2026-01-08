from __future__ import annotations
import time
from pathlib import Path
from typing import Iterable
import requests


class PdfDownloader:
    def __init__(
        self,
        save_dir: str | Path | None = None,
        timeout: int = 30,
        retries: int = 3,
        min_interval: int = 10,
    ):
        from ..config import Config
        self.save_dir = Path(save_dir or Config.pdf_save_path)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.timeout = timeout
        self.retries = retries
        self.min_interval = min_interval

    def _looks_like_pdf(self, content: bytes, content_type: str | None):
        """
        判断是不是 PDF，而不是 CAPTCHA HTML
        """
        if content.startswith(b"%PDF-"):
            return True

        if content_type and "application/pdf" in content_type.lower():
            return True

        return False

    def _download_one(self, url: str, file: Path):
        if file.suffix != ".pdf":
            file = file.with_suffix(".pdf")

        if file.exists():
            print(f"⏭ Skip (exists): {file.name}")
        else:
            tmp = file.with_suffix(file.suffix + ".part")
            if tmp.exists():
                tmp.unlink()

            for attempt in range(1, self.retries + 1):
                try:
                    print(f"⬇ Start [{attempt}/{self.retries}]: {url}")

                    r = requests.get(url, timeout=self.timeout, stream=True)
                    r.raise_for_status()

                    content_type = r.headers.get("Content-Type", "")

                    # 先把内容读入内存头几 KB
                    head = next(r.iter_content(chunk_size=1024 * 16))
                    
                    # 先判断是不是 PDF
                    if not self._looks_like_pdf(head, content_type):
                        print(f"🚫 Not a PDF (maybe CAPTCHA): {url}")
                        return

                    # 写入 .part
                    with tmp.open("wb") as f:
                        f.write(head)
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    tmp.rename(file)
                    print(f"✅ Saved PDF: {file.name}")
                    break

                except Exception as e:
                    print(f"⚠ Error [{attempt}/{self.retries}]: {url} | {e}")

                    if attempt == self.retries:
                        print(f"❌ Failed: {url}")
                        break

                    wait = max(self.min_interval, 2 ** attempt)
                    print(f"⏳ Retry in {wait}s...")
                    time.sleep(wait)

        print(f"⏱ Cooling {self.min_interval}s…\n")
        time.sleep(self.min_interval)
    
    def download_one(self, url: str, id: str):
        file = Path(self.save_dir) / f"{id}.pdf"
        self._download_one(url, file)

    def download_all(self, items: Iterable[tuple[str, str]]):
        items = list(items)
        if not items:
            print("📭 No download tasks.")
            return

        print(f"📥 Total tasks: {len(items)}\n")

        for url, name in items:
            file = Path(self.save_dir) / name
            self._download_one(url, file)