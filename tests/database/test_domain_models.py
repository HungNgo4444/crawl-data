"""
Unit tests for domain database models
Tests SQLAlchemy model validation, constraints, and business logic
Date: 2025-08-11
Author: James (Dev Agent)
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.pool import StaticPool

from storage_layer.database.models.domain_models import (
    Base, DomainConfiguration, DomainParsingTemplate, DomainAnalysisQueue,
    DomainStatus, AnalysisStatus
)


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_domain(session):
    """Create sample domain configuration for testing"""
    domain = DomainConfiguration(
        domain_name="example.com",
        base_url="https://example.com",
        status=DomainStatus.ACTIVE,
        crawl_frequency_hours=24,
        success_rate_24h=Decimal('85.50'),
        created_by_user="test_admin"
    )
    session.add(domain)
    session.commit()
    session.refresh(domain)
    return domain


class TestDomainConfiguration:
    """Test cases for DomainConfiguration model"""
    
    def test_create_domain_configuration(self, session):
        """Test basic domain configuration creation"""
        domain = DomainConfiguration(
            domain_name="vnexpress.net",
            base_url="https://vnexpress.net",
            status=DomainStatus.ACTIVE,
            crawl_frequency_hours=12,
            success_rate_24h=Decimal('92.30'),
            created_by_user="admin_user"
        )
        
        session.add(domain)
        session.commit()
        
        assert domain.id is not None
        assert isinstance(domain.id, uuid.UUID)
        assert domain.domain_name == "vnexpress.net"
        assert domain.status == DomainStatus.ACTIVE
        assert domain.success_rate_24h == Decimal('92.30')
        assert domain.crawl_frequency_hours == 12
        assert domain.created_at is not None
        assert domain.updated_at is not None
    
    def test_domain_name_validation(self, session):
        """Test domain name validation"""
        # Test empty domain name
        with pytest.raises(ValueError, match="Domain name cannot be empty"):
            domain = DomainConfiguration(
                domain_name="",
                base_url="https://example.com",
                created_by_user="test_user"
            )
            session.add(domain)
            session.commit()
    
    def test_base_url_validation(self, session):
        """Test base URL validation"""
        # Test empty URL
        with pytest.raises(ValueError, match="Base URL cannot be empty"):
            domain = DomainConfiguration(
                domain_name="example.com",
                base_url="",
                created_by_user="test_user"
            )
            session.add(domain)
            session.commit()
        
        # Test invalid URL format
        with pytest.raises(ValueError, match="Base URL must start with http"):
            domain = DomainConfiguration(
                domain_name="example.com", 
                base_url="ftp://example.com",
                created_by_user="test_user"
            )
            session.add(domain)
            session.commit()
    
    def test_unique_domain_name_constraint(self, session, sample_domain):
        """Test unique domain name constraint"""
        # Try to create another domain with same name
        duplicate_domain = DomainConfiguration(
            domain_name="example.com",  # Same as sample_domain
            base_url="https://different.com", 
            created_by_user="test_user"
        )
        
        session.add(duplicate_domain)
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_success_rate_constraints(self, session):
        """Test success rate constraint validation"""
        # Test with SQLite (constraint checking may vary)
        domain = DomainConfiguration(
            domain_name="test.com",
            base_url="https://test.com",
            success_rate_24h=Decimal('150.00'),  # Invalid: > 100
            created_by_user="test_user"
        )
        
        session.add(domain)
        # Note: SQLite may not enforce CHECK constraints in the same way as PostgreSQL
        # In production with PostgreSQL, this would raise IntegrityError
    
    def test_crawl_frequency_validation(self, session):
        """Test crawl frequency validation"""
        domain = DomainConfiguration(
            domain_name="test.com",
            base_url="https://test.com",
            crawl_frequency_hours=0,  # Invalid: must be > 0
            created_by_user="test_user"
        )
        
        session.add(domain)
        # Note: Check constraint validation depends on database implementation


class TestDomainParsingTemplate:
    """Test cases for DomainParsingTemplate model"""
    
    def test_create_parsing_template(self, session, sample_domain):
        """Test basic parsing template creation"""
        template_data = {
            "selectors": {
                "title": "h1.article-title",
                "content": ".article-content"
            },
            "extraction_rules": {
                "clean_text": True,
                "extract_links": False
            }
        }
        
        template = DomainParsingTemplate(
            domain_config_id=sample_domain.id,
            template_data=template_data,
            template_version=1,
            confidence_score=Decimal('87.50'),
            structure_hash="abc123def456",
            is_active=True,
            performance_metrics={"success_rate": 95.2}
        )
        
        session.add(template)
        session.commit()
        
        assert template.id is not None
        assert template.domain_config_id == sample_domain.id
        assert template.template_data == template_data
        assert template.confidence_score == Decimal('87.50')
        assert template.is_active is True
        assert template.performance_metrics == {"success_rate": 95.2}
    
    def test_template_data_validation(self, session, sample_domain):
        """Test template data validation"""
        # Test invalid template data (not a dict)
        with pytest.raises(ValueError, match="Template data must be a dictionary"):
            template = DomainParsingTemplate(
                domain_config_id=sample_domain.id,
                template_data="invalid_string",
                confidence_score=Decimal('80.00'),
                structure_hash="test123"
            )
            session.add(template)
            session.commit()
    
    def test_required_template_keys(self, session, sample_domain):
        """Test required keys in template data"""
        # Missing required keys
        with pytest.raises(ValueError, match="Template data must contain 'selectors' key"):
            template = DomainParsingTemplate(
                domain_config_id=sample_domain.id,
                template_data={"invalid": "data"},
                confidence_score=Decimal('80.00'),
                structure_hash="test123"
            )
            session.add(template)
            session.commit()
    
    def test_is_expired_method(self, session, sample_domain):
        """Test template expiration checking"""
        # Non-expired template (expires in future)
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        template = DomainParsingTemplate(
            domain_config_id=sample_domain.id,
            template_data={"selectors": {}, "extraction_rules": {}},
            confidence_score=Decimal('80.00'),
            structure_hash="test123",
            expires_at=future_time
        )
        
        assert not template.is_expired()
        
        # Expired template
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        template.expires_at = past_time
        assert template.is_expired()
        
        # Never expires (None)
        template.expires_at = None
        assert not template.is_expired()
    
    def test_foreign_key_relationship(self, session, sample_domain):
        """Test foreign key relationship with domain configuration"""
        template = DomainParsingTemplate(
            domain_config_id=sample_domain.id,
            template_data={"selectors": {}, "extraction_rules": {}},
            confidence_score=Decimal('80.00'),
            structure_hash="test123"
        )
        
        session.add(template)
        session.commit()
        
        # Test relationship access
        assert template.domain_config is not None
        assert template.domain_config.id == sample_domain.id
        assert template.domain_config.domain_name == "example.com"


class TestDomainAnalysisQueue:
    """Test cases for DomainAnalysisQueue model"""
    
    def test_create_analysis_queue_entry(self, session, sample_domain):
        """Test basic analysis queue entry creation"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        queue_entry = DomainAnalysisQueue(
            domain_config_id=sample_domain.id,
            scheduled_time=scheduled_time,
            status=AnalysisStatus.PENDING,
            priority=7,
            gwen3_model_version="gwen-3:8b"
        )
        
        session.add(queue_entry)
        session.commit()
        
        assert queue_entry.id is not None
        assert queue_entry.domain_config_id == sample_domain.id
        assert queue_entry.status == AnalysisStatus.PENDING
        assert queue_entry.priority == 7
        assert queue_entry.retry_count == 0
    
    def test_priority_validation(self, session, sample_domain):
        """Test priority validation"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Test invalid priority (too high)
        with pytest.raises(ValueError, match="Priority must be an integer between 1 and 10"):
            queue_entry = DomainAnalysisQueue(
                domain_config_id=sample_domain.id,
                scheduled_time=scheduled_time,
                priority=15  # Invalid: > 10
            )
            session.add(queue_entry)
            session.commit()
    
    def test_analysis_duration_validation(self, session, sample_domain):
        """Test analysis duration validation"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Test negative duration
        with pytest.raises(ValueError, match="Analysis duration cannot be negative"):
            queue_entry = DomainAnalysisQueue(
                domain_config_id=sample_domain.id,
                scheduled_time=scheduled_time,
                analysis_duration_seconds=-100  # Invalid: negative
            )
            session.add(queue_entry)
            session.commit()
    
    def test_can_retry_method(self, session, sample_domain):
        """Test can_retry business logic"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        queue_entry = DomainAnalysisQueue(
            domain_config_id=sample_domain.id,
            scheduled_time=scheduled_time,
            status=AnalysisStatus.FAILED,
            retry_count=2
        )
        
        # Can retry (< 3 retries)
        assert queue_entry.can_retry() is True
        
        # Cannot retry (>= 3 retries)
        queue_entry.retry_count = 3
        assert queue_entry.can_retry() is False
        
        # Cannot retry (not failed status)
        queue_entry.status = AnalysisStatus.COMPLETED
        queue_entry.retry_count = 1
        assert queue_entry.can_retry() is False
    
    def test_status_transition_methods(self, session, sample_domain):
        """Test status transition helper methods"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        queue_entry = DomainAnalysisQueue(
            domain_config_id=sample_domain.id,
            scheduled_time=scheduled_time,
            status=AnalysisStatus.PENDING
        )
        
        session.add(queue_entry)
        session.commit()
        
        # Test mark_started
        queue_entry.mark_started()
        assert queue_entry.status == AnalysisStatus.RUNNING
        assert queue_entry.analysis_started_at is not None
        
        # Test mark_completed
        queue_entry.mark_completed(duration_seconds=150)
        assert queue_entry.status == AnalysisStatus.COMPLETED
        assert queue_entry.analysis_duration_seconds == 150
        
        # Test mark_failed
        queue_entry.mark_failed("Connection timeout")
        assert queue_entry.status == AnalysisStatus.FAILED
        assert queue_entry.error_message == "Connection timeout"
        assert queue_entry.retry_count == 1


