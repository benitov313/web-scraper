

import argparse
import logging
import sys
import signal
from datetime import datetime
from typing import List, Optional

from config import ScrapingConfig, ScrapingTargets, get_config_from_env, get_targets_from_env, validate_config
from scraper import ClutchScraper
from exporter import AdvancedDataExporter
from models import ScrapedData, DEVELOPMENT_SUBCATEGORIES
from exceptions import ClutchScraperError, ErrorHandler
from utils import setup_logging

class ClutchScrapingManager:

    def __init__(self, config: ScrapingConfig, targets: ScrapingTargets):
        
        self.config = config
        self.targets = targets
        self.scraper: Optional[ClutchScraper] = None
        self.exporter: Optional[AdvancedDataExporter] = None
        self.error_handler = ErrorHandler()
        self.scraped_data: List[ScrapedData] = []
        self.interrupted = False

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, _frame):
        
        logging.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.interrupted = True

    def run(self) -> bool:
        
        try:
            logging.info("Starting Clutch.co scraping process")
            logging.info(f"Configuration: {self.config}")
            logging.info(f"Targets: {self.targets}")

            if not self._initialize_components():
                return False

            categories_to_scrape = self._get_categories_to_scrape()
            logging.info(f"Will scrape {len(categories_to_scrape)} categories: {list(categories_to_scrape.keys())}")

            success = self._scrape_categories(categories_to_scrape)

            if self.scraped_data:
                self._export_data()
            else:
                logging.warning("No data was scraped")

            self._print_summary()

            return success

        except Exception as e:
            logging.error(f"Fatal error in scraping process: {e}")
            return False

        finally:
            self._cleanup()

    def _initialize_components(self) -> bool:
        
        try:

            config_errors = validate_config(self.config)
            if config_errors:
                logging.error(f"Configuration errors: {config_errors}")
                return False

            self.scraper = ClutchScraper(
                max_pages_per_category=self.config.max_pages_per_category,
                max_companies_per_page=self.config.max_companies_per_page
            )

            self.exporter = AdvancedDataExporter(self.config.output_directory)

            logging.info("Components initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to initialize components: {e}")
            return False

    def _get_categories_to_scrape(self) -> dict:
        
        all_categories = DEVELOPMENT_SUBCATEGORIES

        if self.targets.target_categories:

            categories = {}
            for target in self.targets.target_categories:

                for url, name in all_categories.items():
                    if target.lower() == name.lower():
                        categories[url] = name
                        break
                else:
                    logging.warning(f"Target category not found: {target}")
        else:

            categories = {}
            for url, name in all_categories.items():
                if name not in self.targets.skip_categories:
                    categories[url] = name

        return categories

    def _scrape_categories(self, categories: dict) -> bool:
        
        total_success = False
        consecutive_failures = 0

        for category_url, category_name in categories.items():
            if self.interrupted:
                logging.info("Scraping interrupted by user")
                break

            try:
                logging.info(f"Starting category: {category_name}")

                category_data = self.scraper.scrape_category(category_url, category_name)

                if category_data:
                    self.scraped_data.extend(category_data)
                    logging.info(f"Successfully scraped {len(category_data)} records from {category_name}")
                    consecutive_failures = 0
                    total_success = True
                else:
                    logging.warning(f"No data scraped from {category_name}")
                    consecutive_failures += 1

                if consecutive_failures >= 3:
                    logging.error("Too many consecutive failures, stopping")
                    break

            except ClutchScraperError as e:
                logging.error(f"Scraping error for {category_name}: {e}")
                recovery = self.error_handler.handle_error(e, category_name)

                if recovery['should_retry']:
                    logging.info(f"Retrying {category_name} after {recovery['delay']} seconds")

                else:
                    consecutive_failures += 1

            except Exception as e:
                logging.error(f"Unexpected error scraping {category_name}: {e}")
                consecutive_failures += 1

        return total_success

    def _export_data(self):
        
        try:
            logging.info(f"Exporting {len(self.scraped_data)} records")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"clutch_development_data_{timestamp}"

            exported_files = self.exporter.export_all_formats(self.scraped_data, base_filename)

            logging.info("Export completed successfully:")
            for format_type, filepath in exported_files.items():
                logging.info(f"  {format_type}: {filepath}")

        except Exception as e:
            logging.error(f"Export failed: {e}")

    def _print_summary(self):
        
        print("\n" + "="*60)
        print("CLUTCH.CO SCRAPING SUMMARY")
        print("="*60)

        print(f"Total records scraped: {len(self.scraped_data)}")

        if self.scraped_data:

            category_counts = {}
            company_names = set()

            for item in self.scraped_data:
                subcat = item.subcategory or "Unknown"
                category_counts[subcat] = category_counts.get(subcat, 0) + 1

                if item.competitor and item.competitor.name:
                    company_names.add(item.competitor.name)

            print(f"Unique companies: {len(company_names)}")
            print(f"Categories scraped: {len(category_counts)}")

            print("\nBreakdown by category:")
            for category, count in sorted(category_counts.items()):
                print(f"  {category}: {count} records")

        error_summary = self.error_handler.get_error_summary()
        if error_summary:
            print("\nErrors encountered:")
            for error_type, count in error_summary.items():
                print(f"  {error_type}: {count}")

        print("="*60)

    def _cleanup(self):
        
        if self.scraper:
            self.scraper.close()
        logging.info("Cleanup completed")

def create_parser() -> argparse.ArgumentParser:
    
    parser = argparse.ArgumentParser(
        description="Scrape development company data from Clutch.co",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--categories',
        nargs='+',
        help='Specific categories to scrape (default: all)'
    )

    parser.add_argument(
        '--skip-categories',
        nargs='+',
        help='Categories to skip when scraping all'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum pages per category (default: from config)'
    )

    parser.add_argument(
        '--max-companies',
        type=int,
        help='Maximum companies per page (default: from config)'
    )

    parser.add_argument(
        '--min-delay',
        type=float,
        help='Minimum delay between requests in seconds'
    )

    parser.add_argument(
        '--max-delay',
        type=float,
        help='Maximum delay between requests in seconds'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory for exported files'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    parser.add_argument(
        '--log-file',
        help='Log file path'
    )

    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List all available categories and exit'
    )

    return parser

def main():
    
    parser = create_parser()
    args = parser.parse_args()

    if args.list_categories:
        print("Available Development Categories:")
        print("-" * 40)
        for url, name in DEVELOPMENT_SUBCATEGORIES.items():
            print(f"{name}")
            print(f"  URL: {url}")
        return

    config = get_config_from_env()
    targets = get_targets_from_env()

    if args.categories:
        targets.target_categories = args.categories

    if args.skip_categories:
        targets.skip_categories = args.skip_categories

    if args.max_pages:
        config.max_pages_per_category = args.max_pages

    if args.max_companies:
        config.max_companies_per_page = args.max_companies

    if args.min_delay:
        config.min_delay = args.min_delay

    if args.max_delay:
        config.max_delay = args.max_delay

    if args.output_dir:
        config.output_directory = args.output_dir

    if args.log_level:
        config.log_level = args.log_level

    if args.log_file:
        config.log_file = args.log_file

    setup_logging(
        log_file=config.log_file,
        level=getattr(logging, config.log_level)
    )

    manager = ClutchScrapingManager(config, targets)
    success = manager.run()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
