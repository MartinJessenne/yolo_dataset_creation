# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "crawl4ai>=0.4.0",
#     "playwright",
# ]
# ///

import asyncio
import os
import sys
import subprocess
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def ensure_playwright_browsers():
    if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")):
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

def should_crawl_url(url: str) -> bool:
    """
    Strictest filter possible:
    Only crawls children if they belong exactly to the specified paths.
    """
    parsed = urlparse(url)
    path = parsed.path
    
    # Track 1: Isaac Sim Replicator Tutorials
    if parsed.netloc == "docs.isaacsim.omniverse.nvidia.com":
        if path.startswith("/latest/replicator_tutorials"):
            return True
            
    # Track 2: Omniverse Extension Replicator Core
    elif parsed.netloc == "docs.omniverse.nvidia.com":
        if path.startswith("/extensions/latest/ext_replicator"):
            return True
            
    return False

async def main():
    ensure_playwright_browsers()

    # The clean starting roots
    to_visit = {
        "https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/index.html",
        "https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html"
    }
    
    browser_config = BrowserConfig(headless=True, extra_args=["--no-sandbox"])
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="div[role='main'], article"  # Main content only (no sidebars)
    )
    
    output_dir = "replicator_latest_docs"
    os.makedirs(output_dir, exist_ok=True)
    
    visited = set()
    
    print("🚀 Initiating strict-scope Replicator documentation crawler...")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while to_visit:
            current_batch = list(to_visit - visited)
            to_visit.clear()  # Reset for next depth layer
            
            if not current_batch:
                break
                
            print(f"\n📡 Processing batch of {len(current_batch)} pages...")
            results = await crawler.arun_many(urls=current_batch, config=run_config)
            
            for result in results:
                if not result.success:
                    continue
                
                visited.add(result.url)
                
                # Format clean filenames
                parsed_url = urlparse(result.url)
                sub_namespace = "isaacsim" if "isaacsim" in parsed_url.netloc else "omniverse"
                path_parts = parsed_url.path.strip("/").split("/")
                
                # Build filename dropping 'latest' or 'extensions' to keep it concise
                clean_parts = [p for p in path_parts if p not in ["latest", "extensions"]]
                filename = f"{sub_namespace}_{'_'.join(clean_parts)}".replace(".html", "") + ".md"
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"---\nsource: {result.url}\n---\n\n")
                    f.write(result.markdown)
                print(f"✓ Saved: {filename}")
                
                # Recursive discovery filter
                for link in result.links.get("internal", []):
                    href = link.get("href")
                    if href:
                        # Drop fragment anchors (#heading) and queries
                        full_url = urljoin(result.url, href).split('#')[0].split('?')[0]
                        
                        if should_crawl_url(full_url) and full_url not in visited:
                            to_visit.add(full_url)

    print(f"\n✨ Extraction complete! Clean markdown files saved to: '{output_dir}/'")

if __name__ == "__main__":
    if sys.platform == 'linux':
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    asyncio.run(main())