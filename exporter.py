

import json
import csv
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

from models import ScrapedData
from exceptions import ExportError

class AdvancedDataExporter:

    def __init__(self, output_directory: str = "output"):
        
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)

    def export_all_formats(self, data: List[ScrapedData], base_filename: str = None) -> Dict[str, str]:
        
        if not base_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"clutch_data_{timestamp}"

        exported_files = {}

        try:

            json_file = self.export_to_json(data, f"{base_filename}.json")
            exported_files['json'] = json_file

            csv_file = self.export_to_csv(data, f"{base_filename}.csv")
            exported_files['csv'] = csv_file

            try:
                excel_file = self.export_to_excel(data, f"{base_filename}.xlsx")
                exported_files['excel'] = excel_file
            except ImportError:
                logging.warning("pandas not available, skipping Excel export")

            sqlite_file = self.export_to_sqlite(data, f"{base_filename}.db")
            exported_files['sqlite'] = sqlite_file

            summary_file = self.export_summary_report(data, f"{base_filename}_summary.txt")
            exported_files['summary'] = summary_file

            logging.info(f"Exported data to {len(exported_files)} formats")

        except Exception as e:
            raise ExportError(f"Error during export: {e}")

        return exported_files

    def export_to_json(self, data: List[ScrapedData], filename: str) -> str:
        
        try:
            output_path = self.output_directory / filename
            json_data = [item.to_dict() for item in data]

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)

            logging.info(f"Exported {len(data)} records to {output_path}")
            return str(output_path)

        except Exception as e:
            raise ExportError(f"JSON export failed: {e}", format_type="json", filename=filename)

    def export_to_csv(self, data: List[ScrapedData], filename: str) -> str:
        
        try:
            output_path = self.output_directory / filename

            if not data:
                logging.warning("No data to export to CSV")
                return str(output_path)

            first_record_rows = data[0].to_flat_dict_list()
            fieldnames = list(first_record_rows[0].keys()) if first_record_rows else []

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for item in data:
                    rows = item.to_flat_dict_list()
                    for row in rows:
                        writer.writerow(row)

            logging.info(f"Exported {len(data)} records to {output_path}")
            return str(output_path)

        except Exception as e:
            raise ExportError(f"CSV export failed: {e}", format_type="csv", filename=filename)

    def export_to_excel(self, data: List[ScrapedData], filename: str) -> str:
        
        try:
            import pandas as pd

            output_path = self.output_directory / filename

            if not data:
                logging.warning("No data to export to Excel")
                return str(output_path)

            flat_data = []
            for item in data:
                flat_data.extend(item.to_flat_dict_list())
            df = pd.DataFrame(flat_data)

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

                df.to_excel(writer, sheet_name='All Data', index=False)

                if 'subcategory' in df.columns:
                    summary = df.groupby('subcategory').size().reset_index(name='count')
                    summary.to_excel(writer, sheet_name='Summary by Category', index=False)

                if 'competitor_name' in df.columns:
                    companies = df['competitor_name'].value_counts().reset_index()
                    companies.columns = ['company', 'review_count']
                    companies.to_excel(writer, sheet_name='Companies Summary', index=False)

            logging.info(f"Exported {len(data)} records to {output_path}")
            return str(output_path)

        except ImportError:
            raise ExportError("pandas not available for Excel export", format_type="excel")
        except Exception as e:
            raise ExportError(f"Excel export failed: {e}", format_type="excel", filename=filename)

    def export_to_sqlite(self, data: List[ScrapedData], filename: str) -> str:
        
        try:
            output_path = self.output_directory / filename

            if output_path.exists():
                output_path.unlink()

            conn = sqlite3.connect(output_path)
            cursor = conn.cursor()

            if data:
                sample_rows = data[0].to_flat_dict_list()
                sample_dict = sample_rows[0] if sample_rows else {}
                columns = []
                for key in sample_dict.keys():

                    value = sample_dict[key]
                    if isinstance(value, (int, float)):
                        col_type = "REAL"
                    elif isinstance(value, bool):
                        col_type = "INTEGER"
                    else:
                        col_type = "TEXT"

                    columns.append(f"{key} {col_type}")

                create_table_sql = f"CREATE TABLE IF NOT EXISTS scraped_data ({', '.join(columns)})"
                cursor.execute(create_table_sql)

                placeholders = ', '.join(['?' for _ in sample_dict.keys()])
                insert_sql = f"INSERT INTO scraped_data ({', '.join(sample_dict.keys())}) VALUES ({placeholders})"

                for item in data:
                    flat_rows = item.to_flat_dict_list()
                    for flat_dict in flat_rows:
                        values = [flat_dict.get(key) for key in sample_dict.keys()]
                        cursor.execute(insert_sql, values)

                conn.commit()

            conn.close()

            logging.info(f"Exported {len(data)} records to SQLite database {output_path}")
            return str(output_path)

        except Exception as e:
            raise ExportError(f"SQLite export failed: {e}", format_type="sqlite", filename=filename)

    def export_summary_report(self, data: List[ScrapedData], filename: str) -> str:
        
        try:
            output_path = self.output_directory / filename

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("CLUTCH.CO SCRAPING SUMMARY REPORT\n")
                f.write("=" * 50 + "\n\n")

                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Records: {len(data)}\n\n")

                if not data:
                    f.write("No data to summarize.\n")
                    return str(output_path)

                subcategories = {}
                companies = set()
                reviewers = set()

                for item in data:
                    subcat = item.subcategory or "Unknown"
                    subcategories[subcat] = subcategories.get(subcat, 0) + 1

                    if item.competitor and item.competitor.name:
                        companies.add(item.competitor.name)

                    if item.reviewers:
                        for reviewer in item.reviewers:
                            if reviewer.name:
                                reviewers.add(reviewer.name)

                f.write("BREAKDOWN BY SUBCATEGORY:\n")
                f.write("-" * 30 + "\n")
                for subcat, count in sorted(subcategories.items()):
                    f.write(f"{subcat}: {count} records\n")

                f.write(f"\nUNIQUE COMPANIES: {len(companies)}\n")
                f.write(f"UNIQUE REVIEWERS: {len(reviewers)}\n\n")

                f.write("SAMPLE RECORDS:\n")
                f.write("-" * 20 + "\n")
                for i, item in enumerate(data[:5], 1):
                    f.write(f"\nRecord {i}:\n")
                    f.write(f"  Category: {item.subcategory}\n")
                    f.write(f"  Company: {item.competitor.name if item.competitor else 'N/A'}\n")
                    reviewers_str = ", ".join([r.name for r in item.reviewers if r.name]) if item.reviewers else "N/A"
                    f.write(f"  Reviewers: {reviewers_str}\n")
                    scores = [r.project.score for r in item.reviewers if r.project and r.project.score] if item.reviewers else []
                    avg_score = sum(scores) / len(scores) if scores else "N/A"
                    f.write(f"  Avg Project Score: {avg_score}\n")

                f.write("\nDATA QUALITY METRICS:\n")
                f.write("-" * 25 + "\n")

                company_names = sum(1 for item in data if item.competitor and item.competitor.name)
                reviewer_names = sum(len([r for r in item.reviewers if r.name]) for item in data if item.reviewers)
                project_scores = sum(len([r for r in item.reviewers if r.project and r.project.score]) for item in data if item.reviewers)

                f.write(f"Company names populated: {company_names}/{len(data)} ({company_names/len(data)*100:.1f}%)\n")
                f.write(f"Reviewer names populated: {reviewer_names}/{len(data)} ({reviewer_names/len(data)*100:.1f}%)\n")
                f.write(f"Project scores populated: {project_scores}/{len(data)} ({project_scores/len(data)*100:.1f}%)\n")

            logging.info(f"Generated summary report at {output_path}")
            return str(output_path)

        except Exception as e:
            raise ExportError(f"Summary report export failed: {e}", format_type="summary", filename=filename)

    def export_filtered_data(self, data: List[ScrapedData], filters: Dict[str, Any], filename: str) -> str:
        
        try:
            filtered_data = []

            for item in data:
                include = True

                for field, value in filters.items():
                    if field == 'subcategory' and item.subcategory != value:
                        include = False
                        break
                    elif field == 'company_name' and (not item.competitor or item.competitor.name != value):
                        include = False
                        break
                    elif field == 'min_score' and (not item.project or not item.project.score or item.project.score < value):
                        include = False
                        break

                if include:
                    filtered_data.append(item)

            output_path = self.export_to_csv(filtered_data, filename)
            logging.info(f"Exported {len(filtered_data)} filtered records (from {len(data)} total)")

            return output_path

        except Exception as e:
            raise ExportError(f"Filtered export failed: {e}", filename=filename)

