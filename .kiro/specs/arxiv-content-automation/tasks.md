# Implementation Plan

## Phase 1: Core Infrastructure and Manual Ingestion

**Success Criteria for Phase 1 Completion:**
- ✅ Database successfully stores papers with all required metadata fields
- ✅ All 4 manual input methods work reliably (ArXiv URL, PDF upload, title search, DOI)
- ✅ Can successfully ingest 10 test papers from your Notion database without errors
- ✅ Duplicate detection prevents re-ingestion of same papers
- ✅ Basic data validation ensures no corrupted or incomplete records
- ✅ Database queries perform adequately (< 100ms for basic lookups)

**Validation Tests:**
- Ingest the same paper via different methods (URL vs PDF) - should detect as duplicate
- Upload a malformed PDF - should handle gracefully with error message
- Search for paper by partial title - should return relevant matches
- Database can handle concurrent ingestion operations without corruption

- [x] 1. Set up project structure and database foundation
  - Create directory structure for services, models, and database components
  - Set up PostgreSQL database with pgvector extension (see deployment options below)
  - Create initial database schema for papers, insights, tags, and analysis tracking
  - Set up environment configuration and connection management
  - **Success Measure**: Database schema created, all tables accessible, pgvector extension working
  - _Requirements: 8.1, 8.2_

**Database Deployment Options:**

**Option 1: Local Development (Recommended for Phase 1)**
```bash
# Using Docker for local development
docker run --name arxiv-postgres \
  -e POSTGRES_DB=arxiv_automation \
  -e POSTGRES_USER=arxiv_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -v arxiv_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16

# Or using Homebrew on macOS
brew install postgresql@16
brew install pgvector
```

**Option 2: Cloud Hosted (For Production)**
- **Supabase**: Managed PostgreSQL with pgvector support, generous free tier
- **Neon**: Serverless PostgreSQL with vector support, good for development
- **AWS RDS**: Full control, requires manual pgvector setup
- **Google Cloud SQL**: Managed PostgreSQL with extensions

**Option 3: Hybrid Approach**
- Local PostgreSQL for development and testing
- Cloud database for production deployment
- Environment-based configuration to switch between them

**Recommended Approach:**
Start with **local Docker setup** for Phase 1 development, then migrate to **Supabase** or **Neon** for production. This gives you:
- Fast local development without network latency
- Easy backup/restore for testing
- Simple migration path to cloud when ready
- Cost-effective during development phase

- [ ] 2. Implement core data models and database operations
  - Create Paper, Insight, Tag, and Citation model classes with validation
  - Implement database repository pattern for CRUD operations
  - Add database migration system for schema evolution
  - Create indexes for performance optimization
  - Set up environment-based configuration (local vs cloud)
  - **Success Measure**: Can create, read, update, delete papers programmatically with data validation
  - _Requirements: 8.1, 8.6_

**Database Configuration Example:**
```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"

def get_database_config() -> DatabaseConfig:
    env = os.getenv("ENVIRONMENT", "local")
    
    if env == "local":
        return DatabaseConfig(
            host="localhost",
            port=5432,
            database="arxiv_automation",
            username="arxiv_user",
            password=os.getenv("DB_PASSWORD", "dev_password")
        )
    elif env == "cloud":
        return DatabaseConfig(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME"),
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            ssl_mode="require"
        )
```

**Storage Considerations:**
- **Papers**: Full text can be large (1-50MB per paper), consider separate file storage
- **PDFs**: Store in local filesystem initially, migrate to S3/cloud storage later
- **Embeddings**: Vector data requires pgvector, significant storage for large collections
- **Backups**: Local: pg_dump, Cloud: automated backups included

- [x] 3. Build manual paper ingestion system
  - Create CLI interface for manual paper input (URL, PDF, title, DOI)
  - Implement ArXiv URL parser and metadata fetcher
  - Build PDF upload handler with text extraction
  - Add paper title search functionality across ArXiv and Semantic Scholar
  - Implement duplicate detection logic
  - **Success Measure**: Successfully ingest 10 papers from your Notion database using all 4 input methods
  - _Requirements: 1.1, 1.2, 1.3_

