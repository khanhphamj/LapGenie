import os
import logging
import datetime
import requests
import json
import time
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
from os import makedirs
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables with fallbacks
SRC_PATH = os.getenv("SRC_PATH", "https://www.thegioididong.com/laptop#c=44&o=13&pi=")
PRODUCT_INFO_NEED = int(os.getenv("PRODUCT_INFO_NEED", "400"))
PRODUCTS_IN_ONE_PAGE = int(os.getenv("PRODUCTS_IN_ONE_PAGE", "20"))
PREFIX_PRODUCT_URL = os.getenv("PREFIX_PRODUCT_URL", "https://www.thegioididong.com")
SLEEP_TIME = float(os.getenv("SLEEP_TIME", "0.5"))
# Use absolute path based on current file location for Airflow compatibility
SAVE_DIR = os.getenv("SAVE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def setup_logging():
    log_dir = os.path.join(SAVE_DIR, "logs")
    makedirs(log_dir, exist_ok=True)
    
    current_time = datetime.datetime.now()
    log_filename = os.path.join(log_dir, f"crawler_{current_time.strftime('%Y-%m-%d')}.log")
    
    # Configure logging format and level
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("TGDDCrawler")

# Current time for file naming
current_time = datetime.datetime.now()
current_time_str = current_time.strftime("%Y-%m-%d")

class TGDD_Crawler:
    def __init__(self, logger=None, max_workers=4):
        self.logger = logger or logging.getLogger("TGDDCrawler")
        self.max_workers = max_workers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        self.ignore = ['javascript:;']
        self.stats = {
            "start_time": None,
            "end_time": None,
            "successful_crawls": 0,
            "failed_crawls": 0,
            "total_crawl_attempts": 0
        }

    @staticmethod
    def run_playwright(playwright, url):
        try:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            content = page.content()
            browser.close()
            return content
        except Exception as e:
            logging.error(f"Playwright error for {url}: {e}")
            return None

    @staticmethod
    def get_html_playwright(url):
        try:
            with sync_playwright() as playwright:
                html = TGDD_Crawler.run_playwright(playwright, url)
                return html
        except Exception as e:
            logging.error(f"Failed to get HTML with Playwright for {url}: {e}")
            return None

    def _get_soup(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing {url}: {e}")
            return None

    def _crawl_link_product(self, url):
        self.logger.info(f"Crawling product links from {url}")
        
        try:
            html = TGDD_Crawler.get_html_playwright(url)
            if not html:
                self.logger.error(f"Failed to get HTML from {url}")
                return []
                
            soup = BeautifulSoup(html, 'html.parser')
            product_container = soup.find('div', class_='container-productbox')
            
            if not product_container:
                self.logger.warning(f"Product container not found on {url}")
                return []
                
            product_list = product_container.find('ul', class_='listproduct')
            
            if not product_list:
                self.logger.warning(f"Product list not found on {url}")
                return []
                
            links = []
            for item in product_list.find_all('a'):
                href = item.get('href')
                if href and href not in self.ignore:
                    links.append(href)
            
            self.logger.info(f"Found {len(links)} product links, limiting to {PRODUCT_INFO_NEED}")
            return links[:PRODUCT_INFO_NEED]
            
        except Exception as e:
            self.logger.error(f"Error crawling product links: {e}")
            return []

    def _extract_specs(self, box):
        """Extract specifications from a box element"""
        container = {}
        try:
            title_elem = box.find_next('a')
            if not title_elem:
                return None, {}
                
            title = title_elem.get_text().strip()
            
            ul = box.find_next('ul', class_="text-specifi")
            if not ul:
                return title, container
                
            for li in ul.find_all('li'):
                asides = li.find_all('aside')
                if len(asides) < 2:
                    continue
                    
                sub_title_elem = asides[0].find_next('strong')
                if not sub_title_elem:
                    continue
                    
                sub_title = sub_title_elem.get_text().strip()
                values = []
                
                for content in asides[1]:
                    if content == '\n':
                        continue
                    if hasattr(content, 'get_text'):
                        text = content.get_text().strip()
                        if text:
                            values.append(text)
                
                if values:
                    container[sub_title] = values
            
            return title, container
        except Exception as e:
            self.logger.error(f"Error extracting specs: {e}")
            return None, {}

    def _extract_description(self, soup, url):
        """Extract product description"""
        try:
            description_parts = []
            
            content_divs = soup.find_all('div', class_="text-detail")
            if not content_divs:
                self.logger.debug(f"No description divs found for {url}")
                return None
                
            for div in content_divs:
                # Get h3 headings
                for h3 in div.find_all('h3'):
                    text = h3.get_text().strip()
                    if text:
                        description_parts.append(text)

                # Get paragraphs
                for p in div.find_all('p'):
                    text = p.get_text().strip()
                    if text:
                        description_parts.append(text)

                # If no structured elements found, get all text
                if not div.find_all('h3') and not div.find_all('p'):
                    text = div.get_text().strip()
                    if text:
                        description_parts.append(text)

            return '\n'.join(description_parts) if description_parts else None
            
        except Exception as e:
            self.logger.error(f"Error extracting description for {url}: {e}")
            return None

    def _extract_price(self, soup, url):
        """Extract price information with better handling of price structure"""
        try:
            price = {}
            price_elem = soup.find('div', class_='box-price')
            
            if not price_elem:
                self.logger.debug(f"No price element found for {url}")
                return price
            
            # Look for direct children first
            price_present = price_elem.find('p', class_='box-price-present')
            price_old = price_elem.find('p', class_='box-price-old')
            price_percent = price_elem.find('p', class_='box-price-percent')
            
            # If not found directly, try iterating through children
            if not (price_present or price_old or price_percent):
                for child in price_elem.children:
                    if hasattr(child, 'find'):
                        child_present = child.find('p', class_='box-price-present')
                        child_old = child.find('p', class_='box-price-old')
                        child_percent = child.find('p', class_='box-price-percent')
                        
                        if child_present and not price_present:
                            price_present = child_present
                        if child_old and not price_old:
                            price_old = child_old
                        if child_percent and not price_percent:
                            price_percent = child_percent
            
            # Extract and clean text from elements
            if price_present:
                price['Giá hiện tại'] = price_present.get_text().strip()
                self.logger.debug(f"Found current price: {price['Giá hiện tại']}")
                
                # Extract price in millions for tagging
                extracted_price = self._extract_price_value(price['Giá hiện tại'])
                if extracted_price:
                    price['Giá trị'] = extracted_price
                    price['Phân khúc'] = self._determine_price_range(extracted_price)
                    price['Tag'] = self._determine_price_tag(price['Phân khúc'])
            
            if price_old:
                price['Giá cũ'] = price_old.get_text().strip()
                self.logger.debug(f"Found old price: {price['Giá cũ']}")
            
            if price_percent:
                price['Phần trăm giảm'] = price_percent.get_text().strip()
                self.logger.debug(f"Found discount percentage: {price['Phần trăm giảm']}")
                
            return price
            
        except Exception as e:
            self.logger.error(f"Error extracting price for {url}: {e}")
            return {}
    
    def _extract_price_value(self, price_text):
        """Extract price from text and convert to millions of VND"""
        # Tìm các số có định dạng tiền tệ như 15.990.000đ hoặc 15,990,000 ₫
        price_pattern = r'(\d{1,3}(?:[.,]\d{3})+)(?:\s*)(đ|₫|VND)'
        match = re.search(price_pattern, price_text, re.IGNORECASE)
        
        if match:
            # Lấy phần số và loại bỏ dấu phân cách
            price_str = match.group(1).replace('.', '').replace(',', '')
            try:
                # Chuyển đổi sang triệu
                price_in_millions = int(price_str) / 1000000
                return price_in_millions
            except:
                pass
        return None
    
    def _determine_price_range(self, price):
        """Xác định phân khúc giá dựa trên giá tiền (đơn vị: triệu VND)"""
        if price is None:
            return "Unknown"
        elif price < 10:
            return "Dưới 10 triệu"
        elif price < 15:
            return "10-15 triệu"
        elif price < 20:
            return "15-20 triệu" 
        elif price < 30:
            return "20-30 triệu"
        else:
            return "Trên 30 triệu"
    
    def _determine_price_tag(self, price_range):
        """Xác định tag giá dựa trên phân khúc giá"""
        price_tag_mapping = {
            "Dưới 10 triệu": "Giá rẻ",
            "10-15 triệu": "Giá tầm trung thấp",
            "15-20 triệu": "Giá tầm trung",
            "20-30 triệu": "Giá cao cấp",
            "Trên 30 triệu": "Giá cao cấp đặc biệt",
            "Unknown": "Không xác định"
        }
        return price_tag_mapping.get(price_range, "Không xác định")

    def _crawl_product_info(self, url):
        """Crawl information for a single product"""
        self.stats["total_crawl_attempts"] += 1
        
        try:
            self.logger.debug(f"Crawling product info from {url}")
            res = {}
            
            soup = self._get_soup(url)
            if not soup:
                self.stats["failed_crawls"] += 1
                return res

            # Extract product details
            for box in soup.find_all('div', class_='box-specifi'):
                title, container = self._extract_specs(box)
                if title and container:
                    res[title] = container

            # Extract product description
            description = self._extract_description(soup, url)
            if description:
                res["Mô tả chi tiết"] = description

            # Extract price information
            price = self._extract_price(soup, url)
            if price:
                res["Giá"] = price

            # Add brand and product name
            try:
                # Extract full product path (e.g., /laptop/asus-vivobook-go-15-e1504fa-r5-nj776w)
                product_path = "/".join(url.split("/")[-2:])
                
                # For brand extraction, still use just the last part
                product_name = url.split("/")[-1]
                brand = product_name.split("-")[0]
                if brand == "macbook":
                    brand = "apple"
                
                res["Hãng"] = brand.upper()
                res["Tên máy"] = product_name  # Use the full path here
                res["URL"] = url  # Also store the complete URL
            except Exception as e:
                self.logger.error(f"Error processing product name for {url}: {e}")

            self.stats["successful_crawls"] += 1
            return res
            
        except Exception as e:
            self.logger.error(f"Unexpected error crawling {url}: {e}")
            self.stats["failed_crawls"] += 1
            return {}

    def _crawl_products_info_parallel(self, urls):
        """Crawl multiple products in parallel using ThreadPoolExecutor"""
        products = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create a dictionary mapping futures to their URLs
            future_to_url = {
                executor.submit(self._crawl_single_product, url): url 
                for url in urls
            }
            
            # Track progress with tqdm
            for future in tqdm(
                future_to_url, 
                desc="Crawling products", 
                unit="product",
                ncols=100
            ):
                url = future_to_url[future]
                try:
                    result = future.result()
                    products[url] = result
                except Exception as e:
                    self.logger.error(f"Error processing result for {url}: {e}")
                    self.stats["failed_crawls"] += 1
                    products[url] = {}
                
                # Respect the rate limit
                time.sleep(SLEEP_TIME)
                
        return products

    def _crawl_single_product(self, url):
        """Handle a single product crawl with appropriate URL prefix"""
        full_url = PREFIX_PRODUCT_URL + url if not url.startswith(PREFIX_PRODUCT_URL) else url
        return self._crawl_product_info(full_url)

    def _crawl_products_info(self, url):
        """Crawl information for all products"""
        self.logger.info("Starting to crawl product information")
        self.stats["start_time"] = time.time()
        
        # Get product links
        urls = self._crawl_link_product(url)
        
        if not urls:
            self.logger.error("No product URLs found to crawl")
            return {}
            
        self.logger.info(f"Found {len(urls)} products to crawl")
        
        # Use parallel crawling for better performance
        products = self._crawl_products_info_parallel(urls)
        
        self.stats["end_time"] = time.time()
        return products

    def _save_data(self, data):
        """Save the crawled data to a JSON file"""
        try:
            makedirs(SAVE_DIR, exist_ok=True)
            file_path = os.path.join(SAVE_DIR, f"laptop-{current_time_str}.json")
            
            self.logger.info(f"Saving {len(data)} products to {file_path}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Data successfully saved to {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return None

    def _print_stats(self):
        """Print crawler statistics"""
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]
            success_rate = (self.stats["successful_crawls"] / self.stats["total_crawl_attempts"]) * 100 if self.stats["total_crawl_attempts"] > 0 else 0
            
            self.logger.info("=" * 50)
            self.logger.info("CRAWLER STATISTICS")
            self.logger.info("=" * 50)
            self.logger.info(f"Total crawl time: {duration:.2f} seconds")
            self.logger.info(f"Total products attempted: {self.stats['total_crawl_attempts']}")
            self.logger.info(f"Successfully crawled: {self.stats['successful_crawls']}")
            self.logger.info(f"Failed crawls: {self.stats['failed_crawls']}")
            self.logger.info(f"Success rate: {success_rate:.2f}%")
            self.logger.info("=" * 50)

    def run(self):
        """Run the crawler with proper logging and statistics"""
        start_time = time.time()
        self.logger.info("Starting TGDD crawler process")
        
        # Calculate the URL based on number of pages needed
        page_needed = (PRODUCT_INFO_NEED + PRODUCTS_IN_ONE_PAGE - 1) // PRODUCTS_IN_ONE_PAGE
        url = SRC_PATH + str(page_needed)
        self.logger.info(f"Target URL: {url}")
        
        try:
            # Crawl and save data
            data = self._crawl_products_info(url)
            saved_file = self._save_data(data)
            
            # Print statistics
            self._print_stats()
            
            total_time = time.time() - start_time
            self.logger.info(f"Crawler completed in {total_time:.2f} seconds")
            
            if saved_file:
                return saved_file
            return None
            
        except Exception as e:
            self.logger.error(f"Critical error in crawler execution: {e}", exc_info=True)
            return None


def main():
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting crawler at {current_time_str}")
    
    try:
        # Create and run the crawler
        crawler = TGDD_Crawler(logger=logger)
        saved_file = crawler.run()
        
        if saved_file:
            logger.info(f"Crawler successfully completed. Data saved to {saved_file}")
        else:
            logger.error("Crawler failed to save data")
            
    except Exception as e:
        logger.error(f"Unhandled exception in crawler main: {e}", exc_info=True)


if __name__ == "__main__":
    main()