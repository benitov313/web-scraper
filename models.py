#!/usr/bin/env python3

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import json
import csv
from datetime import datetime


@dataclass
class ProjectInfo:
    service_provided: Optional[str] = None
    project_size: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    score: Optional[float] = None
    score_quality: Optional[float] = None
    score_schedule: Optional[float] = None
    score_cost: Optional[float] = None
    score_willing_to_refer: Optional[float] = None


@dataclass
class ReviewerInfo:
    name: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    project: Optional[ProjectInfo] = None

    def __post_init__(self):
        if self.project is None:
            self.project = ProjectInfo()


@dataclass
class CompetitorInfo:
    name: Optional[str] = None
    locations: List[str] = None

    def __post_init__(self):
        if self.locations is None:
            self.locations = []


@dataclass
class ScrapedData:
    category: str = "Development"
    subcategory: Optional[str] = None
    competitor: Optional[CompetitorInfo] = None
    reviewers: List[ReviewerInfo] = None
    scraped_at: Optional[str] = None
    source_url: Optional[str] = None
    source_url_review: Optional[str] = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()
        if self.competitor is None:
            self.competitor = CompetitorInfo()
        if self.reviewers is None:
            self.reviewers = []
        if self.source_url and not self.source_url_review:
            self.source_url_review = f"{self.source_url}#reviews"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_flat_dict_list(self) -> List[Dict[str, Any]]:
        if not self.reviewers:
            return [{
                'category': self.category,
                'subcategory': self.subcategory,
                'scraped_at': self.scraped_at,
                'source_url': self.source_url,
                'source_url_review': self.source_url_review,
                'competitor_name': self.competitor.name if self.competitor else None,
                'competitor_locations': ', '.join(self.competitor.locations) if self.competitor and self.competitor.locations else None,
                'reviewer_name': None,
                'reviewer_job_title': None,
                'reviewer_company': None,
                'reviewer_industry': None,
                'reviewer_location': None,
                'reviewer_company_size': None,
                'service_provided': None,
                'project_size': None,
                'project_start_date': None,
                'project_end_date': None,
                'project_score': None,
                'project_score_quality': None,
                'project_score_schedule': None,
                'project_score_cost': None,
                'project_score_willing_to_refer': None,
            }]

        rows = []
        for reviewer in self.reviewers:
            row = {
                'category': self.category,
                'subcategory': self.subcategory,
                'scraped_at': self.scraped_at,
                'source_url': self.source_url,
                'source_url_review': self.source_url_review,
                'competitor_name': self.competitor.name if self.competitor else None,
                'competitor_locations': ', '.join(self.competitor.locations) if self.competitor and self.competitor.locations else None,
                'reviewer_name': reviewer.name,
                'reviewer_job_title': reviewer.job_title,
                'reviewer_company': reviewer.company,
                'reviewer_industry': reviewer.industry,
                'reviewer_location': reviewer.location,
                'reviewer_company_size': reviewer.company_size,
                'service_provided': reviewer.project.service_provided if reviewer.project else None,
                'project_size': reviewer.project.project_size if reviewer.project else None,
                'project_start_date': reviewer.project.start_date if reviewer.project else None,
                'project_end_date': reviewer.project.end_date if reviewer.project else None,
                'project_score': reviewer.project.score if reviewer.project else None,
                'project_score_quality': reviewer.project.score_quality if reviewer.project else None,
                'project_score_schedule': reviewer.project.score_schedule if reviewer.project else None,
                'project_score_cost': reviewer.project.score_cost if reviewer.project else None,
                'project_score_willing_to_refer': reviewer.project.score_willing_to_refer if reviewer.project else None,
            }
            rows.append(row)
        return rows


class DataExporter:

    @staticmethod
    def export_to_json(data: List[ScrapedData], filename: str) -> None:
        json_data = [item.to_dict() for item in data]

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(data)} records to {filename}")

    @staticmethod
    def export_to_csv(data: List[ScrapedData], filename: str) -> None:
        if not data:
            print("No data to export")
            return

        all_rows = []
        for item in data:
            all_rows.extend(item.to_flat_dict_list())

        if not all_rows:
            print("No data to export")
            return

        fieldnames = all_rows[0].keys()

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for row in all_rows:
                writer.writerow(row)

        print(f"Exported {len(all_rows)} rows from {len(data)} companies to {filename}")


