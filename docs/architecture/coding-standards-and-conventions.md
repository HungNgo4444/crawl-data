# Coding Standards and Conventions

## Existing Standards Compliance

**Code Style:**
- **Python**: Black formatting (line length 88), flake8 linting với existing .flake8 configuration, type hints mandatory cho all functions
- **React/TypeScript**: ESLint với airbnb-typescript config, Prettier formatting, strict TypeScript mode enabled
- **Docker**: Multi-stage builds với non-root user patterns, health check endpoints required
- **SQL**: Snake_case naming conventions, explicit schema definitions, proper indexing strategies

**Linting Rules:**
- **Python**: flake8 với complexity limits (max-complexity=10), import ordering với isort, docstring requirements cho public functions
- **TypeScript**: ESLint strict mode, no-unused-vars enforcement, consistent-type-definitions, explicit return types
- **YAML/JSON**: Consistent indentation (2 spaces), alphabetical key ordering where logical
- **Dockerfile**: hadolint compliance, security best practices, minimal layer approach

**Testing Patterns:**
- **Python**: pytest với asyncio support, SQLAlchemy test fixtures, mock patterns for external services
- **React**: Jest + React Testing Library, component testing với user interactions, integration tests cho API calls
- **API**: OpenAPI spec compliance testing, endpoint contract validation, authentication flow testing
- **Integration**: Docker Compose test environments, database migration testing, service health check validation

**Documentation Style:**
- **Python**: Google-style docstrings với type annotations, inline comments cho complex business logic
- **React**: JSDoc comments cho complex components, README files cho setup instructions  
- **API**: OpenAPI 3.0 specifications với comprehensive examples, error response documentation
- **Architecture**: Markdown với Mermaid diagrams, decision records cho major technical choices

## Enhancement-Specific Standards

- **GWEN-3 Integration**: Ollama client wrapper classes với connection pooling, error handling for model timeout scenarios
- **WebSocket Implementation**: Connection lifecycle management standards, message type validation, automatic reconnection logic
- **Domain Configuration**: Validation schemas cho domain URLs, sanitization patterns cho user inputs, configuration change audit logging
- **Template Processing**: JSONB schema validation, template versioning strategies, parsing confidence score thresholds
- **Real-time Updates**: Event-driven architecture patterns, message queue error handling, client-side state synchronization

## Critical Integration Rules

- **Existing API Compatibility**: All new endpoints follow existing OpenAPI patterns, maintain consistent error response formats, preserve authentication middleware integration
- **Database Integration**: New schema extends existing patterns without breaking changes, maintain UUID primary key consistency, follow existing JSONB usage patterns cho flexible data
- **Error Handling**: Structured logging với correlation IDs across services, consistent error response formats, graceful degradation cho external service failures
- **Logging Consistency**: JSON-formatted structured logging, log level consistency (DEBUG local, INFO production), sensitive data sanitization, performance metrics inclusion

---
