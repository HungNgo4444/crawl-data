"""
Database Integration for GWEN-3 Domain Analysis Results
Lưu parsing templates vào PostgreSQL database
Author: Quinn (QA Agent)  
Date: 2025-08-12
"""

import asyncio
import asyncpg
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import asdict

from domain_analyzer import DomainAnalysisResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseIntegration:
    """Integration layer between GWEN-3 analysis và PostgreSQL database"""
    
    def __init__(self, connection_string: str = None):
        if connection_string is None:
            # Default connection for local development
            self.connection_string = (
                "postgresql://crawler_user:crawler123@localhost:5432/crawler_db"
            )
        else:
            self.connection_string = connection_string
        
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {str(e)}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def save_domain_analysis(self, 
                                 analysis_result: DomainAnalysisResult,
                                 created_by_user: str = "gwen3_analyzer") -> Optional[str]:
        """
        Lưu domain analysis result vào database
        Returns: domain_config_id nếu thành công
        """
        
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            try:
                # Start transaction
                async with conn.transaction():
                    
                    # 1. Upsert domain_configurations
                    domain_config_id = await self._upsert_domain_config(
                        conn, analysis_result, created_by_user
                    )
                    
                    # 2. Deactivate old templates
                    await self._deactivate_old_templates(conn, domain_config_id)
                    
                    # 3. Insert new parsing template
                    template_id = await self._insert_parsing_template(
                        conn, domain_config_id, analysis_result
                    )
                    
                    logger.info(
                        f"Saved analysis for {analysis_result.domain_name}: "
                        f"domain_id={domain_config_id}, template_id={template_id}"
                    )
                    
                    return domain_config_id
                    
            except Exception as e:
                logger.error(f"Failed to save analysis: {str(e)}")
                raise
    
    async def _upsert_domain_config(self, 
                                  conn: asyncpg.Connection,
                                  analysis_result: DomainAnalysisResult,
                                  created_by_user: str) -> str:
        """Upsert domain configuration"""
        
        # Check if domain exists
        existing_domain = await conn.fetchrow("""
            SELECT id FROM domain_configurations 
            WHERE domain_name = $1
        """, analysis_result.domain_name)
        
        if existing_domain:
            # Update existing domain
            await conn.execute("""
                UPDATE domain_configurations 
                SET 
                    base_url = $2,
                    last_analyzed = $3,
                    status = CASE 
                        WHEN $4 THEN 'ACTIVE'::domain_status 
                        ELSE 'FAILED'::domain_status 
                    END,
                    updated_at = NOW()
                WHERE domain_name = $1
            """, 
                analysis_result.domain_name,
                analysis_result.base_url,
                analysis_result.timestamp,
                analysis_result.is_valid
            )
            
            domain_config_id = existing_domain['id']
            logger.info(f"Updated existing domain config: {domain_config_id}")
            
        else:
            # Insert new domain  
            domain_config_id = await conn.fetchval("""
                INSERT INTO domain_configurations (
                    domain_name,
                    base_url,
                    status,
                    last_analyzed,
                    created_by_user
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """,
                analysis_result.domain_name,
                analysis_result.base_url,
                'ACTIVE' if analysis_result.is_valid else 'FAILED',
                analysis_result.timestamp,
                created_by_user
            )
            
            logger.info(f"Created new domain config: {domain_config_id}")
        
        return str(domain_config_id)
    
    async def _deactivate_old_templates(self, 
                                      conn: asyncpg.Connection,
                                      domain_config_id: str):
        """Deactivate old templates for domain"""
        
        updated_count = await conn.execute("""
            UPDATE domain_parsing_templates 
            SET is_active = false, updated_at = NOW()
            WHERE domain_config_id = $1 AND is_active = true
        """, domain_config_id)
        
        if updated_count != "UPDATE 0":
            logger.info(f"Deactivated old templates for domain {domain_config_id}")
    
    async def _insert_parsing_template(self,
                                     conn: asyncpg.Connection,
                                     domain_config_id: str,
                                     analysis_result: DomainAnalysisResult) -> str:
        """Insert new parsing template"""
        
        # Prepare performance metrics
        performance_metrics = {
            "analysis_duration_seconds": analysis_result.analysis_duration_seconds,
            "token_count": analysis_result.token_count,
            "model_name": analysis_result.model_name,
            "analysis_timestamp": analysis_result.timestamp.isoformat(),
            "validation_errors": analysis_result.validation_errors
        }
        
        # Calculate template version
        max_version = await conn.fetchval("""
            SELECT COALESCE(MAX(template_version), 0)
            FROM domain_parsing_templates 
            WHERE domain_config_id = $1
        """, domain_config_id)
        
        new_version = (max_version or 0) + 1
        
        # Insert new template
        template_id = await conn.fetchval("""
            INSERT INTO domain_parsing_templates (
                domain_config_id,
                template_data,
                template_version,
                confidence_score,
                structure_hash,
                is_active,
                created_by_analysis_run,
                performance_metrics
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """,
            domain_config_id,
            json.dumps(analysis_result.template_data),  # JSONB
            new_version,
            analysis_result.confidence_score,
            analysis_result.structure_hash,
            analysis_result.is_valid,  # Only activate if valid
            analysis_result.analysis_id,
            json.dumps(performance_metrics)  # JSONB
        )
        
        logger.info(f"Created new parsing template: {template_id} (version {new_version})")
        return str(template_id)
    
    async def get_active_template(self, domain_name: str) -> Optional[Dict[str, Any]]:
        """Lấy active parsing template cho domain"""
        
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            template = await conn.fetchrow("""
                SELECT 
                    dpt.template_data,
                    dpt.confidence_score,
                    dpt.structure_hash,
                    dpt.template_version,
                    dpt.created_at,
                    dc.base_url
                FROM domain_parsing_templates dpt
                JOIN domain_configurations dc ON dpt.domain_config_id = dc.id
                WHERE dc.domain_name = $1 
                  AND dpt.is_active = true
                ORDER BY dpt.created_at DESC
                LIMIT 1
            """, domain_name)
            
            if template:
                return {
                    "template_data": template['template_data'],
                    "confidence_score": float(template['confidence_score']),
                    "structure_hash": template['structure_hash'],
                    "template_version": template['template_version'],
                    "created_at": template['created_at'],
                    "base_url": template['base_url']
                }
            
            return None
    
    async def get_domain_stats(self) -> Dict[str, Any]:
        """Lấy thống kê domains đã analyze"""
        
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_domains,
                    COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_domains,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_domains,
                    AVG(
                        CASE WHEN last_analyzed IS NOT NULL 
                        THEN EXTRACT(EPOCH FROM (NOW() - last_analyzed))/3600 
                        END
                    ) as avg_hours_since_analysis
                FROM domain_configurations
            """)
            
            template_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_templates,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_templates,
                    AVG(confidence_score) as avg_confidence,
                    MAX(confidence_score) as max_confidence,
                    MIN(confidence_score) as min_confidence
                FROM domain_parsing_templates
            """)
            
            return {
                "domains": {
                    "total": stats['total_domains'],
                    "active": stats['active_domains'], 
                    "failed": stats['failed_domains'],
                    "avg_hours_since_analysis": float(stats['avg_hours_since_analysis'] or 0)
                },
                "templates": {
                    "total": template_stats['total_templates'],
                    "active": template_stats['active_templates'],
                    "avg_confidence": float(template_stats['avg_confidence'] or 0),
                    "max_confidence": float(template_stats['max_confidence'] or 0),
                    "min_confidence": float(template_stats['min_confidence'] or 0)
                }
            }

