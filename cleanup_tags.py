#!/usr/bin/env python3
"""
Script to clean up existing tags according to the new tag guidelines.
This will merge similar tags, remove paper-specific tags, and standardize naming.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.tag_repository import TagRepository, PaperTagRepository
from src.database.paper_repository import PaperRepository
from src.models.tag import Tag, TagCategory
from src.models.enums import TagSource

class TagCleanupService:
    """Service to clean up and standardize tags according to guidelines."""
    
    def __init__(self):
        self.tag_repo = TagRepository()
        self.paper_tag_repo = PaperTagRepository()
        self.paper_repo = PaperRepository()
        
        # Tag mapping rules for cleanup
        self.tag_mappings = {
            # Paper-specific to generalized
            "attention-is-all-you-need": "transformer-architecture",
            "theagentcompany": "benchmarking",
            "agentic-multimodal-ai-for-hyperpersonalized-b2b-and-b2c-advertising": "multimodal-ai",
            
            # Step-specific to general methodology
            "step-1:-tokenization": "tokenization",
            "step-2:-embedding": "embedding",
            "step-1:-data-integration": "data-integration",
            "step-2:-persona-targeting": "persona-targeting",
            
            # Overly specific to standard terms
            "task-completion-rate": "performance-metrics",
            "large-language-model-(llm)": "language-models",
            "retrieval-augmented-generation-(rag)": "retrieval-augmented-generation",
            
            # Inconsistent naming
            "ai-agents": "agents",
            "adaptive-persona-based-targeting": "persona-targeting",
            "multimodal-reasoning": "multimodal-processing",
            "collaboration-mechanisms": "collaborative-systems",
            "evolutionary-pathways": "evolutionary-algorithms",
            "agent-design-principles": "agent-architecture"
        }
        
        # Category corrections
        self.category_corrections = {
            "task-completion-rate": TagCategory.CONCEPT,  # Should be methodology
            "theagentcompany": TagCategory.APPLICATION,  # Should be concept
            "agentic-multimodal-ai-for-hyperpersonalized-b2b-and-b2c-advertising": TagCategory.CONCEPT,  # Should be concept
        }
        
        # Tags to remove (paper-specific or too granular)
        self.tags_to_remove = [
            "attention-is-all-you-need",
            "theagentcompany", 
            "agentic-multimodal-ai-for-hyperpersonalized-b2b-and-b2c-advertising",
            "step-1:-tokenization",
            "step-2:-embedding", 
            "step-1:-data-integration",
            "step-2:-persona-targeting"
        ]

    async def analyze_current_tags(self) -> Dict[str, any]:
        """Analyze current tags and identify issues."""
        print("🔍 Analyzing current tags...")
        
        # Get all tags with usage statistics
        tag_stats = await self.paper_tag_repo.get_tag_usage_stats()
        
        issues = {
            "paper_specific": [],
            "overly_granular": [],
            "inconsistent_naming": [],
            "wrong_category": [],
            "low_usage": [],
            "total_tags": len(tag_stats),
            "tags_by_category": {}
        }
        
        for tag_info in tag_stats:
            tag_name = tag_info['name']
            usage_count = tag_info['usage_count']
            category = tag_info['category']
            
            # Count by category
            if category not in issues["tags_by_category"]:
                issues["tags_by_category"][category] = 0
            issues["tags_by_category"][category] += 1
            
            # Check for issues
            if tag_name in self.tags_to_remove:
                if "step-" in tag_name:
                    issues["overly_granular"].append(tag_name)
                else:
                    issues["paper_specific"].append(tag_name)
            
            if tag_name in self.tag_mappings:
                issues["inconsistent_naming"].append(tag_name)
            
            if tag_name in self.category_corrections:
                issues["wrong_category"].append(tag_name)
            
            if usage_count == 1:
                issues["low_usage"].append(tag_name)
        
        return issues

    async def cleanup_tags(self, dry_run: bool = True) -> Dict[str, any]:
        """Clean up tags according to guidelines."""
        print(f"🧹 Cleaning up tags (dry_run: {dry_run})...")
        
        # Analyze current state
        issues = await self.analyze_current_tags()
        
        print(f"\n📊 Current Tag Analysis:")
        print(f"   Total tags: {issues['total_tags']}")
        print(f"   Tags by category: {issues['tags_by_category']}")
        print(f"   Paper-specific tags: {len(issues['paper_specific'])}")
        print(f"   Overly granular tags: {len(issues['overly_granular'])}")
        print(f"   Inconsistent naming: {len(issues['inconsistent_naming'])}")
        print(f"   Wrong category: {len(issues['wrong_category'])}")
        print(f"   Low usage (1 paper): {len(issues['low_usage'])}")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No changes will be made")
            return issues
        
        # Perform cleanup operations
        changes = {
            "tags_merged": [],
            "tags_removed": [],
            "categories_fixed": [],
            "errors": []
        }
        
        try:
            # 1. Merge tags according to mappings
            for old_name, new_name in self.tag_mappings.items():
                old_tag = await self.tag_repo.get_by_name(old_name)
                if old_tag:
                    new_tag = await self.tag_repo.get_by_name(new_name)
                    
                    if not new_tag:
                        # Create new tag
                        new_tag = Tag(
                            name=new_name,
                            category=old_tag.category,
                            description=f"Merged from {old_name}"
                        )
                        new_tag = await self.tag_repo.create(new_tag)
                    
                    # Move paper associations
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
                    changes["tags_merged"].append(f"{old_name} → {new_name}")
            
            # 2. Fix categories
            for tag_name, correct_category in self.category_corrections.items():
                tag = await self.tag_repo.get_by_name(tag_name)
                if tag and tag.category != correct_category:
                    tag.category = correct_category
                    await self.tag_repo.update(tag)
                    changes["categories_fixed"].append(f"{tag_name}: {tag.category.value} → {correct_category.value}")
            
            # 3. Remove paper-specific tags
            for tag_name in self.tags_to_remove:
                tag = await self.tag_repo.get_by_name(tag_name)
                if tag:
                    # Remove all associations
                    paper_tags = await self.paper_tag_repo.get_by_tag(tag.id)
                    for paper_tag in paper_tags:
                        await self.paper_tag_repo.remove_tag_from_paper(
                            paper_tag.paper_id, 
                            tag.id
                        )
                    
                    # Delete tag
                    await self.tag_repo.delete(tag.id)
                    changes["tags_removed"].append(tag_name)
        
        except Exception as e:
            changes["errors"].append(str(e))
            print(f"❌ Error during cleanup: {e}")
        
        return changes

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
    parser = argparse.ArgumentParser(description="Tag Cleanup Tool")
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
            await service.cleanup_tags(dry_run=True)
        
        elif args.cleanup:
            print("⚠️  WARNING: This will modify your database!")
            response = input("Are you sure you want to proceed? (y/N): ")
            if response.lower() == 'y':
                changes = await service.cleanup_tags(dry_run=False)
                print(f"\n✅ Cleanup completed:")
                print(f"   Tags merged: {len(changes['tags_merged'])}")
                print(f"   Tags removed: {len(changes['tags_removed'])}")
                print(f"   Categories fixed: {len(changes['categories_fixed'])}")
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