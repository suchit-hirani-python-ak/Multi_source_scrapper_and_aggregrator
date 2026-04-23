import re
import yfinance as yf
from app.utils.job_control import is_cancelled, safe_stream, safe_progress, safe_complete

class YahooFinanceScraper:
    def __init__(self):
        pass

    def _normalize_query(self, query):
        return re.sub(r"\s+", " ", query.strip()) if query else ""

    def _resolve_ticker(self, query):
        
        try:
            
            search = yf.Search(query, max_results=1)
            if search.quotes and len(search.quotes) > 0:
                return search.quotes[0]['symbol']
        except Exception:
            pass
        return query.upper()

    def scrape(self, query):
        try:
            original_query = query
            normalized = self._normalize_query(query)

            if not normalized:
                return {"query": original_query, "error": "Empty query"}

            ticker_symbol = self._resolve_ticker(normalized)
            
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            if not info or 'symbol' not in info:
                return {"query": original_query, "error": f"Could not find data for '{ticker_symbol}'"}

            def fmt(val):
                return val if val is not None else "N/A"

            return {
                "query": original_query,

                "ticker": info.get("symbol"),
                "company_name": info.get("longName") or info.get("shortName", "N/A"),

                "price": fmt(info.get("currentPrice") or info.get("regularMarketPrice")),
                "change": fmt(info.get("regularMarketChange")),
                "change_percent": fmt(info.get("regularMarketChangePercent")),
                "previous_close": fmt(info.get("previousClose")),
                "open": fmt(info.get("open")),
                "day_range": f"{fmt(info.get('dayLow'))} - {fmt(info.get('dayHigh'))}",
                "52_week_range": f"{fmt(info.get('fiftyTwoWeekLow'))} - {fmt(info.get('fiftyTwoWeekHigh'))}",
                "volume": fmt(info.get("volume")),
                "avg_volume": fmt(info.get("averageVolume")),
                "market_cap": fmt(info.get("marketCap")),
                "pe_ratio": fmt(info.get("trailingPE")),
                "eps": fmt(info.get("trailingEps")),
                "beta": fmt(info.get("beta")),
                "dividend_yield": f"{fmt(info.get('dividendRate'))} ({fmt(info.get('dividendYield'))})",
                "ex_dividend_date": fmt(info.get("exDividendDate")),
                "target_estimate_1y": fmt(info.get("targetMeanPrice")),
                "url": f"https://yahoo.com{info.get('symbol')}"
            }

        except Exception as e:
            return {"query": query, "error": str(e)}

    def close(self):
        pass


async def yahoo_scrape_logic(job_id, limit, categories, redis, site):
    scraper = YahooFinanceScraper()
    
    queries = list(dict.fromkeys(categories)) if categories else []
    
    results = []
    processed_tickers = set()
    batch_size = 5 

    try:
        for i in range(0, len(queries), batch_size):
            if await is_cancelled(redis, job_id):
                return results

            chunk = queries[i:i + batch_size]
            batch = []

            for q in chunk:
                res = scraper.scrape(q)
                
                if res and "ticker" in res:
                    ticker = res["ticker"]
                    if ticker in processed_tickers:
                        continue
                    
                    processed_tickers.add(ticker)
                    results.append(res)
                    batch.append(res)
                elif res: 
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
        if redis:
            await redis.update_job(job_id, "failed", 0, site, data={"error": str(e)})
        return []
    finally:
        scraper.close()
