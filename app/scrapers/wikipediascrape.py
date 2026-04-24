import asyncio
import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import quote
from app.utils.job_control import is_cancelled, safe_complete, safe_progress, safe_stream


class WikipediaScraper:

    def __init__(self):
        self.base_url = "https://en.wikipedia.org/wiki/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _normalize_query(self, query: str) -> str:
        if not query:
            return ""
        query = query.strip()
        query = re.sub(r"\s+", " ", query)
        return query.replace(" ", "_")

    def _wiki_url(self, title: str) -> str:
        return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

    async def fetch_one(self, client: httpx.AsyncClient, query: str) -> dict:
        try:
            original_query = query
            normalized = self._normalize_query(query)

            if not normalized:
                return {"query": original_query, "error": "Empty query"}

            url = f"{self.base_url}{quote(normalized)}"
            resp = await client.get(url, follow_redirects=True)
            
            if resp.status_code != 200:
                return {"query": original_query, "error": f"Page not found (Status {resp.status_code})"}

            soup = BeautifulSoup(resp.text, 'html.parser')

            title_tag = soup.find(id="firstHeading")
            title = title_tag.get_text() if title_tag else query

            content_div = soup.find(id="mw-content-text")
            description = ""
            
            if content_div:
                paragraphs = content_div.find_all('p')
                for p in paragraphs:
                    text = re.sub(r'\[\d+\]', '', p.get_text()).strip()
                    if len(text) > 20: # Ensure it's a real sentence, not a tiny snippet
                        description = text
                        break

            return {
                "query": original_query,
                "title": title,
                "description": description if description else "No description found.",
                "link": str(resp.url)
            }

        except Exception as e:
            return {"query": query, "error": str(e)}


async def wiki_scrape_logic(job_id, limit, categories, redis, site):
    scraper = WikipediaScraper()
    queries = categories if categories else []
    results = []

    async with httpx.AsyncClient(headers=scraper.headers, timeout=20.0) as client:

        batch_size = 5

        for i in range(0, len(queries), batch_size):

            if await is_cancelled(redis, job_id):
                return results

            chunk = queries[i:i + batch_size]

            try:
                tasks = [scraper.fetch_one(client, q) for q in chunk]
                responses = await asyncio.gather(*tasks)

                batch = []
                for res in responses:
                    if res:
                        results.append(res)
                        batch.append(res)

                if not await safe_stream(redis, job_id, batch):
                    return results

                progress = int((len(results) / len(queries)) * 100) if queries else 100

                if not await safe_progress(redis, job_id, min(progress, 99), site):
                    return results

            except Exception as e:
                if redis:
                    await redis.update_job(job_id, "failed", 0, site, data={"error": str(e)})
                return []

    await safe_complete(redis, job_id, site)
    return results