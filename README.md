# ArXiv Content Automation System

A system for automatically ingesting ArXiv research papers, analyzing them for insights, and generating platform-specific content.

## Phase 1: Core Infrastructure and Manual Ingestion

This phase focuses on setting up the database foundation and manual paper ingestion capabilities.

## Setup Instructions

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git

### 1. Clone and Setup Environment

```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env if needed for your setup
```

### 2. Start Database

```bash
# Start PostgreSQL with pgvector extension
docker-compose up -d

# Wait for database to be ready (check with)
docker-compose logs postgres
```

### 3. Initialize Database Schema

```bash
# Run database setup and migrations
python setup_database.py

# Test database connection and schema
python test_database.py
```

### 4. Verify Setup

If everything is working correctly, you should see:

```
Database connection successful
Found X tables:
  - citations
  - external_citations
  - insight_embeddings
  - insight_tags
  - insights
  - paper_embeddings
  - paper_tags
  - papers
  - tags

Found X enum types:
  - analysis_status_enum
  - citation_type_enum
  - embedding_type_enum
  - evidence_strength_enum
  - ingestion_status_enum
  - insight_type_enum
  - paper_type_enum
  - practical_applicability_enum
  - tag_category_enum
  - tag_source_enum

Found 2 required extensions:
  - uuid-ossp
  - vector
```

## Project Structure

```
├── src/
│   ├── models/          # Data models
│   ├── services/        # Business logic
│   ├── database/        # Database connection and migrations
│   ├── cli/            # Command-line interface
│   └── config.py       # Configuration management
├── database/
│   ├── init/           # Database initialization scripts
│   └── schema/         # SQL schema files
├── docker-compose.yml  # Local database setup
└── requirements.txt    # Python dependencies
```

## Database Schema

The system uses PostgreSQL with pgvector extension for:

- **Papers**: Core paper metadata and analysis results
- **Tags**: Hierarchical tagging system for organization
- **Insights**: Extracted structured insights from papers
- **Citations**: Citation relationships between papers
- **Embeddings**: Vector representations for semantic search

## Next Steps

Once Phase 1 is complete, you can proceed to:

- **Phase 2**: Analysis Engine and Classification
- **Phase 3**: Review Interface and Validation
- **Phase 4**: Citation Analysis and Knowledge Graph

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps

# View database logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Schema Issues

```bash
# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d
python setup_database.py
```