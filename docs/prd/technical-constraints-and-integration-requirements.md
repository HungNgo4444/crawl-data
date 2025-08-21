# Technical Constraints and Integration Requirements

## Existing Technology Stack

**Languages**: Python 3.11+ (core backend), JavaScript/TypeScript (React frontend)
**Frameworks**: FastAPI/Flask (API backend), React (frontend), LangChain (LLM orchestration)
**Database**: PostgreSQL 15+ (primary data store with JSONB support)
**LLM**: Ollama GWEN-3 8B (local deployment, 16GB RAM allocation)
**Cache**: Redis 7.x (session storage, pub/sub, queue management)
**Storage**: MinIO (S3-compatible object storage for media files)
**Orchestration**: Docker Compose (container deployment và management)
**Monitoring**: Prometheus (metrics), Grafana (dashboards), structured logging
**Web Crawling**: Crawl4AI (content extraction engine)

## Integration Approach

**Database Integration Strategy**: 
- Extend existing PostgreSQL schema với domain management tables
- JSONB columns cho GWEN-3 parsing templates và analysis results
- Maintain existing UUID patterns và indexing strategies
- Connection pooling shared giữa crawler workers và React API backend

**API Integration Strategy**:
- RESTful API endpoints following existing OpenAPI 3.0 specifications  
- React frontend consume APIs với axios/fetch
- WebSocket connections cho real-time domain analysis updates
- Authentication middleware consistent với existing security patterns

**Frontend Integration Strategy**:
- React SPA deployed alongside existing monitoring stack
- Nginx reverse proxy routing cho API và static assets
- State management với Redux/Zustand cho domain data
- Component library integration (Material-UI/Ant Design)

**Testing Integration Strategy**:
- Jest/React Testing Library cho frontend unit tests
- Pytest cho backend API testing  
- Integration tests cho GWEN-3 + Crawl4AI pipeline
- End-to-end testing với Playwright/Cypress

## Code Organization and Standards

**File Structure Approach**:
```
apps/
├── domain-management-api/     # FastAPI backend
├── domain-management-ui/      # React frontend  
├── crawler-worker/           # Enhanced với GWEN-3
├── gwen3-analysis-worker/    # Daily domain analysis
└── monitoring-api/           # Existing monitoring
```

**Naming Conventions**:
- Python: snake_case cho functions, PascalCase cho classes
- React: PascalCase cho components, camelCase cho props/functions
- Database: snake_case tables, columns với descriptive names
- API endpoints: kebab-case URLs (/api/domain-management)

**Coding Standards**:
- Python: Black formatting, flake8 linting, type hints required
- React: ESLint/Prettier, TypeScript strict mode, functional components
- API documentation: OpenAPI 3.0 với comprehensive examples
- Git: Conventional commits với clear PR descriptions

**Documentation Standards**:
- README files cho mỗi service với setup instructions
- API documentation auto-generated từ OpenAPI specs
- React Storybook cho component documentation
- Architecture decision records (ADRs) cho major technical choices

## Deployment and Operations

**Build Process Integration**:
- Docker multi-stage builds cho React production bundles
- Python requirements.txt với pinned versions
- Environment-specific configurations (.env files)
- CI/CD pipeline với automated testing và deployment

**Deployment Strategy**:
- Docker Compose orchestration với service dependencies
- Rolling updates cho zero-downtime deployments  
- Health checks cho tất cả services including GWEN-3
- Environment separation (development, staging, production)

**Monitoring and Logging**:
- Prometheus metrics cho React API performance
- Grafana dashboards cho domain analysis success rates
- Structured logging với correlation IDs across services
- Alert rules cho GWEN-3 model failures và domain parsing issues

**Configuration Management**:
- Environment variables cho sensitive data (DB credentials)
- ConfigMaps cho GWEN-3 model parameters
- Feature flags cho gradual rollout của new domain features
- Secrets management cho API keys và certificates

## Risk Assessment and Mitigation

**Technical Risks**:
- GWEN-3 8B model memory constraints với 16GB RAM limitation
- React frontend performance với 200+ domain real-time updates
- Database performance với high-frequency domain template lookups
- Ollama service stability under daily analysis workloads

**Integration Risks**:
- GWEN-3 + Crawl4AI pipeline compatibility issues
- React frontend authentication integration complexity
- PostgreSQL schema migrations affecting existing crawler functionality
- Docker container resource conflicts với memory-intensive GWEN-3

**Deployment Risks**:  
- Docker Compose service startup dependencies và ordering
- Network connectivity issues giữa React frontend và backend APIs
- Storage volume management cho MinIO và PostgreSQL data persistence
- SSL certificate management cho production HTTPS endpoints

**Mitigation Strategies**:
- GWEN-3 memory monitoring với automatic restart mechanisms
- React pagination và virtualization cho large domain lists
- Database query optimization và connection pool tuning
- Comprehensive health checks và circuit breaker patterns
- Blue-green deployment strategy với rollback capabilities
- Automated backup procedures cho critical data và configurations

---
