#!/usr/bin/env python3

import cloudscraper
from bs4 import BeautifulSoup
import time
import random
import logging
from typing import Optional, Dict, List, Any
import re
from urllib.parse import urljoin, urlparse
import json
from functools import wraps


class RateLimiter:
    def __init__(self, min_delay: float = 3.0, max_delay: float = 7.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request = 0

    def wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request

        delay = random.uniform(self.min_delay, self.max_delay)

        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logging.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request = time.time()


class SessionManager:
    def __init__(self, timeout: int = 30):
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.timeout = timeout
        self.rate_limiter = RateLimiter()

        logging.info("Initialized SessionManager with cloudscraper")

    def _update_headers(self):
        pass

    def get(self, url: str, max_retries: int = 2, **kwargs):
        self.rate_limiter.wait()

        for attempt in range(max_retries + 1):
            try:
                logging.info(f"Requesting: {url}")
                response = self.session.get(url, timeout=self.timeout, **kwargs)

                if response.status_code == 200:
                    logging.debug(f"✅ Success: {url} ({len(response.content)} bytes)")
                    return response
                elif response.status_code == 403:
                    logging.warning(f"Access denied (403) for {url} - cloudscraper may need update")
                    return None
                elif response.status_code == 429:
                    logging.warning(f"Rate limited (429) for {url}")
                    if attempt < max_retries:
                        time.sleep(30)
                        continue
                    return None
                else:
                    logging.warning(f"HTTP {response.status_code} for {url}")
                    if attempt < max_retries and response.status_code >= 500:
                        time.sleep(10)
                        continue
                    return None

            except Exception as e:
                logging.error(f"Request failed for {url}: {e}")
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                return None

        return None

    def close(self):
        self.session.close()


def retry(max_attempts: int = 3, delay: float = 1.0):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logging.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    else:
                        logging.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                        time.sleep(delay * (attempt + 1))
            return None

        return wrapper

    return decorator


class DataCleaner:
    @staticmethod
    def clean_text(text: Optional[str]) -> Optional[str]:
        if not text:
            return None

        cleaned = re.sub(r'\s+', ' ', text.strip())

        if not cleaned:
            return None

        return cleaned

    @staticmethod
    def extract_number_from_text(text: Optional[str]) -> Optional[float]:
        if not text:
            return None

        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None

        return None

    @staticmethod
    def parse_employee_count(text: Optional[str]) -> Optional[str]:
        if not text:
            return None

        text = text.lower().strip()

        patterns = [
            r'(\d+)\s*-\s*(\d+)\s*employees?',
            r'(\d+)\+?\s*employees?',
            r'(\d+)\s*-\s*(\d+)\s*people',
            r'(\d+)\+?\s*people',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)}-{match.group(2)} employees"
                else:
                    return f"{match.group(1)}+ employees"

        return DataCleaner.clean_text(text)

    @staticmethod
    def parse_date_range(text: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not text:
            return None, None

        date_pattern = r'([A-Za-z]+ \d{4})\s*[-–—]\s*([A-Za-z]+ \d{4})'
        match = re.search(date_pattern, text)

        if match:
            return match.group(1), match.group(2)

        single_date_pattern = r'([A-Za-z]+ \d{4})'
        match = re.search(single_date_pattern, text)

        if match:
            return match.group(1), None

        return None, None

    @staticmethod
    def parse_project_size(text: Optional[str]) -> Optional[str]:
        if not text:
            return None

        text = text.strip()

        money_pattern = r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?'
        match = re.search(money_pattern, text)

        if match:
            return match.group(0)

        return DataCleaner.clean_text(text)


def setup_logging(log_file: str = 'clutch_scraper.log', level: int = logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def validate_url(url: str, base_domain: str = 'clutch.co') -> bool:
    try:
        parsed = urlparse(url)
        return base_domain in parsed.netloc
    except:
        return False


def extract_company_id_from_url(url: str) -> Optional[str]:
    if not url:
        return None

    match = re.search(r'/profile/([^/?]+)', url)
    if match:
        return match.group(1)

    return None


def build_company_url(company_id: str) -> str:
    return f"https://clutch.co/profile/{company_id}"


def parse_pagination_info(soup: BeautifulSoup) -> Dict[str, Any]:
    pagination_info = {
        'current_page': 1,
        'total_pages': 1,
        'has_next': False,
        'next_url': None
    }

    try:
        pagination = soup.find('nav', class_=lambda x: x and 'pagination' in x.lower())

        if pagination:
            current = pagination.find('span', class_=lambda x: x and 'current' in x.lower())
            if current:
                pagination_info['current_page'] = int(current.get_text(strip=True))

            next_link = pagination.find('a', string=lambda x: x and 'next' in x.lower())
            if next_link and next_link.get('href'):
                pagination_info['has_next'] = True
                pagination_info['next_url'] = urljoin('https://clutch.co', next_link['href'])

    except Exception as e:
        logging.warning(f"Error parsing pagination: {e}")

    return pagination_info


if __name__ == "__main__":
    setup_logging()

    print("Testing data cleaning utilities...")

    test_cases = [
        ("4.8 out of 5 stars", "score extraction"),
        ("50-100 employees", "employee count"),
        ("Jan 2023 - Jun 2023", "date range"),
        ("$50,000 - $100,000", "project size"),
        ("  Extra   whitespace  text  ", "text cleaning"),
    ]

    cleaner = DataCleaner()

    for text, description in test_cases:
        print(f"\n{description}: '{text}'")
        print(f"  Cleaned text: {cleaner.clean_text(text)}")
        print(f"  Number extraction: {cleaner.extract_number_from_text(text)}")
        print(f"  Employee count: {cleaner.parse_employee_count(text)}")
        print(f"  Date range: {cleaner.parse_date_range(text)}")
        print(f"  Project size: {cleaner.parse_project_size(text)}")

    print("\nUtilities test completed.")