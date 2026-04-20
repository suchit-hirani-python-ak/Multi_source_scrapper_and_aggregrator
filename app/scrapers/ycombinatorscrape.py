import httpx
from bs4 import BeautifulSoup
from app.utils.redishelper import RedisHelper
from app.utils.job_control import is_cancelled, safe_stream, safe_progress, safe_complete

HN_CATEGORIES = {
    "top": "news",
    "newest": "newest",
    "ask": "ask",
    "show": "show",
    "jobs": "jobs",
    "best": "best",
    "comments":"newcomments"
}

async def ycombinator_scrape_logic(job_id, limit, categories, redis, site):

    base_url = "https://news.ycombinator.com/"
    results = []

    async with httpx.AsyncClient(timeout=10.0) as client:

        for category in categories:

            if await is_cancelled(redis, job_id):
                return results

            category = category.lower()
            path = HN_CATEGORIES.get(category, "news")
            current_url = f"{base_url}{path}"

            while len(results) < limit:

                if await is_cancelled(redis, job_id):
                    return results

                try:
                    resp = await client.get(current_url)
                    if resp.status_code != 200:
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    rows = soup.find_all("tr", class_="athing")

                    if not rows:
                        break

                    batch = []

                    for row in rows:
                        if len(results) >= limit:
                            break

                        title_line = row.find("span", class_="titleline")
                        if not title_line:
                            continue

                        title_elem = title_line.find("a")
                        rank_el = row.find("span", class_="rank")

                        meta = row.find_next_sibling("tr")
                        score = meta.find("span", class_="score") if meta else None
                        user = meta.find("a", class_="hnuser") if meta else None

                        item = {
                            "rank": rank_el.text.strip(".") if rank_el else None,
                            "title": title_elem.text,
                            "url": title_elem["href"],
                            "points": score.text if score else "0",
                            "author": user.text if user else "N/A",
                            "category": category
                        }

                        batch.append(item)
                        results.append(item)

                    if not await safe_stream(redis, job_id, batch):
                        return results

                    progress = int((len(results) / limit) * 100)

                    if not await safe_progress(redis, job_id, min(progress, 99), site):
                        return results

                    more = soup.find("a", class_="morelink")
                    if more and len(results) < limit:
                        current_url = base_url + more["href"]
                    else:
                        break

                except Exception as e:
                    await redis.update_job(job_id, "failed", 0, site, data={"error": str(e)})
                    return []

    await safe_complete(redis, job_id, site)
    return results