# Test function
async def test_database_integration():
    """Test database integration"""
    
    from domain_analyzer import DomainAnalyzer
    
    print("=== Testing Database Integration ===")
    
    # Initialize database
    db = DatabaseIntegration()
    
    try:
        await db.initialize()
        print("✅ Database connection successful")
        
        # Test domain analysis
        analyzer = DomainAnalyzer()
        
        sample_html = """
        <article class="news-article">
            <h1 class="headline">Test News Article</h1>
            <p class="summary">Article summary</p>
            <div class="content">Article content here</div>
            <time class="date">2025-08-12</time>
        </article>
        """
        
        # Analyze domain
        analysis_result = await analyzer.analyze_domain(
            domain_name="test-domain.com",
            html_content=sample_html,
            base_url="https://test-domain.com"
        )
        
        print(f"✅ Analysis completed: {analysis_result.confidence_score:.2f} confidence")
        
        # Save to database
        domain_config_id = await db.save_domain_analysis(
            analysis_result, 
            created_by_user="test_user"
        )
        
        print(f"✅ Saved to database: {domain_config_id}")
        
        # Retrieve active template
        template = await db.get_active_template("test-domain.com")
        if template:
            print(f"✅ Retrieved template: version {template['template_version']}")
        
        # Get stats
        stats = await db.get_domain_stats()
        print(f"✅ Database stats:")
        print(f"   Total domains: {stats['domains']['total']}")
        print(f"   Active templates: {stats['templates']['active']}")
        print(f"   Avg confidence: {stats['templates']['avg_confidence']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
        
    finally:
        await db.close()

if __name__ == "__main__":
    # Run test
    asyncio.run(test_database_integration())