DEVELOPMENT_SUBCATEGORIES = {
    'https://clutch.co/directory/mobile-application-developers': 'Mobile Apps',
    'https://clutch.co/directory/iphone-application-developers': 'iPhone Apps',
    'https://clutch.co/directory/android-application-developers': 'Android Apps',
    'https://clutch.co/directory/game-mobile-app-developers': 'Gaming Apps',
    'https://clutch.co/app-developers/financial': 'Finance Apps',
    'https://clutch.co/developers': 'Software Developers',
    'https://clutch.co/developers/testing': 'Software Testing',
    'https://clutch.co/developers/laravel': 'Laravel',
    'https://clutch.co/it-services/microsoft-sharepoint': 'Microsoft Sharepoint',
    'https://clutch.co/developers/webflow': 'Webflow',
    'https://clutch.co/web-developers': 'Web Developers',
    'https://clutch.co/developers/python-django': 'Python & Django',
    'https://clutch.co/web-developers/php': 'PHP',
    'https://clutch.co/developers/wordpress': 'Wordpress',
    'https://clutch.co/developers/drupal': 'Drupal',
    'https://clutch.co/developers/artificial-intelligence': 'Artificial Intelligence',
    'https://clutch.co/developers/blockchain': 'Blockchain',
    'https://clutch.co/developers/virtual-reality': 'AR/VR',
    'https://clutch.co/developers/internet-of-things': 'IoT',
    'https://clutch.co/developers/react-native': 'React Native',
    'https://clutch.co/developers/flutter': 'Flutter',
    'https://clutch.co/developers/dot-net': 'DOTNET',
    'https://clutch.co/developers/ruby-rails': 'Ruby on Rails',
    'https://clutch.co/web-developers/javascript': 'JavaScript',
    'https://clutch.co/developers/ecommerce': 'E-Commerce Developers',
    'https://clutch.co/developers/magento': 'Magento',
    'https://clutch.co/developers/shopify': 'Shopify',
    'https://clutch.co/developers/bigcommerce': 'BigCommerce',
    'https://clutch.co/developers/woocommerce': 'WooCommerce',
}


def get_subcategory_urls() -> Dict[str, str]:
    urls = {}
    for url, name in DEVELOPMENT_SUBCATEGORIES.items():
        urls[name] = url
    return urls


if __name__ == "__main__":
    print("Testing data models...")

    reviewer1 = ReviewerInfo(
        name="John Smith",
        job_title="CTO",
        company="StartupXYZ",
        industry="Technology",
        location="Austin, TX",
        company_size="50-100 employees",
        project=ProjectInfo(
            service_provided="Custom Software Development",
            project_size="$50,000 - $100,000",
            start_date="Jan 2023",
            end_date="Jun 2023",
            score=4.8
        )
    )

    reviewer2 = ReviewerInfo(
        name="Jane Doe",
        job_title="Product Manager",
        company="E-commerce Inc",
        industry="Retail",
        location="Seattle, WA",
        company_size="100-500 employees",
        project=ProjectInfo(
            service_provided="Web Development",
            project_size="$75,000",
            start_date="Mar 2023",
            end_date="Aug 2023",
            score=4.5
        )
    )

    sample_data = ScrapedData(
        subcategory="Software Developers",
        competitor=CompetitorInfo(
            name="Tech Solutions Inc",
            locations=["New York, NY", "San Francisco, CA"]
        ),
        reviewers=[reviewer1, reviewer2],
        source_url="https://clutch.co/profile/tech-solutions-inc"
    )

    print("Sample flat dict:")
    for row in sample_data.to_flat_dict_list():
        for key, value in row.items():
            print(f"  {key}: {value}")
        break

    print(f"\nAvailable subcategories: {len(DEVELOPMENT_SUBCATEGORIES)}")
    for name, url in get_subcategory_urls().items():
        print(f"  {name}: {url}")