if __name__ == "__main__":

    from models import CompetitorInfo, ReviewerInfo, ProjectInfo

    print("Testing AdvancedDataExporter...")

    sample_data = [
        ScrapedData(
            subcategory="Software Developers",
            competitor=CompetitorInfo(
                name="Tech Solutions Inc",
                locations=["New York, NY"]
            ),
            reviewer=ReviewerInfo(
                name="John Smith",
                job_title="CTO",
                company="StartupXYZ"
            ),
            project=ProjectInfo(
                service_provided="Custom Software Development",
                score=4.8
            )
        ),
        ScrapedData(
            subcategory="Web Developers",
            competitor=CompetitorInfo(
                name="Web Masters LLC",
                locations=["San Francisco, CA"]
            ),
            reviewer=ReviewerInfo(
                name="Jane Doe",
                job_title="Product Manager",
                company="BigCorp"
            ),
            project=ProjectInfo(
                service_provided="Website Development",
                score=4.5
            )
        )
    ]

    exporter = AdvancedDataExporter("test_output")

    try:
        exported_files = exporter.export_all_formats(sample_data, "test_data")
        print(f"Successfully exported to {len(exported_files)} formats:")
        for format_type, filepath in exported_files.items():
            print(f"  {format_type}: {filepath}")

        filtered_file = exporter.export_filtered_data(
            sample_data,
            {'subcategory': 'Software Developers'},
            "filtered_test.csv"
        )
        print(f"Filtered export: {filtered_file}")

    except ExportError as e:
        print(f"Export error: {e}")

    print("Exporter test completed.")