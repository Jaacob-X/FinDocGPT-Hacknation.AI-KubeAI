from rest_framework import serializers
from .models import IterativeAnalysis

class IterativeAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for IterativeAnalysis model"""
    
    final_recommendation = serializers.SerializerMethodField(read_only=True)
    confidence_level = serializers.CharField(source='get_confidence_level', read_only=True)
    
    def get_final_recommendation(self, obj):
        """Get final recommendation, handling both string and object formats"""
        recommendation = obj.get_final_recommendation()
        # Always return as-is to let frontend handle the format
        return recommendation
    
    class Meta:
        model = IterativeAnalysis
        fields = [
            'id', 'query', 'company_filter', 'final_analysis', 'iteration_history',
            'total_iterations', 'documents_analyzed', 'rag_queries_executed',
            'final_completeness_score', 'created_at', 'completed_at', 'status',
            'error_message', 'final_recommendation', 'confidence_level', 'cancel_requested'
        ]
        read_only_fields = [
            'id', 'final_analysis', 'iteration_history', 'total_iterations',
            'documents_analyzed', 'rag_queries_executed', 'final_completeness_score',
            'created_at', 'completed_at', 'status', 'error_message'
        ]

class AnalysisCreateSerializer(serializers.Serializer):
    """Serializer for creating new analysis"""
    
    query = serializers.CharField(
        max_length=1000,
        help_text="Investment query or question to analyze"
    )
    company_filter = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional company name to filter analysis"
    )
    
    def validate_query(self, value):
        """Validate the query"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Query must be at least 10 characters long")
        return value.strip()

class AnalysisSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for analysis list view"""
    
    final_recommendation = serializers.SerializerMethodField(read_only=True)
    confidence_level = serializers.CharField(source='get_confidence_level', read_only=True)
    
    def get_final_recommendation(self, obj):
        """Get final recommendation, handling both string and object formats"""
        recommendation = obj.get_final_recommendation()
        # Always return as-is to let frontend handle the format
        return recommendation
    
    class Meta:
        model = IterativeAnalysis
        fields = [
            'id', 'query', 'company_filter', 'total_iterations',
            'documents_analyzed', 'final_completeness_score',
            'created_at', 'status', 'final_recommendation', 'confidence_level'
        ]
