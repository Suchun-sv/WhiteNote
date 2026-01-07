from datetime import datetime, timedelta
from src.crawler import ArxivClient
from src.storage import JsonStore
from src.config import Config

if __name__ == "__main__":
    crawler = ArxivClient()
    keywords = ["vector database", "RAG", "agent"]
    keywords_papers = crawler.search_papers(keywords=keywords, date_range=(datetime.now() - timedelta(days=30), datetime.now()))
    json_store = JsonStore(Config.paper_save_path)
    keyword_papers_count = 0
    for keyword, papers in keywords_papers.items():
        keyword_papers_count_current = json_store.insert_new_papers(papers)
        keyword_papers_count += keyword_papers_count_current
        print(f"Keyword: {keyword}, Papers: {keyword_papers_count_current}")
    print(f"Total papers: {keyword_papers_count}")