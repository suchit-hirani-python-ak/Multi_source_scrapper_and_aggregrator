import time
import re
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from app.utils.job_control import is_cancelled, safe_stream, safe_progress, safe_complete

class YahooFinanceScraper:

    def __init__(self, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)


    def _normalize_query(self, query):
        return re.sub(r"\s+", " ", query.strip().lower()) if query else ""

    def _search_and_navigate(self, query):
        self.driver.get("https://finance.yahoo.com/")

        try:
            search_box = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "p"))
            )
        except TimeoutException:
            return query.upper()

        search_box.clear()
        search_box.send_keys(query)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)

        try:
            ticker = self.driver.current_url.split("/quote/")[1].split("/")[0]
        except:
            ticker = query.upper()

        return ticker

    def _extract_price(self):
        data = {}

        fields = {
            "price": 'fin-streamer[data-field="regularMarketPrice"]',
            "change": 'fin-streamer[data-field="regularMarketChange"]',
            "change_percent": 'fin-streamer[data-field="regularMarketChangePercent"]',
        }

        for key, selector in fields.items():
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                value = el.get_attribute("value") or el.text.strip()
                data[key] = value if value else "N/A"
            except:
                data[key] = "N/A"

        return data


    def _extract_summary(self):
        data = {}

        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "ul li")

            for row in rows:
                try:
                    label = row.find_element(By.CSS_SELECTOR, "span.label").text.strip()
                    value = row.find_element(By.CSS_SELECTOR, "span.value").text.strip()

                    if label and value:
                        data[label] = value

                except:
                    continue

        except:
            pass

        return data

    def scrape(self, query):
        try:
            original_query = query
            query = self._normalize_query(query)

            if not query:
                return {"query": original_query, "error": "Empty query"}

            # resolve ticker
            ticker = self._search_and_navigate(query)
            url = self.driver.current_url

            if "/quote/" not in url:
                return {"query": original_query, "error": "No result found"}

            # wait for page
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)

            # extract
            price = self._extract_price()
            summary = self._extract_summary()

            def get(label):
                return summary.get(label, "N/A")

            return {
                "query": original_query,
                "ticker": ticker,
                "company_name": self.driver.find_element(By.CSS_SELECTOR, "h1").text.strip(),

                "price": price["price"],
                "change": price["change"],
                "change_percent": price["change_percent"],
                "previous_close": get("Previous Close"),
                "open": get("Open"),
                "day_range": get("Day's Range"),
                "52_week_range": get("52 Week Range"),
                "volume": get("Volume"),
                "avg_volume": get("Avg. Volume"),
                "market_cap": get("Market Cap (intraday)") or get("Market Cap"),
                "pe_ratio": get("PE Ratio (TTM)"),
                "eps": get("EPS (TTM)"),
                "beta": get("Beta (5Y Monthly)"),
                "dividend_yield": get("Forward Dividend & Yield"),
                "ex_dividend_date": get("Ex-Dividend Date"),
                "earnings_date": get("Earnings Date"),

                "target_estimate_1y": get("1y Target Est"),
                "url": url
            }

        except Exception as e:
            return {"query": query, "error": str(e)}

    def close(self):
        self.driver.quit()


async def yahoo_scrape_logic(job_id, limit, categories, redis, site):

    scraper = YahooFinanceScraper()
    queries = categories if categories else []
    results = []

    batch_size = 2

    try:
        for i in range(0, len(queries), batch_size):

            if await is_cancelled(redis, job_id):
                return results

            chunk = queries[i:i + batch_size]
            batch = []

            for q in chunk:
                res = scraper.scrape(q)
                if res:
                    results.append(res)
                    batch.append(res)

            if not await safe_stream(redis, job_id, batch):
                return results

            progress = int((len(results) / len(queries)) * 100) if queries else 100

            if not await safe_progress(redis, job_id, min(progress, 99), site):
                return results

        await safe_complete(redis, job_id, site)
        return results

    except Exception as e:
        await redis.update_job(job_id, "failed", 0, site, data={"error": str(e)})
        return []

    finally:
        scraper.close()