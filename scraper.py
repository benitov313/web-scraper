

import logging
from typing import List, Optional, Dict, Generator
from bs4 import BeautifulSoup, Tag
import re
from urllib.parse import urljoin, urlparse
import time
import json

from models import ScrapedData, CompetitorInfo, ReviewerInfo, ProjectInfo, DEVELOPMENT_SUBCATEGORIES
from utils import SessionManager, DataCleaner, retry, validate_url, extract_company_id_from_url, parse_pagination_info

class ClutchScraper:
    def __init__(self, max_pages_per_category: int = 5, max_companies_per_page: int = 20):
        self.session_manager = SessionManager()
        self.data_cleaner = DataCleaner()
        self.max_pages_per_category = max_pages_per_category
        self.max_companies_per_page = max_companies_per_page
        self.max_reviews_per_company = 10
        self.scraped_data: List[ScrapedData] = []

        logging.info("ClutchScraper initialized")

    def scrape_all_development_categories(self) -> List[ScrapedData]:
        
        logging.info("Starting to scrape all development categories")

        for category_url, subcategory_name in DEVELOPMENT_SUBCATEGORIES.items():
            try:
                logging.info(f"Scraping category: {subcategory_name}")

                category_data = self.scrape_category(category_url, subcategory_name)
                self.scraped_data.extend(category_data)

                logging.info(f"Completed {subcategory_name}: {len(category_data)} records")

            except Exception as e:
                logging.error(f"Error scraping category {subcategory_name}: {e}")
                continue

        logging.info(f"Completed all categories. Total records: {len(self.scraped_data)}")

        self.scraped_data = self._deduplicate_companies(self.scraped_data)
        logging.info(f"After deduplication: {len(self.scraped_data)} unique companies")

        return self.scraped_data

    def scrape_category(self, category_url: str, subcategory_name: str) -> List[ScrapedData]:
        
        category_data = []
        current_url = category_url
        page_count = 0

        while current_url and page_count < self.max_pages_per_category:
            try:
                page_count += 1
                logging.info(f"Scraping page {page_count} of {subcategory_name}: {current_url}")

                response = self.session_manager.get(current_url)
                if not response:
                    logging.warning(f"Failed to get response for {current_url}")
                    break

                soup = BeautifulSoup(response.content, 'html.parser')

                companies = self.extract_companies_from_page(soup, subcategory_name, current_url)
                category_data.extend(companies)

                pagination_info = parse_pagination_info(soup)
                current_url = pagination_info['next_url'] if pagination_info['has_next'] else None

            except Exception as e:
                logging.error(f"Error scraping page {current_url}: {e}")
                break

        return category_data

    def extract_companies_from_page(self, soup: BeautifulSoup, subcategory_name: str, page_url: str) -> List[ScrapedData]:
        
        companies_data = []

        company_elements = self._find_company_elements(soup)

        logging.info(f"Found {len(company_elements)} company elements on page")

        for i, company_element in enumerate(company_elements[:self.max_companies_per_page]):
            try:
                company_info = self._extract_company_basic_info(company_element)
                if not company_info:
                    continue

                logging.info(f"Processing company {i+1}: {company_info.get('name', 'Unknown')}")

                company_url = company_info.get('url')
                if company_url:
                    detailed_data = self.scrape_company_details(company_url, subcategory_name)
                    companies_data.extend(detailed_data)
                else:

                    basic_record = ScrapedData(
                        subcategory=subcategory_name,
                        competitor=CompetitorInfo(
                            name=company_info.get('name'),
                            locations=company_info.get('locations', [])
                        ),
                        source_url=page_url
                    )
                    companies_data.append(basic_record)

            except Exception as e:
                logging.error(f"Error processing company element {i}: {e}")
                continue

        return companies_data

    def _find_company_elements(self, soup: BeautifulSoup) -> List[Tag]:

        selectors = [
            'li[itemtype="https://schema.org/Organization"]',  # Main provider items
            '.providers__list li',  # Provider list items
            'li[class*="provider"]',  # Any li with provider in class
            'div[class*="provider"]',  # Any div with provider in class
            'li[itemscope]',  # Schema.org marked items
            '.company-tile',
            '.provider-card'
        ]

        company_elements = []

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                logging.info(f"Found {len(elements)} elements with selector: {selector}")
                company_elements = elements
                break

        if not company_elements:
            logging.info("No elements found with standard selectors, using fallback method")
            all_divs = soup.find_all('div')
            company_elements = [
                div for div in all_divs
                if self._looks_like_company_element(div)
            ]

        return company_elements

    def _looks_like_company_element(self, element: Tag) -> bool:
        
        text = element.get_text(strip=True).lower()

        company_indicators = [
            'reviews',
            'rating',
            'stars',
            'location',
            'employees',
            'founded',
            'services'
        ]

        indicator_count = sum(1 for indicator in company_indicators if indicator in text)

        has_profile_link = bool(element.find('a', href=lambda x: x and '/profile/' in x))

        return indicator_count >= 2 or has_profile_link

    def _extract_company_basic_info(self, element: Tag) -> Optional[Dict]:
        
        try:
            company_info = {}

            name_selectors = [
                'h2 a', 'h3 a', 'h4 a',  # Header with link
                '.company-name a', '.provider-name a',  # Class-based
                'a[href*="/profile/"]'  # Profile link
            ]

            name_element = None
            for selector in name_selectors:
                name_element = element.select_one(selector)
                if name_element:
                    break

            if name_element:
                company_info['name'] = self.data_cleaner.clean_text(name_element.get_text())
                company_info['url'] = urljoin('https://clutch.co', name_element.get('href', ''))

            location_text = self._extract_location_text(element)
            if location_text:
                company_info['locations'] = self._parse_locations(location_text)

            return company_info if company_info.get('name') else None

        except Exception as e:
            logging.error(f"Error extracting company basic info: {e}")
            return None

    def _extract_location_text(self, element: Tag) -> Optional[str]:

        location_patterns = [
            r'[A-Z][a-z]+,\s*[A-Z]{2}',  # City, State
            r'[A-Z][a-z]+,\s*[A-Z][a-z]+',  # City, Country
        ]

        text = element.get_text()
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        location_element = element.find(string=re.compile(r'[A-Z][a-z]+,\s*[A-Z]'))
        return location_element.strip() if location_element else None

    def _parse_locations(self, location_text: str) -> List[str]:
        
        if not location_text:
            return []

        locations = re.split(r'[;|]|\sand\s', location_text)
        return [self.data_cleaner.clean_text(loc) for loc in locations if loc.strip()]

    @retry(max_attempts=3, delay=2.0)
    def scrape_company_details(self, company_url: str, subcategory_name: str) -> List[ScrapedData]:
        
        if not validate_url(company_url):
            logging.warning(f"Invalid URL: {company_url}")
            return []

        response = self.session_manager.get(company_url)
        if not response:
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        company_info = self._extract_detailed_company_info(soup)

        reviews_url = f"{company_url}#reviews"
        reviewers = self._scrape_reviews_from_page(reviews_url)

        record = ScrapedData(
            subcategory=subcategory_name,
            competitor=CompetitorInfo(
                name=company_info.get('name'),
                locations=company_info.get('locations', [])
            ),
            reviewers=reviewers,
            source_url=company_url,
            source_url_review=reviews_url
        )

        return [record]

    def _scrape_reviews_from_page(self, reviews_url: str) -> List[ReviewerInfo]:
        
        response = self.session_manager.get(reviews_url)
        if not response:
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        return self._extract_reviews(soup)

    def _extract_detailed_company_info(self, soup: BeautifulSoup) -> Dict:
        
        company_info = {}

        try:

            name_element = soup.find('h1') or soup.find('h2')
            if name_element:
                company_info['name'] = self.data_cleaner.clean_text(name_element.get_text())

            location_elements = soup.select('.detailed-address.location_element')
            if location_elements:
                locations = []
                for loc_elem in location_elements[:3]:
                    location_parts = []

                    spans = loc_elem.find_all('span')
                    city = None
                    state = None
                    country = None

                    for span in spans:
                        span_text = self._clean_text(span.get_text())
                        if span_text and len(span_text) > 1:
                            if not city and not any(c in span_text for c in [',', 'United States', 'CA', 'NY', 'TX']):
                                if not span_text.isdigit() and 'suite' not in span_text.lower() and 'blvd' not in span_text.lower():
                                    city = span_text
                            elif ', ' in span_text and not state:
                                parts = span_text.split(', ')
                                if len(parts) >= 2 and len(parts[1]) == 2:
                                    if not city:
                                        city = parts[0]
                                    state = parts[1]

                    if city and state:
                        location_str = f"{city}, {state}"
                        if location_str not in locations:
                            locations.append(location_str)
                    elif city:
                        if city not in locations:
                            locations.append(city)

                if locations:
                    company_info['locations'] = locations

        except Exception as e:
            logging.error(f"Error extracting detailed company info: {e}")

        return company_info

    def _extract_reviews(self, soup: BeautifulSoup) -> List[ReviewerInfo]:
        
        reviewers = []

        try:

            review_data_elements = soup.select('.profile-review__data')
            review_content_elements = soup.select('.profile-review__content')
            review_reviewer_elements = soup.select('.profile-review__reviewer')
            review_rating_elements = soup.select('.profile-review__rating-metrics')

            logging.info(f"Found {len(review_data_elements)} review data, {len(review_content_elements)} content, {len(review_reviewer_elements)} reviewer elements, {len(review_rating_elements)} rating metrics")

            num_reviews = min(len(review_data_elements), len(review_content_elements), len(review_reviewer_elements))
            num_reviews = min(num_reviews, self.max_reviews_per_company)

            for i in range(num_reviews):
                try:
                    rating_elem = review_rating_elements[i] if i < len(review_rating_elements) else None
                    reviewer = self._extract_single_clutch_review(
                        review_data_elements[i],
                        review_content_elements[i],
                        review_reviewer_elements[i],
                        rating_elem
                    )
                    if reviewer:
                        reviewers.append(reviewer)
                except Exception as e:
                    logging.warning(f"Error extracting review {i+1}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting reviews: {e}")

        return reviewers

    def _extract_single_clutch_review(self, data_elem: Tag, content_elem: Tag, reviewer_elem: Tag, rating_elem: Optional[Tag] = None) -> Optional[ReviewerInfo]:
        
        try:
            reviewer = ReviewerInfo()
            project = ProjectInfo()

            if data_elem:
                data_text = self._clean_text(data_elem.get_text())

                services = []
                for li in data_elem.find_all('li'):
                    service_text = self._clean_text(li.get_text())
                    if service_text and not any(skip in service_text.lower() for skip in ['confidential', 'ongoing', '2022', '2023', '2024', '2025']):
                        services.append(service_text)

                if services:
                    project.service_provided = ', '.join(services[:3])  # Take first 3 services

                date_patterns = [
                    r'([A-Za-z]{3,9}\.?\s+\d{4})\s*[-–]\s*([A-Za-z]{3,9}\.?\s+\d{4}|Ongoing)',
                    r'([A-Za-z]{3,9})\s*[-–]\s*([A-Za-z]{3,9}\.?\s+\d{4})',
                ]

                for pattern in date_patterns:
                    match = re.search(pattern, data_text)
                    if match:
                        project.start_date = match.group(1).strip()
                        project.end_date = match.group(2).strip()
                        break

                budget_pattern = r'\$([0-9,]+(?:\s*to\s*\$[0-9,]+)?)'
                match = re.search(budget_pattern, data_text)
                if match:
                    project.project_size = f"${match.group(1)}"

            if content_elem:
                content_text = self._clean_text(content_elem.get_text())

                score_patterns = [
                    r'(\d+\.?\d*)\s*(?:Quality|Overall|Rating)',
                    r'(\d+\.?\d*)/5',
                    r'(\d+\.?\d*)\s*stars?',
                ]

                for pattern in score_patterns:
                    match = re.search(pattern, content_text, re.IGNORECASE)
                    if match:
                        try:
                            project.score = float(match.group(1))
                            break
                        except ValueError:
                            continue

            if rating_elem:
                try:
                    dl_elements = rating_elem.find_all('dl')
                    for dl in dl_elements:
                        dt = dl.find('dt')
                        dd = dl.find('dd')
                        if dt and dd:
                            metric_name = self._clean_text(dt.get_text()).lower()
                            metric_value = self._clean_text(dd.get_text())
                            try:
                                score_value = float(metric_value)
                                if 'quality' in metric_name:
                                    project.score_quality = score_value
                                elif 'schedule' in metric_name:
                                    project.score_schedule = score_value
                                elif 'cost' in metric_name:
                                    project.score_cost = score_value
                                elif 'willing to refer' in metric_name or 'refer' in metric_name:
                                    project.score_willing_to_refer = score_value
                            except ValueError:
                                continue
                except Exception as e:
                    logging.warning(f"Error extracting rating metrics: {e}")

            if reviewer_elem:

                reviewer_text = self._clean_text(reviewer_elem.get_text())

                self._parse_reviewer_info(reviewer, reviewer_text, reviewer_elem)

            reviewer.project = project

            if reviewer.name or reviewer.company or project.service_provided or project.score:
                return reviewer

            return None

        except Exception as e:
            logging.error(f"Error extracting Clutch review: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        
        if not text:
            return ""

        cleaned = re.sub(r'\s+', ' ', text)

        cleaned = re.sub(r'\t+', ' ', cleaned)

        cleaned = cleaned.strip()

        return cleaned

    def _parse_reviewer_info(self, reviewer: ReviewerInfo, reviewer_text: str, reviewer_elem: Tag):
        
        try:

            position_elem = reviewer_elem.find(class_='reviewer_position')
            if position_elem:
                position_text = self._clean_text(position_elem.get_text())

                if ',' in position_text:
                    parts = position_text.split(',', 1)
                    reviewer.job_title = parts[0].strip()
                    reviewer.company = parts[1].strip()
                else:
                    reviewer.job_title = position_text

            name_elem = reviewer_elem.find(class_='reviewer_card--name')
            name_found = False
            if name_elem:
                name = self._clean_text(name_elem.get_text())
                if name and name != 'Anonymous':
                    reviewer.name = name
                    name_found = True
                else:

                    name_found = True

            ul_elem = reviewer_elem.find('ul')
            if ul_elem:

                li_elements = ul_elem.find_all('li')
                for li in li_elements:
                    li_text = self._clean_text(li.get_text())

                    if li_text in ['Verified', 'Online Review', 'Phone Interview']:
                        continue

                    if re.search(r'\d+(?:-\d+)?\s*employees?', li_text, re.IGNORECASE):
                        reviewer.company_size = li_text
                        continue

                    industries = [
                        'Industry', 'Technology', 'Consulting', 'Automotive', 'Healthcare',
                        'Finance', 'Marketing', 'Non-profit', 'Nonprofit', 'Education',
                        'Retail', 'Manufacturing', 'Information technology', 'Consumer Products',
                        'Social Networking', 'Other Industry'
                    ]
                    is_industry = False
                    for industry in industries:
                        if industry.lower() in li_text.lower():
                            reviewer.industry = li_text
                            is_industry = True
                            break

                    if is_industry:
                        continue

                    location_patterns = [
                        r'^([A-Za-z\s]+),\s+([A-Za-z\s]+)$',  # City, State (allow mixed case)
                        r'^([A-Za-z\s]+)$',  # Just city or state (allow mixed case)
                    ]
                    for pattern in location_patterns:
                        if re.match(pattern, li_text) and len(li_text) < 50:
                            reviewer.location = li_text
                            break

            if not reviewer.name and not name_found:

                name_patterns = [
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # First Last
                    r'([A-Z][a-z]+)',  # Single name
                ]
                skip_names = ['Anonymous', 'Verified', 'Online', 'Review', 'Phone', 'Interview']
                if reviewer.company:

                    skip_names.extend(reviewer.company.split())

                for pattern in name_patterns:
                    matches = re.findall(pattern, reviewer_text)
                    for match in matches:
                        if match not in skip_names:
                            reviewer.name = match
                            break
                    if reviewer.name:
                        break

        except Exception as e:
            logging.warning(f"Error parsing reviewer info: {e}")

    def _extract_single_review(self, element: Tag) -> Optional[ReviewerInfo]:
        
        try:
            reviewer = ReviewerInfo()
            project = ProjectInfo()

            name_element = element.find('strong') or element.find('h3') or element.find('h4')
            if name_element:
                reviewer.name = self.data_cleaner.clean_text(name_element.get_text())

            text = element.get_text()

            title_company_pattern = r'([^,]+),\s*([^,]+)\s+at\s+([^,\n]+)'
            match = re.search(title_company_pattern, text)
            if match:
                reviewer.job_title = self.data_cleaner.clean_text(match.group(2))
                reviewer.company = self.data_cleaner.clean_text(match.group(3))

            industry_pattern = r'Industry:\s*([^\n]+)'
            match = re.search(industry_pattern, text)
            if match:
                reviewer.industry = self.data_cleaner.clean_text(match.group(1))

            size_pattern = r'(\d+[-\s]*\d*\s*employees?)'
            match = re.search(size_pattern, text, re.IGNORECASE)
            if match:
                reviewer.company_size = self.data_cleaner.parse_employee_count(match.group(1))

            service_pattern = r'Service[s]?:\s*([^\n]+)'
            match = re.search(service_pattern, text)
            if match:
                project.service_provided = self.data_cleaner.clean_text(match.group(1))

            budget_pattern = r'\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?'
            match = re.search(budget_pattern, text)
            if match:
                project.project_size = match.group(0)

            date_text = text
            start_date, end_date = self.data_cleaner.parse_date_range(date_text)
            project.start_date = start_date
            project.end_date = end_date

            rating_element = element.find(string=re.compile(r'\d+\.?\d*\s*(?:out of|/)\s*\d+'))
            if rating_element:
                project.score = self.data_cleaner.extract_number_from_text(rating_element)

            reviewer.project = project

            if reviewer.name or reviewer.company or project.service_provided:
                return reviewer

            return None

        except Exception as e:
            logging.error(f"Error extracting single review: {e}")
            return None

    def _deduplicate_companies(self, data: List[ScrapedData]) -> List[ScrapedData]:
        
        if not data:
            return data

        company_groups = {}
        for record in data:
            company_name = record.competitor.name if record.competitor else None
            if not company_name:
                continue

            normalized_name = company_name.lower().strip()

            if normalized_name not in company_groups:
                company_groups[normalized_name] = []
            company_groups[normalized_name].append(record)

        deduplicated = []
        for company_name, records in company_groups.items():
            if len(records) == 1:
                deduplicated.append(records[0])
            else:

                best_record = max(records, key=lambda r: len(r.reviewers) if r.reviewers else 0)

                all_reviewers = []
                reviewer_signatures = set()

                for record in records:
                    if record.reviewers:
                        for reviewer in record.reviewers:

                            signature = (
                                reviewer.name or "",
                                reviewer.company or "",
                                reviewer.job_title or ""
                            )
                            if signature not in reviewer_signatures:
                                reviewer_signatures.add(signature)
                                all_reviewers.append(reviewer)

                best_record.reviewers = all_reviewers
                deduplicated.append(best_record)

                logging.info(f"Merged {len(records)} instances of '{company_name}' -> {len(all_reviewers)} unique reviewers")

        return deduplicated

    def close(self):
        
        self.session_manager.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":

    from utils import setup_logging
    from models import DataExporter

    setup_logging()

    print("Testing ClutchScraper...")

    with ClutchScraper(max_pages_per_category=1, max_companies_per_page=3) as scraper:

        test_url = "https://clutch.co/developers/software-developers"
        test_data = scraper.scrape_category(test_url, "Software Developers")

        print(f"Scraped {len(test_data)} records")

        if test_data:

            DataExporter.export_to_json(test_data, "test_output.json")
            DataExporter.export_to_csv(test_data, "test_output.csv")

            print("Sample record:")
            sample = test_data[0].to_flat_dict()
            for key, value in sample.items():
                print(f"  {key}: {value}")

    print("Scraper test completed.")