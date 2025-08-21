# Tech Stack Alignment

## Existing Technology Stack

| Category | Current Technology | Version | Usage in Enhancement | Notes |
|----------|-------------------|---------|---------------------|-------|
| Backend Language | Python | 3.11+ | Core backend cho all new services | Maintain existing patterns |
| Web Framework | FastAPI/Flask | Latest | Domain management API, React backend | Follow existing API patterns |
| Database | PostgreSQL | 15+ | Extended với domain management schema | JSONB support cho GWEN-3 results |
| Cache/Queue | Redis | 7.x | Domain analysis queuing, template caching | Existing pub/sub patterns |
| Object Storage | MinIO | Latest | Media files từ 200+ domains | S3-compatible API maintained |
| LLM Processing | Ollama | Latest | GWEN-3 8B model hosting | Enhanced với specific model |
| Container Platform | Docker Compose | Latest | All services orchestration | Existing patterns extended |
| Monitoring | Prometheus | Latest | Enhanced với domain analysis metrics | Existing metrics infrastructure |
| Dashboards | Grafana | Latest | Domain management dashboards | Integrated với existing setup |
| Reverse Proxy | Nginx | Latest | React app routing, API gateway | Existing proxy patterns |
| Frontend | React | 18+ | NEW - Admin interface | Addition to existing stack |

## New Technology Additions

| Technology | Version | Purpose | Rationale | Integration Method |
|-----------|---------|---------|-----------|-------------------|
| GWEN-3 8B | Latest via Ollama | Vietnamese content analysis | Specialized Vietnamese language model cho news parsing | Deployed trong existing Ollama container |
| React | 18+ | Domain management interface | Modern admin interface cho 200+ domain management | New service trong Docker Compose |
| TypeScript | 5+ | React development | Type safety cho complex domain management logic | Development dependency only |
| Material-UI/Ant Design | Latest | UI component library | Professional, consistent interface components | React application dependency |
| WebSocket | Native | Real-time updates | Live domain analysis status trong admin interface | Integrated với existing FastAPI backend |

---
