#!/usr/bin/env python3
"""
Configuration settings for Clutch.co scraper
Centralized configuration management
"""

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ScrapingConfig:
    """Configuration class for scraping parameters"""

    # Rate limiting settings
    min_delay: float = 1.0  # Minimum delay between requests (seconds)
    max_delay: float = 3.0  # Maximum delay between requests (seconds)

    # Request settings
    timeout: int = 30  # Request timeout (seconds)
    max_retries: int = 3  # Maximum retry attempts for failed requests
    retry_delay: float = 2.0  # Delay between retries (seconds)

    # Scraping limits
    max_pages_per_category: int = 5  # Maximum pages to scrape per category
    max_companies_per_page: int = 20  # Maximum companies to process per page
    max_reviews_per_company: int = 10  # Maximum reviews to extract per company

    # Output settings
    output_directory: str = "output"  # Directory for output files
    enable_json_export: bool = True  # Enable JSON export
    enable_csv_export: bool = True  # Enable CSV export
    backup_data: bool = True  # Create backup of scraped data

    # Logging settings
    log_level: str = "INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR)
    log_file: str = "clutch_scraper.log"  # Log file name
    enable_console_logging: bool = True  # Enable console logging

    # User agent rotation
    user_agents: List[str] = None

    def __post_init__(self):
        """Initialize default user agents if not provided"""
        if self.user_agents is None:
            self.user_agents = [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
            ]

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)


@dataclass
class ScrapingTargets:
    """Configuration for what to scrape"""

    # Categories to scrape (empty means all)
    target_categories: List[str] = None

    # Specific companies to target (optional)
    target_companies: List[str] = None

    # Skip categories (if scraping all but want to exclude some)
    skip_categories: List[str] = None

    def __post_init__(self):
        """Initialize defaults"""
        if self.target_categories is None:
            self.target_categories = []

        if self.target_companies is None:
            self.target_companies = []

        if self.skip_categories is None:
            self.skip_categories = []


# Development categories configuration with priority levels
DEVELOPMENT_CATEGORIES_CONFIG = {
    # High priority - most common/valuable categories
    'high_priority': [
        'Software Developers',
        'Web Developers',
        'Mobile Apps',
        'E-Commerce Developers',
        'Python & Django',
        'React Native',
        'Artificial Intelligence'
    ],

    # Medium priority
    'medium_priority': [
        'App Developers',
        'PHP',
        'Java',
        'Software Testing',
        'Wordpress',
        'Shopify',
        'Flutter'
    ],

    # Lower priority
    'low_priority': [
        'Laravel',
        'Microsoft Sharepoint',
        'Webflow',
        'Drupal',
        'Blockchain',
        'AR/VR',
        'IoT',
        'DOTNET',
        'Ruby on Rails',
        'Magento',
        'BigCommerce',
        'WooCommerce'
    ]
}

# Selectors configuration - adjust these based on actual site structure
SELECTORS_CONFIG = {
    'company_listing': [
        'div[class*="company"]',
        'div[class*="provider"]',
        'div[class*="listing"]',
        'article[class*="company"]',
        'div[class*="card"]',
        '.search-result',
        '.company-tile',
        '.provider-card'
    ],

    'company_name': [
        'h2 a',
        'h3 a',
        'h4 a',
        '.company-name a',
        '.provider-name a',
        'a[href*="/profile/"]'
    ],

    'reviews': [
        'div[class*="review"]',
        'article[class*="review"]',
        'div[class*="testimonial"]',
        '.review-card',
        '.client-review'
    ],

    'pagination': [
        'nav[class*="pagination"]',
        '.pagination',
        '.pager',
        'div[class*="pagination"]'
    ]
}

# Error handling configuration
ERROR_HANDLING_CONFIG = {
    'max_consecutive_failures': 5,  # Stop category after N consecutive failures
    'max_total_failures': 20,  # Stop entire scraping after N total failures
    'retry_on_status_codes': [429, 500, 502, 503, 504],  # HTTP codes to retry
    'skip_on_status_codes': [403, 404, 401],  # HTTP codes to skip (don't retry)
    'backoff_multiplier': 2.0,  # Exponential backoff multiplier
    'max_backoff_delay': 60.0  # Maximum backoff delay (seconds)
}


def get_config_from_env() -> ScrapingConfig:
    """Create configuration from environment variables"""
    config = ScrapingConfig()

    # Override with environment variables if they exist
    config.min_delay = float(os.getenv('SCRAPER_MIN_DELAY', config.min_delay))
    config.max_delay = float(os.getenv('SCRAPER_MAX_DELAY', config.max_delay))
    config.timeout = int(os.getenv('SCRAPER_TIMEOUT', config.timeout))
    config.max_retries = int(os.getenv('SCRAPER_MAX_RETRIES', config.max_retries))
    config.max_pages_per_category = int(os.getenv('SCRAPER_MAX_PAGES', config.max_pages_per_category))
    config.max_companies_per_page = int(os.getenv('SCRAPER_MAX_COMPANIES', config.max_companies_per_page))
    config.output_directory = os.getenv('SCRAPER_OUTPUT_DIR', config.output_directory)
    config.log_level = os.getenv('SCRAPER_LOG_LEVEL', config.log_level)
    config.log_file = os.getenv('SCRAPER_LOG_FILE', config.log_file)

    return config


def get_targets_from_env() -> ScrapingTargets:
    """Create targets configuration from environment variables"""
    targets = ScrapingTargets()

    # Parse comma-separated environment variables
    target_cats = os.getenv('SCRAPER_TARGET_CATEGORIES', '')
    if target_cats:
        targets.target_categories = [cat.strip() for cat in target_cats.split(',')]

    skip_cats = os.getenv('SCRAPER_SKIP_CATEGORIES', '')
    if skip_cats:
        targets.skip_categories = [cat.strip() for cat in skip_cats.split(',')]

    return targets


def validate_config(config: ScrapingConfig) -> List[str]:
    """Validate configuration and return list of errors"""
    errors = []

    if config.min_delay < 0:
        errors.append("min_delay must be non-negative")

    if config.max_delay < config.min_delay:
        errors.append("max_delay must be >= min_delay")

    if config.timeout <= 0:
        errors.append("timeout must be positive")

    if config.max_retries < 0:
        errors.append("max_retries must be non-negative")

    if config.max_pages_per_category <= 0:
        errors.append("max_pages_per_category must be positive")

    if config.max_companies_per_page <= 0:
        errors.append("max_companies_per_page must be positive")

    if not os.path.exists(config.output_directory):
        try:
            os.makedirs(config.output_directory)
        except OSError as e:
            errors.append(f"Cannot create output directory: {e}")

    return errors


if __name__ == "__main__":
    # Test configuration
    print("Testing configuration...")

    config = get_config_from_env()
    targets = get_targets_from_env()

    print(f"Config: {config}")
    print(f"Targets: {targets}")

    errors = validate_config(config)
    if errors:
        print(f"Configuration errors: {errors}")
    else:
        print("Configuration is valid")

    print(f"Available categories by priority:")
    for priority, categories in DEVELOPMENT_CATEGORIES_CONFIG.items():
        print(f"  {priority}: {len(categories)} categories")
        for cat in categories:
            print(f"    - {cat}")