from datetime import datetime, timedelta
import asyncio

from src.crawler.arxiv_client import ArxivClient
from src.storage.json_store import JsonStore
from src.service.pdf_download_service import PdfDownloader
from src.config import Config


async def main():
    print("🌿 LavenderSentinel — ArXiv Fetch Running...")

    crawler = ArxivClient()

    keywords = ["vector database", "RAG", "agent"]

    keywords_papers = crawler.search_papers(
        keywords=keywords,
        # date_range=(datetime.now() - timedelta(days=30), datetime.now())
    )

    store = JsonStore(Config.paper_save_path)
    downloader = PdfDownloader(Config.pdf_save_path)

    total_added = 0
    download_items = []

    for kw, papers in keywords_papers.items():
        added_papers = store.insert_new_papers(papers)
        total_added += len(added_papers)

        print(f"📌 Keyword='{kw}' Found={len(papers)} New={len(added_papers)}")
        download_items.extend([(p.pdf_url, f"{p.id}.pdf") for p in papers if p.pdf_url])


    print(f"\n📚 Total new papers = {total_added}")
    await downloader.download_all(download_items)
    print("✅ PDF download complete")


if __name__ == "__main__":
    asyncio.run(main())