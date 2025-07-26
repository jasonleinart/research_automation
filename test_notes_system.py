#!/usr/bin/env python3
"""
Test script for the notes system.
This script tests the note models, repository, and database operations.
"""

import sys
import asyncio
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.note import Note, NoteTag, NoteRelationship, NoteCollection, NoteTemplate
from src.models.enums import NoteType, NotePriority
from src.database.note_repository import NoteRepository
from src.database.paper_repository import PaperRepository
from src.database.connection import db_manager

def test_note_models():
    print("🧪 Testing Note Models...")
    
    # Test Note model
    note = Note(
        title="Test Note",
        content="This is a test note content",
        paper_id=uuid4(),
        note_type=NoteType.GENERAL,
        priority=NotePriority.MEDIUM,
        tags=["test", "example"],
        page_number=1,
        x_position=Decimal("0.25"),
        y_position=Decimal("0.5"),
        selected_text="test content",
        annotation_color="#FF0000"
    )
    print(f"✅ Created note: {note.title}")
    print(f"   Type: {note.note_type}")
    print(f"   Priority: {note.priority}")
    print(f"   Tags: {note.tags}")
    print(f"   Is annotation: {note.is_annotation}")
    print(f"   Has PDF coordinates: {note.has_pdf_coordinates}")
    
    # Test NoteTag model
    tag = NoteTag(
        name="research",
        color="#00FF00",
        description="Research-related notes",
        usage_count=5
    )
    print(f"✅ Created tag: {tag.name} ({tag.color})")
    
    # Test NoteRelationship model
    relationship = NoteRelationship(
        source_note_id=uuid4(),
        target_note_id=uuid4(),
        relationship_type="references",
        strength=0.8
    )
    print(f"✅ Created relationship: {relationship.relationship_type} (strength: {relationship.strength})")
    
    # Test NoteCollection model
    collection = NoteCollection(
        name="Research Insights",
        description="Collection of research insights",
        color="#0000FF",
        is_public=True
    )
    print(f"✅ Created collection: {collection.name}")
    
    # Test NoteTemplate model
    template = NoteTemplate(
        name="Question Template",
        template_content="Question: {question}\nAnswer: {answer}",
        note_type=NoteType.QUESTION
    )
    print(f"✅ Created template: {template.name}")
    
    print("✅ All note models tested successfully!\n")

async def test_note_repository():
    print("🧪 Testing Note Repository...")
    
    # Initialize database connection
    await db_manager.initialize()
    
    repo = NoteRepository()
    paper_repo = PaperRepository()
    
    # Get a paper to work with
    papers = await paper_repo.list_all(limit=1)
    if not papers:
        print("❌ No papers found in database. Please ingest a paper first.")
        return False
    
    paper = papers[0]
    print(f"Using paper: {paper.title}")
    
    # Test creating a note
    note = Note(
        title="Test Repository Note",
        content="This is a test note created via repository",
        paper_id=paper.id,
        note_type=NoteType.GENERAL,
        priority=NotePriority.HIGH,
        tags=["test", "repository"]
    )
    
    created_note = await repo.create_note(note)
    print(f"✅ Created note: {created_note.title} (ID: {created_note.id})")
    
    # Test retrieving the note
    retrieved_note = await repo.get_note(created_note.id)
    if retrieved_note and retrieved_note.id == created_note.id:
        print("✅ Successfully retrieved note")
    else:
        print("❌ Failed to retrieve note")
        return False
    
    # Test updating the note
    retrieved_note.title = "Updated Test Note"
    retrieved_note.content = "This note has been updated"
    updated_note = await repo.update_note(retrieved_note)
    if updated_note.title == "Updated Test Note":
        print("✅ Successfully updated note")
    else:
        print("❌ Failed to update note")
        return False
    
    # Test getting notes by paper
    paper_notes = await repo.get_notes_by_paper(paper.id)
    if len(paper_notes) > 0:
        print(f"✅ Found {len(paper_notes)} notes for paper")
    else:
        print("❌ No notes found for paper")
        return False
    
    # Test search functionality
    search_results = await repo.search_notes("test", paper_id=paper.id)
    if len(search_results) > 0:
        print(f"✅ Search found {len(search_results)} notes")
    else:
        print("❌ Search returned no results")
        # Let's check if the search vector was created
        note_with_vector = await repo.get_note(created_note.id)
        if note_with_vector and note_with_vector.search_vector:
            print(f"✅ Search vector exists: {note_with_vector.search_vector[:100]}...")
            # Try a direct database query to debug
            async with db_manager.get_connection() as conn:
                direct_results = await conn.fetch("""
                    SELECT title, ts_rank(search_vector, plainto_tsquery('english', 'test')) as rank 
                    FROM notes 
                    WHERE search_vector @@ plainto_tsquery('english', 'test') AND paper_id = $1
                """, paper.id)
                print(f"Direct query found {len(direct_results)} results")
                for result in direct_results:
                    print(f"  - {result['title']} (rank: {result['rank']})")
        else:
            print("❌ Search vector not created")
        return False
    
    # Test tag operations
    tag = NoteTag(name="important", color="#FF0000", description="Important notes")
    created_tag = await repo.create_tag(tag)
    print(f"✅ Created tag: {created_tag.name}")
    
    all_tags = await repo.get_all_tags()
    print(f"✅ Found {len(all_tags)} total tags")
    
    # Test collection operations
    collection = NoteCollection(
        name="Test Collection",
        description="A test collection",
        color="#00FF00",
        is_public=False
    )
    created_collection = await repo.create_collection(collection)
    print(f"✅ Created collection: {created_collection.name}")
    
    # Test adding note to collection
    success = await repo.add_note_to_collection(created_note.id, created_collection.id)
    if success:
        print("✅ Successfully added note to collection")
    else:
        print("❌ Failed to add note to collection")
        return False
    
    # Test getting notes in collection
    collection_notes = await repo.get_notes_in_collection(created_collection.id)
    if len(collection_notes) > 0:
        print(f"✅ Found {len(collection_notes)} notes in collection")
    else:
        print("❌ No notes found in collection")
        return False
    
    # Test template operations
    templates = await repo.get_templates()
    print(f"✅ Found {len(templates)} templates")
    
    default_template = await repo.get_default_template(NoteType.QUESTION)
    if default_template:
        print(f"✅ Found default template: {default_template.name}")
    else:
        print("❌ No default template found")
        return False
    
    # Test statistics
    stats = await repo.get_note_statistics(paper.id)
    print(f"✅ Retrieved note statistics: {stats}")
    
    # Clean up - delete the test note
    deleted = await repo.delete_note(created_note.id)
    if deleted:
        print("✅ Successfully deleted test note")
    else:
        print("❌ Failed to delete test note")
        return False
    
    print("✅ All repository operations tested successfully!\n")
    return True

