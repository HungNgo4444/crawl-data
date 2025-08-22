"""
Test Extraction Preview for Vietnamese News Domains
================================================

This script tests actual data extraction using sample HTML files from output folder
to show exactly what data will be extracted from each domain.

Usage:
    python test_extraction_preview.py
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

# Add the enhanced-crawler-worker to Python path
sys.path.append(str(Path(__file__).parent.parent / "apps" / "enhanced-crawler-worker" / "src"))

try:
    from workers.vietnamese_news_patterns import (
        VietnameseNewsSchemaFactory,
        VIETNAMESE_DOMAIN_PATTERNS,
        clean_vietnamese_title,
        is_vietnamese_content
    )
    print("✅ Successfully imported Vietnamese patterns module")
except ImportError as e:
    print(f"❌ Failed to import patterns module: {e}")
    sys.exit(1)

try:
    from lxml import html, etree
    print("✅ LXML available for HTML parsing")
except ImportError:
    print("❌ LXML not available. Install with: pip install lxml")
    sys.exit(1)

class ExtractionTester:
    """Test actual data extraction from sample HTML files"""
    
    def __init__(self, output_folder: Path):
        self.output_folder = output_folder
        self.results = {}
    
    def find_sample_files(self) -> Dict[str, List[Path]]:
        """Find HTML sample files for each domain"""
        sample_files = {}
        
        # Map domains to their file patterns
        domain_file_patterns = {
            "vnexpress.net": ["raw_html_vnexpress.net*", "raw_html_vnexpress_net*"],
            "dantri.com.vn": ["raw_html_dantri.com.vn*", "raw_html_dantri_com_vn*"], 
            "tuoitre.vn": ["raw_html_tuoitre.vn*", "raw_html_tuoitre_vn*"],
            "thanhnien.vn": ["raw_html_thanhnien.vn*", "raw_html_thanhnien_vn*"],
            "24h.com.vn": ["raw_html_www.24h.com.vn*", "raw_html_24h_com_vn*"],
            "vov.vn": ["raw_html_vov.vn*", "raw_html_vov_vn*"],
            "zingnews.vn": ["raw_html_zingnews.vn*", "raw_html_zingnews_vn*"],
            "cafef.vn": ["raw_html_cafef.vn*", "raw_html_cafef_vn*"],
            "baomoi.com": ["raw_html_baomoi.com*", "raw_html_baomoi_com*"]
        }
        
        print("🔍 Searching for sample HTML files...")
        
        for domain, patterns in domain_file_patterns.items():
            files = []
            for pattern in patterns:
                files.extend(self.output_folder.glob(pattern))
            
            if files:
                sample_files[domain] = files[:3]  # Max 3 files per domain
                print(f"   📰 {domain}: Found {len(files)} files, using {len(sample_files[domain])}")
            else:
                print(f"   ❌ {domain}: No sample files found")
        
        return sample_files
    
    def extract_from_html(self, html_content: str, domain: str, file_name: str) -> Dict[str, Any]:
        """Extract data from HTML content using domain patterns"""
        pattern = VIETNAMESE_DOMAIN_PATTERNS.get(domain)
        if not pattern:
            return {"error": "No pattern found for domain"}
        
        try:
            # Parse HTML
            tree = html.fromstring(html_content)
            
            # Extract using patterns
            extracted = {
                "domain": domain,
                "file": file_name,
                "extraction_method": "domain_pattern",
                "title": self._extract_field(tree, pattern.title_selectors, "title"),
                "content": self._extract_field(tree, pattern.content_selectors, "content", min_length=9999999999),
                "author": self._extract_field(tree, pattern.author_selectors, "author"),
                "publish_date": self._extract_field(tree, pattern.date_selectors, "date"),
                "category": self._extract_field(tree, pattern.category_selectors, "category"),
                "url_image": self._extract_image(tree, pattern.image_selectors)
            }
            
            # Clean title
            if extracted["title"]:
                extracted["title_cleaned"] = clean_vietnamese_title(extracted["title"], domain)
                extracted["title_cleaning_applied"] = extracted["title"] != extracted["title_cleaned"]
            
            # Check Vietnamese content
            if extracted["content"]:
                extracted["is_vietnamese"] = is_vietnamese_content(extracted["content"])
                extracted["content_length"] = len(extracted["content"])
                extracted["content_preview"] = extracted["content"][:200] + "..." if len(extracted["content"]) > 200 else extracted["content"]
            
            # Extract JSON-LD if available
            json_ld = self._extract_json_ld(html_content)
            if json_ld:
                extracted["json_ld_available"] = True
                extracted["json_ld_data"] = json_ld
            else:
                extracted["json_ld_available"] = False
            
            # Extract OG metadata
            og_data = self._extract_og_metadata(tree)
            if og_data:
                extracted["og_metadata"] = og_data
            
            # Quality assessment
            extracted["quality_score"] = self._assess_quality(extracted)
            
            return extracted
            
        except Exception as e:
            return {"error": f"Extraction failed: {str(e)}", "domain": domain, "file": file_name}
    
    def _extract_field(self, tree, selectors: List[str], field_type: str, min_length: int = 1) -> Optional[str]:
        """Extract field using CSS selectors"""
        for selector in selectors:
            try:
                elements = tree.cssselect(selector)
                if elements:
                    text = elements[0].text_content().strip()
                    if text and len(text) >= min_length:
                        # Clean whitespace
                        text = re.sub(r'\s+', ' ', text)
                        return text
            except Exception:
                continue
        return None
    
    def _extract_image(self, tree, selectors: List[str]) -> Optional[str]:
        """Extract image URL"""
        for selector in selectors:
            try:
                elements = tree.cssselect(selector)
                if elements:
                    img_src = elements[0].get('src') or elements[0].get('data-src')
                    if img_src:
                        return img_src
            except Exception:
                continue
        return None
    
    def _extract_json_ld(self, html_content: str) -> Optional[Dict]:
        """Extract JSON-LD structured data"""
        try:
            pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                try:
                    data = json.loads(match.strip())
                    if isinstance(data, dict) and data.get("@type") in ["Article", "NewsArticle"]:
                        return {
                            "type": data.get("@type"),
                            "headline": data.get("headline"),
                            "author": data.get("author", {}).get("name") if isinstance(data.get("author"), dict) else data.get("author"),
                            "datePublished": data.get("datePublished"),
                            "articleSection": data.get("articleSection"),
                            "image": data.get("image")
                        }
                except json.JSONDecodeError:
                    continue
            return None
        except Exception:
            return None
    
    def _extract_og_metadata(self, tree) -> Dict[str, str]:
        """Extract Open Graph metadata"""
        og_data = {}
        
        og_tags = {
            "og:title": "title",
            "og:description": "description", 
            "og:image": "image",
            "og:type": "type",
            "og:url": "url"
        }
        
        for og_property, key in og_tags.items():
            try:
                elements = tree.cssselect(f'meta[property="{og_property}"]')
                if elements:
                    content = elements[0].get('content')
                    if content:
                        og_data[key] = content
            except Exception:
                continue
        
        return og_data
    
    def _assess_quality(self, extracted: Dict[str, Any]) -> float:
        """Assess extraction quality (0-1 score)"""
        score = 0.0
        
        # Title quality (30%)
        if extracted.get("title"):
            score += 0.3
            if len(extracted["title"]) > 10:
                score += 0.1
        
        # Content quality (40%)
        if extracted.get("content"):
            content_len = len(extracted["content"])
            if content_len > 200:
                score += 0.4
            elif content_len > 50:
                score += 0.2
        
        # Author presence (10%)
        if extracted.get("author"):
            score += 0.1
        
        # Date presence (10%)
        if extracted.get("publish_date"):
            score += 0.1
        
        # Category presence (5%)
        if extracted.get("category"):
            score += 0.05
        
        # Image presence (5%)
        if extracted.get("url_image"):
            score += 0.05
        
        return min(score, 1.0)
    
    def test_domain_extraction(self, domain: str, files: List[Path]) -> List[Dict[str, Any]]:
        """Test extraction for a specific domain"""
        print(f"\n🧪 Testing extraction for {domain}")
        print("-" * 50)
        
        results = []
        
        for file_path in files:
            print(f"   📄 Processing {file_path.name}...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                result = self.extract_from_html(html_content, domain, file_path.name)
                results.append(result)
                
                # Print extraction preview
                if "error" not in result:
                    print(f"      ✅ Title: {result.get('title_cleaned', 'N/A')[:60]}...")
                    print(f"      📝 Content: {result.get('content_length', 0)} chars")
                    print(f"      👤 Author: {result.get('author', 'N/A')}")
                    print(f"      📅 Date: {result.get('publish_date', 'N/A')}")
                    print(f"      🏷️ Category: {result.get('category', 'N/A')}")
                    print(f"      🖼️ Image: {'Yes' if result.get('url_image') else 'No'}")
                    print(f"      🇻🇳 Vietnamese: {result.get('is_vietnamese', False)}")
                    print(f"      ⭐ Quality: {result.get('quality_score', 0):.2f}")
                    print(f"      📊 JSON-LD: {'Yes' if result.get('json_ld_available') else 'No'}")
                else:
                    print(f"      ❌ Error: {result['error']}")
                
            except Exception as e:
                print(f"      ❌ Failed to process {file_path.name}: {e}")
                results.append({"error": str(e), "domain": domain, "file": file_path.name})
        
        return results
    
    def generate_extraction_report(self, all_results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Generate comprehensive extraction report"""
        print("\n📋 Generating Extraction Report...")
        
        report = {
            "timestamp": "2025-08-21T12:00:00Z",
            "test_summary": {
                "total_domains": len(all_results),
                "total_files": sum(len(results) for results in all_results.values()),
                "successful_extractions": 0,
                "failed_extractions": 0
            },
            "domain_results": {},
            "overall_statistics": {
                "avg_quality_score": 0,
                "fields_extraction_rates": {
                    "title": 0,
                    "content": 0, 
                    "author": 0,
                    "publish_date": 0,
                    "category": 0,
                    "url_image": 0
                },
                "vietnamese_content_rate": 0,
                "json_ld_availability": 0,
                "title_cleaning_applied": 0
            },
            "domain_specific_insights": {}
        }
        
        # Process results for each domain
        all_quality_scores = []
        field_counts = {"title": 0, "content": 0, "author": 0, "publish_date": 0, "category": 0, "url_image": 0}
        total_successful = 0
        vietnamese_count = 0
        json_ld_count = 0
        title_cleaned_count = 0
        
        for domain, results in all_results.items():
            domain_stats = {
                "total_files": len(results),
                "successful": 0,
                "failed": 0,
                "avg_quality": 0,
                "field_extraction_rates": {},
                "sample_extractions": []
            }
            
            domain_quality_scores = []
            domain_field_counts = {"title": 0, "content": 0, "author": 0, "publish_date": 0, "category": 0, "url_image": 0}
            
            for result in results:
                if "error" not in result:
                    domain_stats["successful"] += 1
                    total_successful += 1
                    
                    # Quality score
                    quality = result.get("quality_score", 0)
                    domain_quality_scores.append(quality)
                    all_quality_scores.append(quality)
                    
                    # Field extraction
                    for field in field_counts:
                        if result.get(field):
                            domain_field_counts[field] += 1
                            field_counts[field] += 1
                    
                    # Vietnamese content
                    if result.get("is_vietnamese"):
                        vietnamese_count += 1
                    
                    # JSON-LD availability
                    if result.get("json_ld_available"):
                        json_ld_count += 1
                    
                    # Title cleaning
                    if result.get("title_cleaning_applied"):
                        title_cleaned_count += 1
                    
                    # Add sample extraction (first successful one)
                    if not domain_stats["sample_extractions"]:
                        domain_stats["sample_extractions"].append({
                            "file": result["file"],
                            "title_original": result.get("title"),
                            "title_cleaned": result.get("title_cleaned"),
                            "content_preview": result.get("content_preview"),
                            "author": result.get("author"),
                            "publish_date": result.get("publish_date"),
                            "category": result.get("category"),
                            "url_image": result.get("url_image"),
                            "quality_score": result.get("quality_score"),
                            "json_ld_data": result.get("json_ld_data"),
                            "og_metadata": result.get("og_metadata")
                        })
                else:
                    domain_stats["failed"] += 1
                    report["test_summary"]["failed_extractions"] += 1
            
            # Calculate domain averages
            if domain_quality_scores:
                domain_stats["avg_quality"] = sum(domain_quality_scores) / len(domain_quality_scores)
            
            for field, count in domain_field_counts.items():
                domain_stats["field_extraction_rates"][field] = count / domain_stats["successful"] if domain_stats["successful"] > 0 else 0
            
            report["domain_results"][domain] = domain_stats
            
            # Domain-specific insights
            pattern = VIETNAMESE_DOMAIN_PATTERNS.get(domain)
            if pattern:
                report["domain_specific_insights"][domain] = {
                    "total_selectors": {
                        "title": len(pattern.title_selectors),
                        "content": len(pattern.content_selectors),
                        "author": len(pattern.author_selectors),
                        "date": len(pattern.date_selectors),
                        "category": len(pattern.category_selectors),
                        "image": len(pattern.image_selectors)
                    },
                    "performance_config": {
                        "javascript_required": pattern.javascript_required,
                        "dynamic_content": pattern.dynamic_content
                    },
                    "extraction_success_rate": domain_stats["successful"] / domain_stats["total_files"] if domain_stats["total_files"] > 0 else 0
                }
        
        # Calculate overall statistics
        report["test_summary"]["successful_extractions"] = total_successful
        
        if all_quality_scores:
            report["overall_statistics"]["avg_quality_score"] = sum(all_quality_scores) / len(all_quality_scores)
        
        for field, count in field_counts.items():
            report["overall_statistics"]["fields_extraction_rates"][field] = count / total_successful if total_successful > 0 else 0
        
        report["overall_statistics"]["vietnamese_content_rate"] = vietnamese_count / total_successful if total_successful > 0 else 0
        report["overall_statistics"]["json_ld_availability"] = json_ld_count / total_successful if total_successful > 0 else 0
        report["overall_statistics"]["title_cleaning_applied"] = title_cleaned_count / total_successful if total_successful > 0 else 0
        
        return report
    
    def print_detailed_report(self, report: Dict[str, Any]):
        """Print detailed extraction report"""
        print("\n" + "="*80)
        print("📊 VIETNAMESE NEWS EXTRACTION TEST REPORT")
        print("="*80)
        
        # Test Summary
        summary = report["test_summary"]
        print(f"\n📋 TEST SUMMARY:")
        print(f"   Total domains tested: {summary['total_domains']}")
        print(f"   Total files processed: {summary['total_files']}")
        print(f"   Successful extractions: {summary['successful_extractions']}")
        print(f"   Failed extractions: {summary['failed_extractions']}")
        print(f"   Success rate: {summary['successful_extractions']/(summary['successful_extractions']+summary['failed_extractions'])*100:.1f}%")
        
        # Overall Statistics
        stats = report["overall_statistics"]
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Average quality score: {stats['avg_quality_score']:.3f}")
        print(f"   Vietnamese content rate: {stats['vietnamese_content_rate']*100:.1f}%")
        print(f"   JSON-LD availability: {stats['json_ld_availability']*100:.1f}%")
        print(f"   Title cleaning applied: {stats['title_cleaning_applied']*100:.1f}%")
        
        print(f"\n🎯 FIELD EXTRACTION RATES:")
        for field, rate in stats["fields_extraction_rates"].items():
            print(f"   {field:15}: {rate*100:5.1f}%")
        
        # Domain-specific results
        print(f"\n🌐 DOMAIN-SPECIFIC RESULTS:")
        print("-" * 80)
        
        for domain, result in report["domain_results"].items():
            print(f"\n📰 {domain.upper()}")
            print(f"   Files tested: {result['total_files']}")
            print(f"   Success rate: {result['successful']}/{result['total_files']} ({result['successful']/result['total_files']*100:.1f}%)")
            print(f"   Avg quality: {result['avg_quality']:.3f}")
            
            print(f"   Field extraction rates:")
            for field, rate in result["field_extraction_rates"].items():
                print(f"      {field:12}: {rate*100:5.1f}%")
            
            # Show sample extraction
            if result["sample_extractions"]:
                sample = result["sample_extractions"][0]
                print(f"   📄 SAMPLE EXTRACTION ({sample['file']}):")
                print(f"      Title: {sample.get('title_cleaned', 'N/A')}")
                print(f"      Author: {sample.get('author', 'N/A')}")
                print(f"      Date: {sample.get('publish_date', 'N/A')}")
                print(f"      Category: {sample.get('category', 'N/A')}")
                print(f"      Content: {sample.get('content_preview', 'N/A')}")
                print(f"      Quality: {sample.get('quality_score', 0):.3f}")
            
            # Domain insights
            if domain in report["domain_specific_insights"]:
                insights = report["domain_specific_insights"][domain]
                print(f"   🔧 CONFIGURATION:")
                total_selectors = sum(insights["total_selectors"].values())
                print(f"      Total selectors: {total_selectors}")
                print(f"      JavaScript required: {insights['performance_config']['javascript_required']}")
                print(f"      Dynamic content: {insights['performance_config']['dynamic_content']}")
                print(f"      Success rate: {insights['extraction_success_rate']*100:.1f}%")

def main():
    """Main execution function"""
    print("🧪 Vietnamese News Extraction Preview Test")
    print("=" * 60)
    
    # Find output folder
    output_folder = Path(__file__).parent.parent / "output"
    if not output_folder.exists():
        print(f"❌ Output folder not found: {output_folder}")
        return 1
    
    print(f"📁 Using output folder: {output_folder}")
    
    # Initialize tester
    tester = ExtractionTester(output_folder)
    
    # Find sample files
    sample_files = tester.find_sample_files()
    if not sample_files:
        print("❌ No sample files found")
        return 1
    
    print(f"\n🔍 Found sample files for {len(sample_files)} domains")
    
    # Test extraction for each domain
    all_results = {}
    
    for domain, files in sample_files.items():
        results = tester.test_domain_extraction(domain, files)
        all_results[domain] = results
    
    # Generate and display report
    report = tester.generate_extraction_report(all_results)
    tester.print_detailed_report(report)
    
    # Save detailed report
    report_path = Path(__file__).parent / "vietnamese_extraction_test_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed report saved to: {report_path}")
    print("\n🎉 Extraction testing completed!")
    print("✅ This shows exactly what data will be extracted from each domain")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)