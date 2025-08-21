#!/usr/bin/env python3
"""
Test Database Setup Script
Creates database with Vietnamese news domains and sample crawl data
Author: Quinn (QA Architect)
Date: 2025-08-12
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseSetup:
    """Database setup for Vietnamese news domains testing"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'crawler_db'),
            'user': os.getenv('DB_USER', 'crawler_user'),
            'password': os.getenv('DB_PASSWORD', 'crawler_password')
        }
        
        self.migrations_path = Path(__file__).parent.parent.parent / 'config' / 'database' / 'migrations'
        
    async def connect(self) -> asyncpg.Connection:
        """Connect to PostgreSQL database"""
        try:
            connection = await asyncpg.connect(**self.db_config)
            logger.info(f"Connected to database: {self.db_config['host']}:{self.db_config['port']}")
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def run_migration_file(self, connection: asyncpg.Connection, migration_file: Path):
        """Run a single migration file"""
        try:
            logger.info(f"Running migration: {migration_file.name}")
            
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for stmt in statements:
                if stmt.strip():
                    await connection.execute(stmt)
            
            logger.info(f"✅ Migration {migration_file.name} completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Migration {migration_file.name} failed: {e}")
            raise
    
    async def setup_database(self):
        """Setup complete database with Vietnamese news domains"""
        connection = None
        try:
            connection = await self.connect()
            
            # Get migration files in order
            migration_files = [
                self.migrations_path / '005_vietnamese_news_domains.sql',
                self.migrations_path / '006_sample_crawl_data.sql'
            ]
            
            # Check if migration files exist
            for migration_file in migration_files:
                if not migration_file.exists():
                    logger.error(f"Migration file not found: {migration_file}")
                    return False
            
            # Run migrations
            for migration_file in migration_files:
                await self.run_migration_file(connection, migration_file)
            
            # Verify setup
            await self.verify_setup(connection)
            
            logger.info("🎉 Database setup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            return False
        finally:
            if connection:
                await connection.close()
    
    async def verify_setup(self, connection: asyncpg.Connection):
        """Verify database setup is correct"""
        logger.info("Verifying database setup...")
        
        # Check domain configurations
        domain_count = await connection.fetchval(
            "SELECT COUNT(*) FROM domain_configurations WHERE status = 'ACTIVE'"
        )
        logger.info(f"✅ Active domains: {domain_count}")
        
        # Check discovered URLs
        url_count = await connection.fetchval("SELECT COUNT(*) FROM discovered_urls")
        logger.info(f"✅ Discovered URLs: {url_count}")
        
        # Check analysis results
        analysis_count = await connection.fetchval("SELECT COUNT(*) FROM domain_analysis_results")
        logger.info(f"✅ Analysis results: {analysis_count}")
        
        # Check crawled articles
        article_count = await connection.fetchval("SELECT COUNT(*) FROM crawled_articles")
        logger.info(f"✅ Crawled articles: {article_count}")
        
        # Show sample domains
        domains = await connection.fetch("""
            SELECT domain_name, display_name, category, crawl_priority 
            FROM domain_configurations 
            WHERE status = 'ACTIVE' 
            ORDER BY crawl_priority, domain_name 
            LIMIT 10
        """)
        
        logger.info("📰 Sample Vietnamese news domains:")
        for domain in domains:
            logger.info(f"  • {domain['display_name']} ({domain['domain_name']}) - {domain['category']} [Priority: {domain['crawl_priority']}]")
    
    async def get_database_stats(self):
        """Get comprehensive database statistics"""
        connection = None
        try:
            connection = await self.connect()
            
            stats = {}
            
            # Domain statistics
            stats['domains'] = await connection.fetch("""
                SELECT 
                    category,
                    COUNT(*) as count,
                    AVG(crawl_priority) as avg_priority
                FROM domain_configurations 
                WHERE status = 'ACTIVE'
                GROUP BY category 
                ORDER BY count DESC
            """)
            
            # URL discovery statistics
            stats['url_types'] = await connection.fetch("""
                SELECT 
                    url_type,
                    COUNT(*) as count,
                    AVG(confidence_score) as avg_confidence
                FROM discovered_urls 
                GROUP BY url_type 
                ORDER BY count DESC
            """)
            
            # Analysis statistics
            stats['analysis_status'] = await connection.fetch("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(overall_confidence_score) as avg_confidence,
                    AVG(analysis_duration_seconds) as avg_duration
                FROM domain_analysis_results 
                GROUP BY status
            """)
            
            # Recent activity
            stats['recent_activity'] = await connection.fetch("""
                SELECT 
                    domain_name,
                    status,
                    overall_confidence_score,
                    analysis_timestamp
                FROM domain_analysis_results 
                ORDER BY analysis_timestamp DESC 
                LIMIT 5
            """)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
        finally:
            if connection:
                await connection.close()
    
    async def reset_database(self):
        """Reset database by dropping and recreating tables"""
        connection = None
        try:
            connection = await self.connect()
            
            logger.info("🔄 Resetting database...")
            
            # Drop tables in correct order (reverse of dependencies)
            drop_statements = [
                "DROP TABLE IF EXISTS crawled_articles CASCADE;",
                "DROP TABLE IF EXISTS discovered_urls CASCADE;",
                "DROP TABLE IF EXISTS domain_analysis_results CASCADE;",
                "DROP TABLE IF EXISTS domain_configurations CASCADE;",
                "DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;"
            ]
            
            for stmt in drop_statements:
                await connection.execute(stmt)
            
            logger.info("✅ Database tables dropped")
            
            # Re-run setup
            await self.setup_database()
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False
        finally:
            if connection:
                await connection.close()


async def main():
    """Main function"""
    print("🚀 Vietnamese News Domains Database Setup")
    print("=" * 50)
    
    setup = DatabaseSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'reset':
            print("⚠️  Resetting database (this will delete all data)...")
            input("Press Enter to continue or Ctrl+C to cancel...")
            success = await setup.reset_database()
        elif command == 'stats':
            print("📊 Getting database statistics...")
            stats = await setup.get_database_stats()
            
            if stats:
                print("\n📰 Domain Categories:")
                for row in stats.get('domains', []):
                    print(f"  • {row['category']}: {row['count']} domains (avg priority: {row['avg_priority']:.1f})")
                
                print("\n🔗 URL Types:")
                for row in stats.get('url_types', []):
                    print(f"  • {row['url_type']}: {row['count']} URLs (confidence: {row['avg_confidence']:.2f})")
                
                print("\n📊 Analysis Results:")
                for row in stats.get('analysis_status', []):
                    print(f"  • {row['status']}: {row['count']} analyses (confidence: {row['avg_confidence']:.2f}, duration: {row['avg_duration']:.1f}s)")
                
                print("\n🕒 Recent Activity:")
                for row in stats.get('recent_activity', []):
                    print(f"  • {row['domain_name']}: {row['status']} (confidence: {row['overall_confidence_score']:.2f}) - {row['analysis_timestamp']}")
            
            return
        else:
            print(f"Unknown command: {command}")
            print("Available commands: reset, stats")
            return
    else:
        # Default: setup database
        success = await setup.setup_database()
    
    if success:
        print("\n🎉 Database setup completed!")
        print("\n📋 Next steps:")
        print("1. Start Analysis Worker: docker-compose up -d")
        print("2. Test domain analysis: curl -X POST http://localhost:8080/api/v1/analysis/trigger")
        print("3. View results: curl http://localhost:8080/api/v1/analysis/recent")
        print("4. Check database stats: python scripts/setup_test_database.py stats")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())