async def test_note_relationships():
    print("🧪 Testing Note Relationships...")
    
    await db_manager.initialize()
    repo = NoteRepository()
    paper_repo = PaperRepository()
    
    # Get a paper
    papers = await paper_repo.list_all(limit=1)
    if not papers:
        print("❌ No papers found for relationship testing")
        return False
    
    paper = papers[0]
    
    # Create two notes
    note1 = Note(
        title="Source Note",
        content="This is the source note for relationship testing",
        paper_id=paper.id,
        note_type=NoteType.GENERAL
    )
    note2 = Note(
        title="Target Note", 
        content="This is the target note for relationship testing",
        paper_id=paper.id,
        note_type=NoteType.GENERAL
    )
    
    created_note1 = await repo.create_note(note1)
    created_note2 = await repo.create_note(note2)
    
    # Create a relationship
    relationship = NoteRelationship(
        source_note_id=created_note1.id,
        target_note_id=created_note2.id,
        relationship_type="references",
        strength=0.9
    )
    
    created_relationship = await repo.create_relationship(relationship)
    print(f"✅ Created relationship: {created_relationship.relationship_type}")
    
    # Get relationships for note1
    relationships = await repo.get_note_relationships(created_note1.id)
    if len(relationships) > 0:
        print(f"✅ Found {len(relationships)} relationships for note")
    else:
        print("❌ No relationships found")
        return False
    
    # Clean up
    await repo.delete_note(created_note1.id)
    await repo.delete_note(created_note2.id)
    
    print("✅ Note relationships tested successfully!\n")
    return True

async def test_pdf_annotations():
    print("🧪 Testing PDF Annotations...")
    
    await db_manager.initialize()
    repo = NoteRepository()
    paper_repo = PaperRepository()
    
    # Get a paper
    papers = await paper_repo.list_all(limit=1)
    if not papers:
        print("❌ No papers found for PDF annotation testing")
        return False
    
    paper = papers[0]
    
    # Create a PDF annotation note
    annotation = Note(
        title="PDF Annotation",
        content="This is a highlight on page 1",
        paper_id=paper.id,
        note_type=NoteType.ANNOTATION,
        page_number=1,
        x_position=Decimal("0.3"),
        y_position=Decimal("0.6"),
        width=Decimal("0.4"),
        height=Decimal("0.1"),
        selected_text="highlighted text content",
        annotation_color="#FFFF00"
    )
    
    created_annotation = await repo.create_note(annotation)
    print(f"✅ Created PDF annotation: {created_annotation.title}")
    print(f"   Page: {created_annotation.page_number}")
    print(f"   Position: ({created_annotation.x_position}, {created_annotation.y_position})")
    print(f"   Selected text: {created_annotation.selected_text}")
    
    # Test getting notes by page
    page_notes = await repo.get_notes_by_page(paper.id, 1)
    if len(page_notes) > 0:
        print(f"✅ Found {len(page_notes)} notes on page 1")
    else:
        print("❌ No notes found on page 1")
        return False
    
    # Clean up
    await repo.delete_note(created_annotation.id)
    
    print("✅ PDF annotations tested successfully!\n")
    return True

async def main():
    print("🚀 Testing Notes System for Research Dashboard")
    print("=" * 60)
    
    try:
        test_note_models()
        
        if not await test_note_repository():
            print("❌ Repository tests failed")
            return
        
        if not await test_note_relationships():
            print("❌ Relationship tests failed")
            return
        
        if not await test_pdf_annotations():
            print("❌ PDF annotation tests failed")
            return
        
        print("🎉 All notes system tests completed successfully!")
        print("\nThe notes system is ready for integration with:")
        print("1. PDF viewer interface")
        print("2. Chat interface for note creation")
        print("3. Dashboard for note management")
        print("4. Search and filtering capabilities")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 