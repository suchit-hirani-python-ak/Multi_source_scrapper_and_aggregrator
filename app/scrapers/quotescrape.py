import httpx
from bs4 import BeautifulSoup
from app.utils.redishelper import RedisHelper

async def run_scrape_logic(job_id: str, limit: int, tags: list, redis: RedisHelper, site: str):
    base_url = "https://quotes.toscrape.com" 
    results = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for tag in tags:
            page = 1
            # Continue fetching while under the limit
            while len(results) < limit:
                url = f"{base_url}/tag/{tag}/page/{page}/"
                
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200: 
                        break # Stop if page does not exist
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    quotes = soup.find_all("div", class_="quote")
                    
                    if not quotes: 
                        break # Stop if no quotes found
                    
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
                    print(f"WORKER DEBUG: Scraping Page {page} for Tag {tag}")
                    # Live updates for frontend
                    await redis.append_to_stream(job_id, batch)
                    progress_pct = int((len(results) / limit) * 100)
                    await redis.update_job(job_id, "running", min(progress_pct, 99), site=site)
                    
                    # FIX: Check if a "Next" button exists to continue to the next page
                    if not soup.find("li", class_="next"):
                        break
                        
                    page += 1 # Move to the next page number
                    
                except Exception as e:
                    await redis.update_job(job_id, "failed", 0, site=site,data={"error": str(e)})
                    return []
            
            if len(results) >= limit: 
                break

    await redis.update_job(job_id, "completed", 100, site=site)
    return results
