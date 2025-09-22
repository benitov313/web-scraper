

import logging
from config import ScrapingConfig, ScrapingTargets
from main import ClutchScrapingManager
from models import ScrapedData, CompetitorInfo, ReviewerInfo, ProjectInfo
from exporter import AdvancedDataExporter

def demo_data_models():
    
    print("="*60)
    print("DEMO: Data Models")
    print("="*60)

    sample_data = ScrapedData(
        subcategory="Software Developers",
        competitor=CompetitorInfo(
            name="TechnoSoft Solutions",
            locations=["New York, NY", "London, UK"]
        ),
        reviewer=ReviewerInfo(
            name="John Smith",
            job_title="Chief Technology Officer",
            company="FinanceCorpXYZ",
            industry="Financial Services",
            location="Austin, TX",
            company_size="100-200 employees"
        ),
        project=ProjectInfo(
            service_provided="Custom Enterprise Software Development",
            project_size="$75,000 - $150,000",
            start_date="Jan 2023",
            end_date="Aug 2023",
            score=4.7
        ),
        source_url="https://clutch.co/profile/technosoft-solutions"
    )

    print("Sample ScrapedData object:")
    flat_dict = sample_data.to_flat_dict()
    for key, value in flat_dict.items():
        print(f"  {key}: {value}")

    return [sample_data]

def demo_exporter(sample_data):
    
    print("\n" + "="*60)
    print("DEMO: Data Export")
    print("="*60)

    exporter = AdvancedDataExporter("demo_output")

    try:

        exported_files = exporter.export_all_formats(sample_data, "demo_clutch_data")

        print("Successfully exported sample data to:")
        for format_type, filepath in exported_files.items():
            print(f"  {format_type}: {filepath}")

        filtered_file = exporter.export_filtered_data(
            sample_data,
            {'subcategory': 'Software Developers'},
            "demo_filtered.csv"
        )
        print(f"  filtered: {filtered_file}")

    except Exception as e:
        print(f"Export demo failed: {e}")

def demo_configuration():
    
    print("\n" + "="*60)
    print("DEMO: Configuration")
    print("="*60)

    config = ScrapingConfig(
        max_pages_per_category=2,
        max_companies_per_page=5,
        min_delay=0.5,
        max_delay=1.5,
        output_directory="demo_output"
    )

    targets = ScrapingTargets(
        target_categories=["Software Developers", "Web Developers"],
        skip_categories=[]
    )

    print("Configuration:")
    print(f"  Max pages per category: {config.max_pages_per_category}")
    print(f"  Max companies per page: {config.max_companies_per_page}")
    print(f"  Delay range: {config.min_delay} - {config.max_delay} seconds")
    print(f"  Output directory: {config.output_directory}")

    print("\nTargets:")
    print(f"  Target categories: {targets.target_categories}")
    print(f"  Skip categories: {targets.skip_categories}")

    return config, targets

def demo_command_line_usage():
    
    print("\n" + "="*60)
    print("DEMO: Command-Line Usage Examples")
    print("="*60)

    examples = [
        ("List all available categories:", "python main.py --list-categories"),
        ("Scrape all development categories:", "python main.py"),
        ("Scrape specific categories:", "python main.py --categories \"Software Developers\" \"Web Developers\""),
        ("Scrape with custom limits:", "python main.py --max-pages 3 --max-companies 10"),
        ("Skip certain categories:", "python main.py --skip-categories \"AR/VR\" \"Blockchain\""),
        ("Use custom output directory:", "python main.py --output-dir /path/to/output"),
        ("Enable debug logging:", "python main.py --log-level DEBUG"),
        ("Use environment variables:", "SCRAPER_MAX_PAGES=2 SCRAPER_MIN_DELAY=2.0 python main.py"),
    ]

    for description, command in examples:
        print(f"\n{description}")
        print(f"  {command}")

