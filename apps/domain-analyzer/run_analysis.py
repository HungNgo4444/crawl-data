"""
Script chính để chạy domain analysis với database
Usage: python run_analysis.py [domain_name]
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.main import DomainAnalysisOrchestrator
import logging

# Setup logging với encoding UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def main():
    """Main function"""
    orchestrator = DomainAnalysisOrchestrator()
    
    if len(sys.argv) > 1:
        domain_name = sys.argv[1]
        print(f"Analyzing domain: {domain_name}")
        success = orchestrator.run_analysis(domain_name)
    else:
        print("Analyzing all active domains")
        success = orchestrator.run_analysis()
    
    if success:
        print("[SUCCESS] Analysis completed!")
    else:
        print("[ERROR] Analysis failed!")

if __name__ == "__main__":
    main()