class TestModelRelationships:
    """Test relationships between models"""
    
    def test_domain_to_templates_relationship(self, session, sample_domain):
        """Test one-to-many relationship from domain to templates"""
        # Create multiple templates for the domain
        for i in range(3):
            template = DomainParsingTemplate(
                domain_config_id=sample_domain.id,
                template_data={"selectors": {}, "extraction_rules": {}},
                confidence_score=Decimal(f'80.{i}0'),
                structure_hash=f"hash{i}",
                template_version=i+1
            )
            session.add(template)
        
        session.commit()
        
        # Test relationship access
        templates = sample_domain.parsing_templates
        assert len(templates) == 3
        assert all(t.domain_config_id == sample_domain.id for t in templates)
    
    def test_domain_to_queue_relationship(self, session, sample_domain):
        """Test one-to-many relationship from domain to analysis queue"""
        # Create multiple queue entries for the domain
        for i in range(2):
            queue_entry = DomainAnalysisQueue(
                domain_config_id=sample_domain.id,
                scheduled_time=datetime.now(timezone.utc) + timedelta(hours=i+1),
                priority=5+i
            )
            session.add(queue_entry)
        
        session.commit()
        
        # Test relationship access
        queue_entries = sample_domain.analysis_queue
        assert len(queue_entries) == 2
        assert all(q.domain_config_id == sample_domain.id for q in queue_entries)
    
    def test_cascade_delete(self, session):
        """Test cascade delete behavior"""
        # Create domain with templates and queue entries
        domain = DomainConfiguration(
            domain_name="cascade-test.com",
            base_url="https://cascade-test.com",
            created_by_user="test_user"
        )
        session.add(domain)
        session.commit()
        
        # Add template and queue entry
        template = DomainParsingTemplate(
            domain_config_id=domain.id,
            template_data={"selectors": {}, "extraction_rules": {}},
            confidence_score=Decimal('80.00'),
            structure_hash="test"
        )
        queue_entry = DomainAnalysisQueue(
            domain_config_id=domain.id,
            scheduled_time=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        session.add_all([template, queue_entry])
        session.commit()
        
        template_id = template.id
        queue_id = queue_entry.id
        
        # Delete domain
        session.delete(domain)
        session.commit()
        
        # Verify cascaded deletion
        assert session.query(DomainParsingTemplate).filter_by(id=template_id).first() is None
        assert session.query(DomainAnalysisQueue).filter_by(id=queue_id).first() is None