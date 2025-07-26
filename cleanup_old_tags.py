#!/usr/bin/env python3
"""
Script to clean up old, specific tags and replace them with properly generalized ones.
This will remove paper-specific tags and create new generalized tags using the intelligent tagging system.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.tag_repository import TagRepository, PaperTagRepository
from src.database.paper_repository import PaperRepository
from src.models.tag import Tag, TagCategory
from src.models.enums import TagSource
from src.services.insight_extraction_service import InsightExtractionService

class TagCleanupService:
    """Service to clean up old, specific tags and replace with generalized ones."""
    
    def __init__(self):
        self.tag_repo = TagRepository()
        self.paper_tag_repo = PaperTagRepository()
        self.paper_repo = PaperRepository()
        self.extraction_service = InsightExtractionService()
        
        # Tags that are too specific and need to be replaced
        self.specific_tags_to_replace = {
            # Paper-specific methodology tags
            "analyze-the-relationship-between-size-dataset-size": "scaling-analysis",
            "derive-simple-equations-that-relate-overfitting-to": "overfitting-analysis",
            
            # Step-specific tags
            "step-1-tokenization-process": "tokenization",
            "attention-computation": "attention-mechanism",
            "input-processing": "data-preprocessing",
            "encoder-module-with-self-attention": "attention-mechanism",
            "decoder-module-with-cross-attention": "attention-mechanism",
            "position-encoding-mechanism": "position-encoding",
            
            # Overly specific concept tags
            "bleu-score": "performance-metrics",
            "accuracy": "performance-metrics",
            "multi-head-attention": "attention-mechanism",
            "self-attention": "attention-mechanism",
            "transformer": "transformer-architecture",
        }

    async def analyze_specific_tags(self) -> Dict[str, any]:
        """Analyze which tags are too specific and need replacement."""
        print("🔍 Analyzing specific tags that need replacement...")
        
        # Get all tags
        all_tags = await self.tag_repo.list_all()
        
        specific_tags = []
        for tag in all_tags:
            if tag.name in self.specific_tags_to_replace:
                specific_tags.append({
                    'tag': tag,
                    'suggested_replacement': self.specific_tags_to_replace[tag.name],
                    'usage_count': 0
                })
        
        # Get usage statistics
        tag_stats = await self.paper_tag_repo.get_tag_usage_stats()
        for stat in tag_stats:
            for specific_tag_info in specific_tags:
                if stat['name'] == specific_tag_info['tag'].name:
                    specific_tag_info['usage_count'] = stat['usage_count']
        
        return {
            'specific_tags': specific_tags,
            'total_specific': len(specific_tags)
        }

    async def cleanup_specific_tags(self, dry_run: bool = True) -> Dict[str, any]:
        """Clean up specific tags and replace with generalized ones."""
        print(f"🧹 Cleaning up specific tags (dry_run: {dry_run})...")
        
        # Analyze current state
        analysis = await self.analyze_specific_tags()
        
        print(f"\n📊 Specific Tags Analysis:")
        print(f"   Total specific tags found: {analysis['total_specific']}")
        
        if not analysis['specific_tags']:
            print("✅ No specific tags found that need replacement")
            return {'replaced': [], 'errors': []}
        
        print(f"\n📋 Specific tags to replace:")
        for tag_info in analysis['specific_tags']:
            tag = tag_info['tag']
            replacement = tag_info['suggested_replacement']
            usage = tag_info['usage_count']
            print(f"   - {tag.name} ({usage} papers) → {replacement}")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No changes will be made")
            return {'replaced': [], 'errors': []}
        
        # Perform cleanup
        replaced_tags = []
        errors = []
        
        try:
            for tag_info in analysis['specific_tags']:
                old_tag = tag_info['tag']
                new_tag_name = tag_info['suggested_replacement']
                
                # Direct approach: Create new tag directly without intelligent tagging
                new_tag = await self._create_replacement_tag_directly(
                    new_tag_name,
                    old_tag.category,
                    f"Generalized from {old_tag.name}"
                )
                
                if new_tag:
                    # Move paper associations from old tag to new tag
                    paper_tags = await self.paper_tag_repo.get_by_tag(old_tag.id)
                    
                    for paper_tag in paper_tags:
                        # Check if association already exists
                        existing = await self.paper_tag_repo.get_by_paper(paper_tag.paper_id)
                        if not any(pt.tag_id == new_tag.id for pt in existing):
                            await self.paper_tag_repo.add_tag_to_paper(
                                paper_tag.paper_id, 
                                new_tag.id, 
                                paper_tag.confidence,
                                TagSource.AUTOMATIC
                            )
                    
                    # Remove old tag associations
                    for paper_tag in paper_tags:
                        await self.paper_tag_repo.remove_tag_from_paper(
                            paper_tag.paper_id, 
                            old_tag.id
                        )
                    
                    # Delete old tag
                    await self.tag_repo.delete(old_tag.id)
                    
                    replaced_tags.append(f"{old_tag.name} → {new_tag.name}")
                    print(f"   ✅ Replaced {old_tag.name} with {new_tag.name}")
                else:
                    errors.append(f"Failed to create replacement for {old_tag.name}")
                    print(f"   ❌ Failed to create replacement for {old_tag.name}")
        
        except Exception as e:
            errors.append(str(e))
            print(f"❌ Error during cleanup: {e}")
        
        return {'replaced': replaced_tags, 'errors': errors}

    async def _create_replacement_tag_directly(self, name: str, category: TagCategory, description: str) -> Optional[Tag]:
        """Create a replacement tag directly without using intelligent tagging system."""
        try:
            # Check if tag already exists
            existing_tag = await self.tag_repo.get_by_name(name)
            if existing_tag:
                return existing_tag
            
            # Create new tag directly
            new_tag = Tag(
                name=name,
                category=category,
                description=description
            )
            
            created_tag = await self.tag_repo.create(new_tag)
            return created_tag
            
        except Exception as e:
            print(f"   ⚠️  Error creating tag '{name}': {e}")
            return None

    async def show_improved_tag_stats(self):
        """Show tag statistics after cleanup."""
        print("\n📈 Improved Tag Statistics:")
        
        tag_stats = await self.paper_tag_repo.get_tag_usage_stats()
        
        print(f"   Total tags: {len(tag_stats)}")
        
        # Group by category
        by_category = {}
        for tag_info in tag_stats:
            category = tag_info['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(tag_info)
        
        for category, tags in by_category.items():
            print(f"   {category}: {len(tags)} tags")
            for tag in sorted(tags, key=lambda x: x['usage_count'], reverse=True)[:3]:
                print(f"     - {tag['name']}: {tag['usage_count']} papers")
        
        # Show reusable tags (2+ papers)
        reusable_tags = [t for t in tag_stats if t['usage_count'] >= 2]
        print(f"   Reusable tags (2+ papers): {len(reusable_tags)}/{len(tag_stats)} ({len(reusable_tags)/len(tag_stats)*100:.1f}%)")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Specific Tag Cleanup Tool")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--cleanup', action='store_true', help='Perform the actual cleanup')
    parser.add_argument('--stats', action='store_true', help='Show tag statistics')
    
    args = parser.parse_args()
    
    if not any([args.dry_run, args.cleanup, args.stats]):
        print("Please specify an action: --dry-run, --cleanup, or --stats")
        return
    
    try:
        await db_manager.initialize()
        
        service = TagCleanupService()
        
        if args.dry_run:
            await service.cleanup_specific_tags(dry_run=True)
        
        elif args.cleanup:
            print("⚠️  WARNING: This will replace specific tags with generalized ones!")
            response = input("Are you sure you want to proceed? (y/N): ")
            if response.lower() == 'y':
                changes = await service.cleanup_specific_tags(dry_run=False)
                print(f"\n✅ Cleanup completed:")
                print(f"   Tags replaced: {len(changes['replaced'])}")
                if changes['errors']:
                    print(f"   Errors: {len(changes['errors'])}")
                
                await service.show_improved_tag_stats()
            else:
                print("Cleanup cancelled.")
        
        elif args.stats:
            await service.show_improved_tag_stats()
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    import argparse
    asyncio.run(main()) 