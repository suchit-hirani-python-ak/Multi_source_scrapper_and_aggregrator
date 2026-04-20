import asyncio
import httpx
import re
from urllib.parse import quote
from app.utils.job_control import is_cancelled, safe_complete, safe_progress, safe_stream
from app.utils.redishelper import RedisHelper


class WikipediaScraper:

    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.headers = {
            "User-Agent": "WikipediaScraper/1.0"
        }

    def _clean_snippet(self, snippet: str) -> str:
        return re.sub(r"<[^>]+>", "", snippet).strip()

    def _wiki_url(self, title: str) -> str:
        return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


    def _normalize_query(self, query: str) -> str:
        if not query:
            return ""

        query = query.strip()
        query = re.sub(r"\s+", " ", query)
        query = query.lower()

        return query

    async def fetch_one(self, client: httpx.AsyncClient, query: str) -> dict:
        try:
            original_query = query
            query = self._normalize_query(query)

            if not query:
                return {"query": original_query, "error": "Empty query"}

            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 1
            }

            resp = await client.get(self.base_url, params=search_params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("query", {}).get("search", [])
            if not results:
                return {"query": original_query, "error": "No result found"}

            top = results[0]
            title = top["title"]

            params = {
                "action": "query",
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "titles": title,
                "format": "json"
            }

            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            page = next(iter(pages.values()))

            return {
                "query": original_query,
                "title": title,
                "description": page.get("extract", "")[:],
                "link": self._wiki_url(title)
            }

        except Exception as e:
            return {"query": query, "error": str(e)}



async def wiki_scrape_logic(job_id, limit, categories, redis, site):

    scraper = WikipediaScraper()
    queries = categories if categories else []
    results = []

    async with httpx.AsyncClient(headers=scraper.headers, timeout=10.0) as client:

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
                await redis.update_job(job_id, "failed", 0, site, data={"error": str(e)})
                return []

    await safe_complete(redis, job_id, site)
    return results