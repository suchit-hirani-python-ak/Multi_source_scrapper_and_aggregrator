import httpx
from bs4 import BeautifulSoup
from app.utils.redishelper import RedisHelper
from app.utils.job_control import is_cancelled, safe_stream, safe_progress, safe_complete


async def quote_scrape_logic(job_id: str, limit: int, tags: list, redis: RedisHelper, site: str):
    base_url = "https://quotes.toscrape.com"
    results = []

    async with httpx.AsyncClient(timeout=10.0) as client:

        for tag in tags:
            page = 1

            while len(results) < limit:

                if await is_cancelled(redis, job_id):
                    return results

                url = f"{base_url}/tag/{tag}/page/{page}/"

                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    quotes = soup.find_all("div", class_="quote")

                    if not quotes:
                        break

                    batch = []

                    for q in quotes:
                        if len(results) >= limit:
                            break

                        text_el = q.find("span", class_="text")
                        author_el = q.find("small", class_="author")

                        if text_el and author_el:
                            item = {
                                "author": author_el.get_text(strip=True),
                                "text": text_el.get_text(strip=True).strip("“”")
                            }
                            batch.append(item)
                            results.append(item)

                    if not await safe_stream(redis, job_id, batch):
                        return results

                    progress = int((len(results) / limit) * 100)
                    if not await safe_progress(redis, job_id, min(progress, 99), site):
                        return results

                    if not soup.find("li", class_="next"):
                        break

                    page += 1

                except Exception as e:
                    await redis.update_job(job_id, "failed", 0, site, data={"error": str(e)})
                    return []

            if len(results) >= limit:
                break

    await safe_complete(redis, job_id, site)
    return results