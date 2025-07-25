"""
Service for applying classifications to papers and managing the classification process.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from .paper_classifier import PaperClassifier
from ..database.paper_repository import PaperRepository
from ..models.paper import Paper
from ..models.enums import AnalysisStatus

logger = logging.getLogger(__name__)


class ClassificationService:
    """Service for managing paper classification workflow."""
    
    def __init__(self):
        self.classifier = PaperClassifier()
        self.paper_repo = PaperRepository()
        self.confidence_thresholds = {
            'auto_approve': 0.8,
            'manual_review': 0.5,
            'auto_reject': 0.2
        }
    
    async def classify_paper(self, paper_id: UUID) -> Optional[Dict[str, Any]]:
        """Classify a single paper and update it in the database."""
        try:
            # Get paper from database
            paper = await self.paper_repo.get_by_id(paper_id)
            if not paper:
                logger.error(f"Paper not found: {paper_id}")
                return None
            
            # Skip if already classified with high confidence
            if (paper.analysis_status == AnalysisStatus.COMPLETED and 
                paper.analysis_confidence and paper.analysis_confidence > 0.8):
                logger.info(f"Paper already classified with high confidence: {paper.title}")
                return self._paper_to_classification_result(paper)
            
            # Update status to in_progress
            await self.paper_repo.update_analysis_status(paper_id, AnalysisStatus.IN_PROGRESS)
            
            # Perform classification
            classification = self.classifier.classify_paper(paper)
            
            # Update paper with classification results
            paper.paper_type = classification['paper_type']
            paper.evidence_strength = classification['evidence_strength']
            paper.practical_applicability = classification['practical_applicability']
            paper.analysis_confidence = classification['overall_confidence']
            
            # Determine final status based on confidence
            if classification['overall_confidence'] >= self.confidence_thresholds['auto_approve']:
                paper.analysis_status = AnalysisStatus.COMPLETED
            elif classification['overall_confidence'] >= self.confidence_thresholds['manual_review']:
                paper.analysis_status = AnalysisStatus.MANUAL_REVIEW
            else:
                paper.analysis_status = AnalysisStatus.FAILED
            
            # Save updated paper
            updated_paper = await self.paper_repo.update(paper)
            
            # Prepare result
            result = {
                'paper_id': paper_id,
                'paper_title': paper.title,
                'classification': classification,
                'status': paper.analysis_status,
                'updated_paper': updated_paper
            }
            
            logger.info(f"Successfully classified paper: {paper.title} -> {classification['paper_type']} "
                       f"(confidence: {classification['overall_confidence']:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to classify paper {paper_id}: {e}")
            # Update status to failed
            try:
                await self.paper_repo.update_analysis_status(paper_id, AnalysisStatus.FAILED)
            except:
                pass
            return None
    
    async def classify_pending_papers(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Classify all papers with pending analysis status."""
        try:
            # Get pending papers
            pending_papers = await self.paper_repo.get_by_status(AnalysisStatus.PENDING, limit=limit)
            
            if not pending_papers:
                logger.info("No pending papers found for classification")
                return []
            
            logger.info(f"Starting classification of {len(pending_papers)} pending papers")
            
            results = []
            for paper in pending_papers:
                result = await self.classify_paper(paper.id)
                if result:
                    results.append(result)
            
            # Summary
            successful = len([r for r in results if r])
            failed = len(pending_papers) - successful
            
            logger.info(f"Classification complete: {successful} successful, {failed} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to classify pending papers: {e}")
            return []
    
    async def reclassify_paper(self, paper_id: UUID, force: bool = False) -> Optional[Dict[str, Any]]:
        """Reclassify a paper, optionally forcing reclassification of completed papers."""
        try:
            paper = await self.paper_repo.get_by_id(paper_id)
            if not paper:
                logger.error(f"Paper not found: {paper_id}")
                return None
            
            if not force and paper.analysis_status == AnalysisStatus.COMPLETED:
                logger.info(f"Paper already classified, use force=True to reclassify: {paper.title}")
                return self._paper_to_classification_result(paper)
            
            # Reset status and reclassify
            await self.paper_repo.update_analysis_status(paper_id, AnalysisStatus.PENDING)
            return await self.classify_paper(paper_id)
            
        except Exception as e:
            logger.error(f"Failed to reclassify paper {paper_id}: {e}")
            return None
    
    async def get_classification_stats(self) -> Dict[str, Any]:
        """Get statistics about paper classifications."""
        try:
            stats = await self.paper_repo.get_statistics()
            
            # Get papers by status
            all_papers = await self.paper_repo.list_all()
            
            # Count by paper type
            type_counts = {}
            for paper in all_papers:
                if paper.paper_type:
                    type_name = paper.paper_type.value
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            # Count by evidence strength
            evidence_counts = {}
            for paper in all_papers:
                if paper.evidence_strength:
                    evidence_name = paper.evidence_strength.value
                    evidence_counts[evidence_name] = evidence_counts.get(evidence_name, 0) + 1
            
            # Count by practical applicability
            applicability_counts = {}
            for paper in all_papers:
                if paper.practical_applicability:
                    app_name = paper.practical_applicability.value
                    applicability_counts[app_name] = applicability_counts.get(app_name, 0) + 1
            
            # Confidence distribution
            confidence_ranges = {'high': 0, 'medium': 0, 'low': 0, 'none': 0}
            for paper in all_papers:
                if paper.analysis_confidence is None:
                    confidence_ranges['none'] += 1
                elif paper.analysis_confidence >= 0.8:
                    confidence_ranges['high'] += 1
                elif paper.analysis_confidence >= 0.5:
                    confidence_ranges['medium'] += 1
                else:
                    confidence_ranges['low'] += 1
            
            classification_stats = {
                **stats,
                'paper_types': type_counts,
                'evidence_strength': evidence_counts,
                'practical_applicability': applicability_counts,
                'confidence_distribution': confidence_ranges,
                'classification_thresholds': self.confidence_thresholds
            }
            
            return classification_stats
            
        except Exception as e:
            logger.error(f"Failed to get classification stats: {e}")
            return {}
    
    async def get_papers_needing_review(self) -> List[Paper]:
        """Get papers that need manual review."""
        try:
            return await self.paper_repo.get_by_status(AnalysisStatus.MANUAL_REVIEW)
        except Exception as e:
            logger.error(f"Failed to get papers needing review: {e}")
            return []
    
    async def approve_classification(self, paper_id: UUID) -> bool:
        """Approve a paper's classification (move from manual review to completed)."""
        try:
            paper = await self.paper_repo.get_by_id(paper_id)
            if not paper:
                logger.error(f"Paper not found: {paper_id}")
                return False
            
            if paper.analysis_status != AnalysisStatus.MANUAL_REVIEW:
                logger.warning(f"Paper is not in manual review status: {paper.title}")
                return False
            
            await self.paper_repo.update_analysis_status(paper_id, AnalysisStatus.COMPLETED)
            logger.info(f"Approved classification for paper: {paper.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve classification for paper {paper_id}: {e}")
            return False
    
    async def reject_classification(self, paper_id: UUID) -> bool:
        """Reject a paper's classification (move back to pending for reclassification)."""
        try:
            paper = await self.paper_repo.get_by_id(paper_id)
            if not paper:
                logger.error(f"Paper not found: {paper_id}")
                return False
            
            await self.paper_repo.update_analysis_status(paper_id, AnalysisStatus.PENDING)
            logger.info(f"Rejected classification for paper: {paper.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject classification for paper {paper_id}: {e}")
            return False
    
    def _paper_to_classification_result(self, paper: Paper) -> Dict[str, Any]:
        """Convert paper to classification result format."""
        return {
            'paper_id': paper.id,
            'paper_title': paper.title,
            'classification': {
                'paper_type': paper.paper_type,
                'evidence_strength': paper.evidence_strength,
                'practical_applicability': paper.practical_applicability,
                'overall_confidence': paper.analysis_confidence,
                'classification_details': {
                    'has_abstract': bool(paper.abstract),
                    'arxiv_categories': paper.categories or []
                }
            },
            'status': paper.analysis_status,
            'updated_paper': paper
        }