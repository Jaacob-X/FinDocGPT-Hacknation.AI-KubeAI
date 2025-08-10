from django.db import models
import json

class IterativeAnalysis(models.Model):
    """Model to store iterative analysis results"""
    
    query = models.TextField(help_text="Original investment query")
    company_filter = models.CharField(max_length=255, blank=True, null=True, help_text="Company filter applied")
    
    # Analysis results
    final_analysis = models.JSONField(help_text="Final analysis results", blank=True, null=True)
    iteration_history = models.JSONField(help_text="Complete iteration history", blank=True, null=True)
    cancel_requested = models.BooleanField(default=False, help_text="User requested cancellation")
    
    # Metadata
    total_iterations = models.IntegerField(default=0)
    documents_analyzed = models.IntegerField(default=0)
    rag_queries_executed = models.IntegerField(default=0)
    final_completeness_score = models.FloatField(default=0.0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Iterative Analysis'
        verbose_name_plural = 'Iterative Analyses'
    
    def __str__(self):
        return f"Analysis: {self.query[:50]}... ({self.status})"
    
    def get_final_recommendation(self):
        """Extract the final recommendation from analysis"""
        if self.final_analysis and isinstance(self.final_analysis, dict):
            recommendation = self.final_analysis.get('recommendation', 'No recommendation available')
            
            # Handle case where recommendation is an object with decision/rationale
            if isinstance(recommendation, dict):
                decision = recommendation.get('decision', '')
                rationale = recommendation.get('rationale', '')
                if decision and rationale:
                    return f"{decision} - {rationale}"
                elif decision:
                    return decision
                elif rationale:
                    return rationale
                else:
                    # Return the whole object structure for frontend to handle
                    return recommendation
            
            return recommendation
        return 'Analysis incomplete'
    
    def get_confidence_level(self):
        """Extract confidence level from analysis"""
        if self.final_analysis and isinstance(self.final_analysis, dict):
            return self.final_analysis.get('confidence_level', 'Unknown')
        return 'Unknown'
    
    def update_progress(self, **kwargs):
        """Update analysis progress incrementally during execution"""
        updated = False

        if 'total_iterations' in kwargs:
            self.total_iterations = kwargs['total_iterations']
            updated = True

        if 'documents_analyzed' in kwargs:
            self.documents_analyzed = kwargs['documents_analyzed']
            updated = True

        if 'rag_queries_executed' in kwargs:
            self.rag_queries_executed = kwargs['rag_queries_executed']
            updated = True

        if 'final_completeness_score' in kwargs:
            self.final_completeness_score = kwargs['final_completeness_score']
            updated = True

        if 'iteration_history' in kwargs:
            self.iteration_history = kwargs['iteration_history']
            updated = True

        if 'final_analysis' in kwargs:
            self.final_analysis = kwargs['final_analysis']
            updated = True

        if updated:
            self.save(update_fields=[
                'total_iterations', 'documents_analyzed', 'rag_queries_executed',
                'final_completeness_score', 'iteration_history', 'final_analysis'
            ])

    def mark_completed(self, results: dict):
        """Mark analysis as completed with results"""
        from django.utils import timezone

        self.status = 'COMPLETED'
        self.final_analysis = results.get('final_analysis', {})
        self.iteration_history = results.get('iteration_history', [])
        self.total_iterations = results.get('total_iterations', 0)
        self.documents_analyzed = results.get('documents_analyzed', 0)
        self.completed_at = timezone.now()

        analysis_quality = results.get('analysis_quality', {})
        self.rag_queries_executed = analysis_quality.get('rag_queries_executed', 0)
        self.final_completeness_score = analysis_quality.get('final_completeness_score', 0.0)

        self.save()
    
    def mark_failed(self, error_message: str, partial_results: dict = None):
        """Mark analysis as failed with optional partial results"""
        from django.utils import timezone

        self.status = 'FAILED'
        self.error_message = error_message

        # Preserve partial results if available
        if partial_results:
            self.final_analysis = partial_results.get('final_analysis', self.final_analysis)
            self.iteration_history = partial_results.get('iteration_history', self.iteration_history)
            self.total_iterations = partial_results.get('total_iterations', self.total_iterations)
            self.documents_analyzed = partial_results.get('documents_analyzed', self.documents_analyzed)
            analysis_quality = partial_results.get('analysis_quality', {})
            if analysis_quality:
                self.rag_queries_executed = analysis_quality.get('rag_queries_executed', self.rag_queries_executed)
                self.final_completeness_score = analysis_quality.get('final_completeness_score', self.final_completeness_score)

        self.completed_at = timezone.now()
        self.save()

    def mark_cancel_requested(self):
        """Mark that user requested cancellation"""
        self.cancel_requested = True
        self.save(update_fields=['cancel_requested'])

    def mark_cancelled(self, results: dict | None = None, message: str | None = None):
        """Mark analysis as cancelled"""
        from django.utils import timezone
        self.status = 'CANCELLED'
        if results:
            # Optionally preserve partial state
            self.final_analysis = results.get('final_analysis', self.final_analysis)
            self.iteration_history = results.get('iteration_history', self.iteration_history)
            self.total_iterations = results.get('total_iterations', self.total_iterations)
            self.documents_analyzed = results.get('documents_analyzed', self.documents_analyzed)
            analysis_quality = results.get('analysis_quality', {})
            if analysis_quality:
                self.rag_queries_executed = analysis_quality.get('rag_queries_executed', self.rag_queries_executed)
                self.final_completeness_score = analysis_quality.get('final_completeness_score', self.final_completeness_score)
        if message:
            self.error_message = message
        self.completed_at = timezone.now()
        self.save()

    def get_latest_iteration_analysis(self):
        """Extract the latest analysis from iteration history for terminated analyses"""
        if not self.iteration_history:
            return None

        # Find the most recent analysis iteration
        latest_analysis = None
        latest_timestamp = None

        for iteration in self.iteration_history:
            if iteration.get('type') == 'initial_analysis' or iteration.get('type') == 'refinement':
                timestamp = iteration.get('timestamp')
                if timestamp and (not latest_timestamp or timestamp > latest_timestamp):
                    latest_timestamp = timestamp
                    latest_analysis = iteration.get('analysis')

        return latest_analysis

    def has_partial_results(self):
        """Check if this terminated analysis has any partial results to display"""
        if self.status not in ['CANCELLED', 'FAILED']:
            return False

        return bool(
            self.final_analysis or
            self.get_latest_iteration_analysis() or
            (self.iteration_history and len(self.iteration_history) > 0)
        )
