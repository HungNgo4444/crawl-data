#!/usr/bin/env python3
"""
Script để tạo tất cả tables trong database production
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from storage_layer.database.database_manager import get_db_manager
from storage_layer.database.models import Base
from sqlalchemy import create_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_all_tables():
    """Tạo tất cả tables từ SQLAlchemy models"""
    try:
        # Get database manager
        db_manager = get_db_manager()
        logger.info("✅ Database connection successful!")
        
        # Create all tables
        engine = db_manager.get_engine()
        logger.info("🔧 Creating all tables from models...")
        
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ All tables created successfully!")
        
        # Test by listing all tables
        with db_manager.get_session() as session:
            result = session.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name
            """)
            tables = result.fetchall()
            
            logger.info("📋 Created tables:")
            for schema, table in tables:
                logger.info(f"   • {schema}.{table}")
                
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_all_tables())