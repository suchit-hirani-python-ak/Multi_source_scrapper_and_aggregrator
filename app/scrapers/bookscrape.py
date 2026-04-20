import httpx
from bs4 import BeautifulSoup
from app.utils.redishelper import RedisHelper
from app.utils.job_control import is_cancelled, safe_stream, safe_progress, safe_complete

BASE_URL = "https://books.toscrape.com/"


async def get_all_categories(client: httpx.AsyncClient) -> dict:
    resp = await client.get(BASE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    category_list = soup.select(".side_categories ul ul li a")

    return {
        cat.text.strip().lower(): BASE_URL + cat["href"]
        for cat in category_list
    }


async def book_scrape_logic(job_id: str, limit: int, categories: list, redis: RedisHelper, site: str):
    results = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        all_categories = await get_all_categories(client)

        for category in categories:
            if await is_cancelled(redis, job_id):
                return results

            category = category.lower()
            if category not in all_categories:
                continue

            current_url = all_categories[category]

            while len(results) < limit:

                if await is_cancelled(redis, job_id):
                    return results

                try:
                    resp = await client.get(current_url)
                    if resp.status_code != 200:
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    books = soup.select(".product_pod")

                    if not books:
                        break

                    batch = []

                    for b in books:
                        if len(results) >= limit:
                            break

                        item = {
                            "title": b.h3.a["title"],
                            "price": b.select_one(".price_color").text,
                            "instock": "In stock" in b.select_one(".availability").text,
                            "rating": b.select_one(".star-rating")["class"][1],
                            "category": category
                        }

                        batch.append(item)
                        results.append(item)

                    if not await safe_stream(redis, job_id, batch):
                        return results

                    progress = int((len(results) / limit) * 100)
                    if not await safe_progress(redis, job_id, min(progress, 99), site):
                        return results

                    next_btn = soup.select_one(".next a")
                    if next_btn:
                        current_url = current_url.rsplit("/", 1)[0] + "/" + next_btn["href"]
                    else:
                        break

                except Exception as e:
                    await redis.update_job(job_id, "failed", 0, site, data={"error": str(e)})
                    return []

            if len(results) >= limit:
                break

    await safe_complete(redis, job_id, site)
    return results