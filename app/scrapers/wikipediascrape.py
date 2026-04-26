import asyncio
import httpx
import re
from urllib.parse import quote
from app.utils.job_control import is_cancelled, safe_complete, safe_progress, safe_stream


class WikipediaScraper:

    def __init__(self):
        self.search_url = "https://en.wikipedia.org/w/api.php"

    def _normalize_query(self, query: str) -> str:
        if not query:
            return ""
        return re.sub(r"\s+", " ", query.strip()).lower()

    def _clean_snippet(self, text: str) -> str:
        text = re.sub(r"<.*?>", "", text)
        text = re.sub(r"\[\d+\]", "", text)
        return text.strip()

    def _wiki_url(self, title: str) -> str:
        return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

    async def fetch_one(self, client: httpx.AsyncClient, query: str) -> dict:
        try:
            original_query = query
            normalized = self._normalize_query(query)

            if not normalized:
                return {"query": original_query, "title": "", "description": "", "link": ""}

            # 🔹 STEP 1: search API
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": normalized,
                "format": "json"
            }

            search_resp = await client.get(self.search_url, params=search_params)
            search_data = search_resp.json()

            search_results = search_data.get("query", {}).get("search", [])
            if not search_results:
                return {"query": original_query, "title": "", "description": "", "link": ""}

            title = search_results[0]["title"]

            # 🔹 STEP 2: extract API
            extract_params = {
                "action": "query",
                "prop": "extracts",
                "explaintext": True,
                "titles": title,
                "format": "json"
            }

            extract_resp = await client.get(self.search_url, params=extract_params)
            extract_data = extract_resp.json()

            pages = extract_data.get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})

            description = page.get("extract", "")

            return {
                "query": original_query,
                "title": title,
                "description": description,
                "link": self._wiki_url(title)
            }

        except Exception as e:
            return {"query": query, "title": "", "description": "", "link": ""}


async def wiki_scrape_logic(job_id, limit, categories, redis, site):
    scraper = WikipediaScraper()
    queries = categories or []
    results = []

    async with httpx.AsyncClient(timeout=20.0) as client:

        for i in range(0, len(queries), 5):

            if await is_cancelled(redis, job_id):
                return results

            chunk = queries[i:i + 5]

            try:
                tasks = [scraper.fetch_one(client, q) for q in chunk]
                responses = await asyncio.gather(*tasks)

                batch = []
                for res in responses:
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