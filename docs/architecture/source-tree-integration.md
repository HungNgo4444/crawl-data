# Source Tree Integration

## Existing Project Structure
```plaintext
commercial-news-crawler/
├── docs/                            # Existing documentation
│   ├── architecture.md              # Current architecture document
│   ├── brainstorming-session-results.md
│   └── prd.md                       # Product requirements
├── .bmad-core/                      # BMad framework files
├── CLAUDE.md                        # Project instructions
└── README.md                        # Project overview
```

## New File Organization
```plaintext
commercial-news-crawler/
├── existing structure context
│   ├── apps/                       # New service containers
│   │   ├── domain-management-api/  # FastAPI backend service
│   │   │   ├── src/
│   │   │   │   ├── api/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── domains.py           # Domain CRUD endpoints
│   │   │   │   │   ├── analysis.py         # Analysis management endpoints
│   │   │   │   │   └── websocket.py        # Real-time updates
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── domain.py           # Domain data models
│   │   │   │   │   └── analysis.py         # Analysis data models
│   │   │   │   ├── services/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── domain_manager.py   # Domain business logic
│   │   │   │   │   └── analysis_service.py # Analysis coordination
│   │   │   │   ├── database.py             # Database connection
│   │   │   │   └── main.py                 # FastAPI application entry
│   │   │   ├── tests/
│   │   │   ├── Dockerfile
│   │   │   └── requirements.txt
│   │   ├── domain-management-ui/    # React frontend service  
│   │   │   ├── src/
│   │   │   │   ├── components/
│   │   │   │   │   ├── DomainList.tsx      # Domain management grid
│   │   │   │   │   ├── DomainForm.tsx      # Add/edit domain form
│   │   │   │   │   ├── AnalysisStatus.tsx  # Real-time status display
│   │   │   │   │   └── Dashboard.tsx       # Main dashboard layout
│   │   │   │   ├── services/
│   │   │   │   │   ├── api.ts              # API client functions
│   │   │   │   │   └── websocket.ts        # WebSocket connection management
│   │   │   │   ├── types/
│   │   │   │   │   ├── domain.ts           # TypeScript type definitions
│   │   │   │   │   └── analysis.ts         # Analysis type definitions
│   │   │   │   ├── App.tsx                 # Main React application
│   │   │   │   └── index.tsx               # Application entry point
│   │   │   ├── public/
│   │   │   ├── package.json
│   │   │   ├── Dockerfile
│   │   │   └── nginx.conf                  # Production nginx config
│   │   ├── gwen3-analysis-worker/   # GWEN-3 analysis service
│   │   │   ├── src/
│   │   │   │   ├── workers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── analysis_worker.py  # Main GWEN-3 analysis logic
│   │   │   │   │   └── scheduler.py        # Analysis job scheduling
│   │   │   │   ├── integrations/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── ollama_client.py    # GWEN-3 model interaction
│   │   │   │   │   └── template_generator.py # Parsing template creation
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── analysis.py         # Analysis data models
│   │   │   │   └── main.py                 # Worker service entry
│   │   │   ├── tests/
│   │   │   ├── Dockerfile
│   │   │   └── requirements.txt
│   │   └── enhanced-crawler-worker/ # Enhanced Crawl4AI integration
│   │       ├── src/
│   │       │   ├── workers/
│   │       │   │   ├── __init__.py
│   │       │   │   └── crawler_worker.py   # Template-based crawling
│   │       │   ├── integrations/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── crawl4ai_client.py  # Enhanced Crawl4AI integration
│   │       │   │   └── template_processor.py # Template-based extraction
│   │       │   └── main.py                 # Enhanced crawler entry
│   │       ├── tests/
│   │       ├── Dockerfile
│   │       └── requirements.txt
│   ├── infrastructure/              # Infrastructure as code
│   │   ├── docker/
│   │   │   ├── docker-compose.yml   # Main orchestration file
│   │   │   ├── docker-compose.dev.yml # Development overrides
│   │   │   ├── .env.example         # Environment template
│   │   │   └── nginx/
│   │   │       ├── nginx.conf       # Reverse proxy configuration
│   │   │       └── ssl/             # SSL certificates directory
│   │   └── scripts/                 # Operational scripts
│   │       ├── setup.sh             # Initial environment setup
│   │       ├── migrate.sh           # Database migration runner
│   │       └── health-check.sh      # System health verification
│   ├── config/                     # Configuration files
│   │   ├── database/
│   │   │   ├── migrations/          # Database schema migrations
│   │   │   └── seeds/               # Initial data setup
│   │   └── gwen3/
│   │       ├── model-config.yml     # GWEN-3 model parameters
│   │       └── analysis-prompts.yml # Analysis prompt templates
│   └── docs/                       # Enhanced documentation
│       ├── architecture.md          # This updated document
│       ├── api/                     # API documentation
│       │   ├── domain-management.md # Domain API documentation  
│       │   └── websocket.md         # WebSocket API documentation
│       └── deployment/
│           ├── development.md       # Local development setup
│           └── production.md        # Production deployment guide
```

## Integration Guidelines

- **File Naming:** Follow existing Python snake_case conventions, React PascalCase for components, kebab-case for directories
- **Folder Organization:** Service-based organization maintaining existing Docker Compose patterns với clear separation of concerns  
- **Import/Export Patterns:** Maintain existing patterns với __init__.py files, consistent module imports, shared utilities in common packages

---
