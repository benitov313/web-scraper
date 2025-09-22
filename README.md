# Clutch.co Web Scraper

## Quick Start

### Installation

```bash
# Clone or download the scraper files
cd web-scraper-clutch

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# List all available categories
python main.py --list-categories

# Scrape all development categories (respectful defaults)
python main.py

# Scrape specific categories only
python main.py --categories "Software Developers" "Web Developers"

# Quick test with limited scope
python main.py --max-pages 1 --max-companies 5
```

### Extracted Information

**GENERAL**
- Category
- Subcategory

**COMPANY**
- Company name
- Company locations

**REVIEWS**
- Reviewer name
- Reviewer job title
- Reviewer company
- Reviewer industry
- Reviewer location
- Reviewer company size (# of employees)

**PROJECT**
- Service provided
- Project size/budget
- Dates (start–end)
- Score/rating

### 📊 **Multiple Export Formats**
- **JSON**: Structured data for APIs and applications
- **CSV**: Spreadsheet-compatible format
- **Excel**: Multi-sheet workbooks with summaries
- **SQLite**: Database format for complex queries
- **Summary Reports**: Human-readable analysis



## Configuration

### Command Line Options

```bash
# Target selection
--categories "Software Developers" "Web Developers"  # Specific categories
--skip-categories "AR/VR" "Blockchain"               # Exclude categories

# Scraping limits
--max-pages 3              # Pages per category
--max-companies 10         # Companies per page

# Rate limiting
--min-delay 1.0           # Minimum delay (seconds)
--max-delay 3.0           # Maximum delay (seconds)

# Output
--output-dir /path/to/output    # Custom output directory
--log-level DEBUG              # Logging verbosity
```

### Environment Variables

```bash
# Configuration via environment
export SCRAPER_MAX_PAGES=2
export SCRAPER_MIN_DELAY=2.0
export SCRAPER_OUTPUT_DIR="/custom/path"

python main.py
```

## Troubleshooting

### Common Issues

**403 Forbidden Errors**
```bash
# Increase delays
python main.py --min-delay 3.0 --max-delay 5.0

# Use environment variables for longer delays
export SCRAPER_MIN_DELAY=5.0
export SCRAPER_MAX_DELAY=10.0
```

**Performance Issues**
```bash
# Reduce scope for faster testing
python main.py --max-pages 1 --max-companies 3

# Process fewer categories
python main.py --categories "Software Developers"
```

### Debug Mode

```bash
# Enable detailed logging
python main.py --log-level DEBUG --log-file debug.log

# Check the log file for detailed information
tail -f debug.log
```