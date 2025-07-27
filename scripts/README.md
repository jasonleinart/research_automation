# Scripts Directory

This directory contains organized scripts for the ArXiv Content Automation project.

## Directory Structure

### `essential/`
Core scripts needed for daily operation:
- `analyze_paper.py` - Paper analysis pipeline
- `classify_papers.py` - Paper type classification with enhanced full text analysis
- `extract_insights.py` - Insight extraction service
- `ingest_paper.py` - Paper ingestion service
- `reclassify_all_papers.py` - Reclassify all papers with enhanced full text analysis
- `setup_database.py` - Database initialization

**Note:** The main dashboard launcher (`start_dashboard.py`) is located in the project root directory.

### `utility/`
Utility scripts for data management and analysis:
- `view_data.py` - View database contents
- `view_insights.py` - View extracted insights
- `view_papers.py` - View paper details
- `view_tags.py` - View tag information

### `migration/`
Database migration and data transformation scripts:
- `migrate_authors.py` - Author data migration to relational model

### `test/`
Testing and validation scripts:
- `test_classification.py` - Test paper classification
- `test_database.py` - Test database operations
- `test_ingestion.py` - Test paper ingestion
- `test_models.py` - Test data models

### `cleanup/`
Data cleanup and maintenance scripts:
- `cleanup_old_insights.py` - Remove old insight data
- `cleanup_old_tags.py` - Remove old tag data
- `cleanup_tags.py` - Clean up tag data
- `cleanup_test_data.py` - Remove test data

### `view/`
Data viewing and export scripts:
- `list_insights.py` - List all insights
- `show_insights.py` - Show insight details
- `show_tags.py` - Show tag information
- `view_insight_details.py` - View detailed insight information
- `view_insights_by_type.py` - View insights by type
- `view_paper_insights.py` - View insights for specific papers

## Usage Examples

### Essential Operations

```bash
# Start the dashboard
python start_dashboard.py

# Ingest a paper from ArXiv URL
python scripts/essential/ingest_paper.py arxiv_url "https://arxiv.org/abs/1234.5678"

# Classify all papers with enhanced full text analysis
python scripts/essential/classify_papers.py

# Reclassify all papers with enhanced full text analysis
python scripts/essential/reclassify_all_papers.py

# Analyze a specific paper
python scripts/essential/analyze_paper.py "paper title or arxiv id"
```

### Data Management

```bash
# View all papers
python scripts/utility/view_papers.py

# View insights
python scripts/utility/view_insights.py

# Clean up old data
python scripts/cleanup/cleanup_old_insights.py
```

## Enhanced Classification System

The classification system now uses **comprehensive full text analysis** to achieve the highest possible confidence scores:

- **Title Analysis**: 3x weight for title patterns
- **Abstract Analysis**: 2x weight for abstract patterns  
- **Full Text Analysis**: Comprehensive analysis of introduction, conclusion, and key sections
- **Enhanced Scoring**: Improved confidence calculation with detailed pattern matching
- **Auto-Approval**: Papers with ≥70% confidence are automatically completed
- **Manual Review**: Papers with 40-70% confidence require review
- **Failed**: Papers with <40% confidence are marked as failed

This ensures the most accurate paper type classification based on complete content analysis rather than just metadata. 