**Phase 1 Demo Scenario:**
```bash
# Should work flawlessly by end of Phase 1
./ingest_paper --arxiv-url "https://arxiv.org/abs/2301.12345"
./ingest_paper --pdf-file "path/to/paper.pdf" --title "Optional Title Override"
./ingest_paper --title "Attention Is All You Need"
./ingest_paper --doi "10.1000/182"

# Verify ingestion
./list_papers --count
# Output: "4 papers successfully ingested, 0 duplicates detected"
```

## Phase 2: Analysis Engine and Classification

- [x] 4. Implement paper classification system
  - Create paper type classifier (Framework, Survey, Case Study, etc.)
  - Build evidence strength assessment logic
  - Implement practical applicability scoring
  - Add confidence calculation for classifications
  - _Requirements: 2.2, 2.8_

- [x] 5. Build configurable analysis rubric system
  - Create rubric configuration loader (YAML/JSON based)
  - Implement type-specific extraction templates
  - Build LLM integration for insight extraction
  - Add structured output validation and parsing
  - _Requirements: 2.1, 2.2, 2.9_

- [x] 6. Implement insight extraction and storage
  - Create insight extraction pipeline using configured rubrics
  - Build confidence scoring system for extracted insights
  - Implement structured insight storage with JSON content
  - Add automatic tagging based on extracted content
  - _Requirements: 2.3, 2.4, 2.5, 2.7_

## Phase 3: Review Interface and Validation

- [ ] 7. Create analysis review dashboard
  - Build web interface for reviewing automated analysis results
  - Implement side-by-side comparison of automated vs manual analysis
  - Add correction and feedback forms for classification and insights
  - Create batch approval/rejection functionality
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 8. Implement feedback loop and rubric tuning
  - Create feedback storage system for tracking corrections
  - Build rubric performance metrics and analytics
  - Implement A/B testing framework for rubric improvements
  - Add confidence threshold adjustment based on validation results
  - _Requirements: 2.10, 5.4_

- [ ] 9. Build search and browsing interface
  - Implement full-text search across papers and insights
  - Create filtering by categories, tags, and metadata
  - Build hierarchical tag browsing interface
  - Add paper relationship visualization (citations, similar papers)
  - _Requirements: 8.2, 8.3, 8.4_

## Phase 4: Citation Analysis and Knowledge Graph

- [ ] 10. Implement citation extraction and analysis
  - Build citation parser for extracting references from papers
  - Create external citation prioritization system
  - Implement citation relationship mapping and storage
  - Add citation-based paper recommendation system
  - _Requirements: 1.5, 1.6, 1.7, 4.1, 4.3_

- [ ] 11. Build semantic similarity and cross-referencing
  - Implement vector embedding generation for papers and insights
  - Create semantic similarity search functionality
  - Build cross-reference suggestion system
  - Add relationship type classification (builds-upon, contradicts, etc.)
  - _Requirements: 4.2, 4.4, 4.5_

## Phase 5: System Integration and Testing

- [ ] 12. Create comprehensive testing suite
  - Write unit tests for all core models and services
  - Implement integration tests for the full ingestion pipeline
  - Create test data fixtures with known papers for validation
  - Add performance tests for database queries and analysis speed
  - _Requirements: All requirements validation_

- [ ] 13. Build monitoring and analytics dashboard
  - Implement system performance monitoring
  - Create analytics for ingestion rates, analysis accuracy, and user feedback
  - Build rubric performance tracking and comparison tools
  - Add alerting for system failures or quality degradation
  - _Requirements: 2.10, 8.5_

- [ ] 14. Create deployment and configuration management
  - Set up containerized deployment with Docker
  - Create configuration management for different environments
  - Implement database backup and recovery procedures
  - Add logging and error tracking systems
  - _Requirements: System reliability and maintenance_