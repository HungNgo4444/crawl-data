# API Design and Integration

## API Integration Strategy
**API Integration Strategy:** RESTful endpoints following existing OpenAPI 3.0 patterns với WebSocket additions cho real-time features
**Authentication:** Integration với existing authentication middleware và security patterns from original architecture
**Versioning:** API versioning strategy consistent với existing endpoint patterns (v1 prefix maintained)

## New API Endpoints

### **Domain Management Endpoints**

#### **GET /api/v1/domains**
- **Method:** GET
- **Purpose:** Retrieve paginated list của all configured domains với filtering và sorting
- **Integration:** Extends existing API patterns với consistent response formatting

**Request**
```json
{
  "page": 1,
  "limit": 50,
  "status": "ACTIVE",
  "search": "vnexpress",
  "sort_by": "success_rate_24h",
  "sort_order": "desc"
}
```

**Response**
```json
{
  "domains": [
    {
      "id": "uuid-here",
      "domain_name": "vnexpress.net",
      "base_url": "https://vnexpress.net",
      "status": "ACTIVE",
      "crawl_frequency_hours": 1,
      "success_rate_24h": 0.95,
      "last_analyzed": "2025-08-11T10:30:00Z",
      "next_analysis_scheduled": "2025-08-12T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 203,
    "page": 1,
    "limit": 50,
    "total_pages": 5
  }
}
```

#### **POST /api/v1/domains**
- **Method:** POST  
- **Purpose:** Add new domain configuration với validation và initial analysis scheduling
- **Integration:** Follows existing validation patterns và error handling from current API structure

**Request**
```json
{
  "domain_name": "dantri.com.vn",
  "base_url": "https://dantri.com.vn",
  "crawl_frequency_hours": 2,
  "priority": 5
}
```

**Response**
```json
{
  "id": "new-uuid-here",
  "domain_name": "dantri.com.vn",
  "status": "PENDING_ANALYSIS",
  "message": "Domain added successfully. GWEN-3 analysis scheduled.",
  "next_analysis_scheduled": "2025-08-11T14:00:00Z"
}
```

#### **GET /api/v1/domains/{domain_id}/analysis-status**
- **Method:** GET
- **Purpose:** Real-time analysis status và parsing template information cho specific domain
- **Integration:** Provides detailed status information consistent với existing monitoring endpoint patterns

**Response**
```json
{
  "domain_id": "uuid-here",
  "analysis_status": "COMPLETED",
  "last_analysis_run": {
    "started_at": "2025-08-11T10:00:00Z",
    "completed_at": "2025-08-11T10:04:30Z",
    "duration_seconds": 270,
    "gwen3_model_version": "gwen-3-8b-v1.2"
  },
  "current_template": {
    "confidence_score": 0.92,
    "template_version": 3,
    "expires_at": "2025-08-12T10:00:00Z"
  },
  "performance_metrics": {
    "extraction_success_rate": 0.89,
    "avg_extraction_time_ms": 1250
  }
}
```

### **Real-time WebSocket Endpoints**

#### **WebSocket /ws/domain-analysis-updates**
- **Method:** WebSocket Connection
- **Purpose:** Real-time updates cho React interface về domain analysis progress và status changes
- **Integration:** New WebSocket capability adding real-time features to existing API infrastructure

**Connection Messages**
```json
{
  "type": "analysis_started",
  "domain_id": "uuid-here", 
  "domain_name": "vnexpress.net",
  "estimated_duration_minutes": 5
}

{
  "type": "analysis_completed",
  "domain_id": "uuid-here",
  "template_confidence": 0.94,
  "performance_improvement": 0.12
}

{
  "type": "analysis_failed", 
  "domain_id": "uuid-here",
  "error_message": "GWEN-3 model timeout after 300 seconds",
  "retry_scheduled": "2025-08-11T12:00:00Z"
}
```

---
