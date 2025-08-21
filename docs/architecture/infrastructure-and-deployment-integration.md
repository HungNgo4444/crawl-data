# Infrastructure and Deployment Integration

## Existing Infrastructure
**Current Deployment:** Docker Compose orchestration trên Ubuntu VPS với self-hosted services
**Infrastructure Tools:** Docker Compose, Makefiles for operations, Nginx reverse proxy, PostgreSQL/Redis/MinIO stack
**Environments:** Development (local), Production (VPS) với environment-specific configurations

## Enhancement Deployment Strategy

**Deployment Approach:** 
- Extend existing Docker Compose với additional services cho new components
- Maintain single compose file approach với development overrides
- Use existing Nginx reverse proxy patterns cho React app routing
- Preserve existing database/Redis/MinIO shared service approach

**Infrastructure Changes:**
- **Memory Allocation**: Increase từ current baseline to 16GB total (8GB cho GWEN-3, 8GB cho other services)
- **New Services**: Add domain-management-api, domain-management-ui, gwen3-analysis-worker, enhanced-crawler-worker containers
- **Storage Requirements**: Add persistent volumes cho domain configurations, analysis templates, React build artifacts
- **Network Configuration**: Extend existing internal network với new service communication patterns

**Pipeline Integration:**
- Maintain existing build && deploy approach với enhanced health checks
- Add service-specific health endpoints cho new components (React app, GWEN-3 worker, domain API)
- Extend existing monitoring integration với new service metrics
- Use existing environment variable patterns cho configuration management

## Rollback Strategy

**Rollback Method:**
- Docker Compose service isolation enables individual service rollback without affecting existing crawler functionality
- Database schema migrations với backward compatibility ensure existing crawler continues operation
- Feature flags trong React interface allow gradual feature activation/deactivation
- GWEN-3 analysis worker can be disabled while maintaining existing 3-source crawling approach

**Risk Mitigation:**
- **Data Protection**: Database backups before schema migrations, separate domain management tables minimizes existing data risk
- **Service Isolation**: New services failures don't impact existing crawler operations due to queue-based loose coupling
- **Graceful Degradation**: Enhanced Crawl4AI worker falls back to existing extraction methods when templates unavailable
- **Resource Monitoring**: GWEN-3 memory usage monitoring với automatic restart prevents system-wide memory exhaustion

**Monitoring:**
- Extend existing Prometheus metrics collection với domain analysis performance tracking
- Add Grafana dashboards cho new service health, domain success rates, GWEN-3 model performance
- Enhance existing alert rules với domain management system failures, analysis queue overload warnings
- Maintain existing log aggregation patterns với structured logging from new services

---
