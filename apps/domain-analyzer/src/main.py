"""
Main script cho Domain Analyzer
Tự động phân tích domains và extract URLs sử dụng newspaper4k
"""
import logging
import sys
import traceback
from typing import List, Dict, Any

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer
from utils.database_utils import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('domain_analyzer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class DomainAnalysisOrchestrator:
    """Main orchestrator cho domain analysis"""
    
    def __init__(self):
        self.analyzer = Newspaper4kDomainAnalyzer()
        self.db_manager = DatabaseManager()
        
    def run_analysis(self, domain_name: str = None):
        """
        Run domain analysis cho một domain cụ thể hoặc tất cả domains
        
        Args:
            domain_name: Tên domain cần phân tích. Nếu None thì phân tích tất cả
        """
        logger.info("Starting domain analysis process...")
        
        # Ket noi database
        if not self.db_manager.connect():
            logger.error("Cannot connect to database")
            return False
        
        try:
            # Lấy domains từ database
            if domain_name:
                domains = [self.db_manager.get_domain_by_name(domain_name)]
                domains = [d for d in domains if d]  # Filter None
            else:
                domains = self.db_manager.get_active_domains()
            
            if not domains:
                logger.warning(f"No domains found for analysis")
                return False
            
            logger.info(f"Will analyze {len(domains)} domains")
            
            # Process từng domain
            for domain in domains:
                self._process_domain(domain)
                
            logger.info("Completed domain analysis process!")
            return True
            
        except Exception as e:
            logger.error(f"Error trong analysis process: {e}")
            traceback.print_exc()
            return False
        finally:
            self.db_manager.disconnect()
    
    def _process_domain(self, domain: Dict[str, Any]):
        """Process một domain cụ thể"""
        domain_id = domain['id']
        domain_name = domain['name']
        base_url = domain['base_url']
        
        logger.info(f"Processing domain: {domain_name} ({base_url})")
        
        try:
            # 1. Phân tích domain bằng newspaper4k
            analysis_result = self.analyzer.analyze_domain(base_url, domain_name)
            
            # 2. Update domains table với kết quả phân tích
            self._update_domain_analysis(domain_id, analysis_result)
            
            # 3. Phase 2: Extract article URLs from discovered sources
            article_urls = self.analyzer.extract_all_article_urls(base_url, domain_name, analysis_result)
            
            # 4. Lưu URLs vào url_tracking table
            success_count = self.db_manager.bulk_add_urls_to_tracking(
                article_urls, domain_id, 'newspaper4k-phase2'
            )
            
            logger.info(f"Domain {domain_name} processed successfully: "
                      f"{success_count}/{len(article_urls)} article URLs saved")
                      
        except Exception as e:
            logger.error(f"Error processing domain {domain_name}: {e}")
            traceback.print_exc()
    
    def _update_domain_analysis(self, domain_id: str, analysis_result: Dict[str, Any]):
        """Update domains table với analysis results"""
        try:
            update_data = {
                'rss_feeds': analysis_result.get('rss_feeds', []),
                'sitemaps': analysis_result.get('sitemaps', []),
                'homepage_urls': analysis_result.get('homepage_urls', []),
                'category_urls': analysis_result.get('category_urls', []),
                'css_selectors': analysis_result.get('css_selectors', {})
            }
            
            success = self.db_manager.update_domain_analysis(domain_id, update_data)
            if success:
                logger.info(f"Updated analysis data for domain {domain_id}")
            else:
                logger.warning(f"Failed to update analysis data for domain {domain_id}")
                
        except Exception as e:
            logger.error(f"Error updating domain analysis: {e}")

def main():
    """Main function"""
    orchestrator = DomainAnalysisOrchestrator()
    
    # Kiểm tra command line arguments
    if len(sys.argv) > 1:
        domain_name = sys.argv[1]
        logger.info(f"Analyzing specific domain: {domain_name}")
        orchestrator.run_analysis(domain_name)
    else:
        logger.info("Analyzing all active domains")
        orchestrator.run_analysis()

if __name__ == "__main__":
    main()