def demo_scraper_features():
    
    print("\n" + "="*60)
    print("DEMO: Scraper Features")
    print("="*60)

    print("Key Features:")
    print("  - Respectful scraping with rate limiting")
    print("  - Automatic retry logic for failed requests")
    print("  - Comprehensive error handling and logging")
    print("  - Multiple export formats (JSON, CSV, Excel, SQLite)")
    print("  - Configurable targeting and limits")
    print("  - Graceful shutdown on interruption")
    print("  - Data validation and cleaning")

    print("\nData Extracted:")
    print("  GENERAL:")
    print("    - Category (Development)")
    print("    - Subcategory (e.g., Software Developers)")
    print("  COMPETITOR:")
    print("    - Competitor name")
    print("    - Competitor locations")
    print("  REVIEWS:")
    print("    - Reviewer name")
    print("    - Reviewer job title")
    print("    - Reviewer company")
    print("    - Reviewer industry")
    print("    - Reviewer location")
    print("    - Reviewer company size")
    print("  PROJECT:")
    print("    - Service provided")
    print("    - Project size")
    print("    - Dates (start–end)")
    print("    - Score")

    print("\nAll Development Subcategories Supported:")
    from models import DEVELOPMENT_SUBCATEGORIES
    for slug, name in DEVELOPMENT_SUBCATEGORIES.items():
        print(f"  - {name}")

def demo_best_practices():
    
    print("\n" + "="*60)
    print("DEMO: Web Scraping Best Practices")
    print("="*60)

    print("This scraper follows these best practices:")

    print("\n1. RESPECTFUL SCRAPING:")
    print("  - Rate limiting between requests (1-3 second delays)")
    print("  - Realistic browser headers")
    print("  - Graceful handling of rate limit responses")
    print("  - Configurable limits to avoid overwhelming servers")

    print("\n2. ERROR HANDLING:")
    print("  - Comprehensive exception handling")
    print("  - Retry logic for transient failures")
    print("  - Detailed logging for debugging")
    print("  - Graceful degradation on errors")

    print("\n3. DATA QUALITY:")
    print("  - Data validation and cleaning")
    print("  - Structured data models")
    print("  - Multiple export formats")
    print("  - Data integrity checks")

    print("\n4. MAINTAINABILITY:")
    print("  - Modular code structure")
    print("  - Configuration-driven behavior")
    print("  - Comprehensive documentation")
    print("  - Easy extensibility")

    print("\n5. ETHICAL CONSIDERATIONS:")
    print("  - Respects robots.txt (when implemented)")
    print("  - Reasonable request frequency")
    print("  - No overwhelming of target servers")
    print("  - Transparent user agent")

def demo_troubleshooting():
    
    print("\n" + "="*60)
    print("DEMO: Troubleshooting Common Issues")
    print("="*60)

    issues = [
        ("403 Forbidden errors", "Site has bot protection. Try:\n    - Increasing delays between requests\n    - Using different user agents\n    - Running from different IP addresses"),
        ("No data extracted", "Site structure may have changed. Check:\n    - CSS selectors in scraper.py\n    - URL patterns in models.py\n    - HTML structure analysis"),
        ("Slow performance", "Optimize by:\n    - Reducing max_pages_per_category\n    - Reducing max_companies_per_page\n    - Increasing delays (paradoxically faster due to fewer blocks)"),
        ("Memory issues", "Handle large datasets by:\n    - Processing in smaller batches\n    - Streaming data to files\n    - Using database storage instead of in-memory"),
        ("Network timeouts", "Improve reliability with:\n    - Increasing timeout values\n    - Adding more retry attempts\n    - Using proxy rotation"),
    ]

    for issue, solution in issues:
        print(f"\nISSUE: {issue}")
        print(f"SOLUTION: {solution}")

def main():
    
    print("CLUTCH.CO WEB SCRAPER - COMPREHENSIVE DEMO")
    print("This demo shows all features and capabilities")

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    sample_data = demo_data_models()

    demo_exporter(sample_data)

    demo_configuration()

    demo_command_line_usage()

    demo_scraper_features()

    demo_best_practices()

    demo_troubleshooting()

    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("To run the actual scraper:")
    print("  python main.py --list-categories  # See available categories")
    print("  python main.py --help             # See all options")
    print("  python main.py --max-pages 1      # Quick test run")

if __name__ == "__main__":
    main()