from rest_framework import serializers
from .models import Document, Query

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    
    class Meta:
        model = Document
        fields = [
            'id', 'accession_number', 'form_type', 'company_name', 
            'ticker', 'cik', 'filing_date', 'period_of_report',
            'description', 'url', 'status', 'content_size',
            'created_at', 'updated_at', 'stored_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'stored_at']

class QuerySerializer(serializers.ModelSerializer):
    """Serializer for Query model"""
    
    class Meta:
        model = Query
        fields = [
            'id', 'query_text', 'status', 'documents_found',
            'documents_processed', 'strategy_result', 'research_result',
            'risk_result', 'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'documents_found', 'documents_processed',
            'strategy_result', 'research_result', 'risk_result',
            'created_at', 'completed_at'
        ]

class QueryCreateSerializer(serializers.Serializer):
    """Serializer for creating new queries"""
    query_text = serializers.CharField(max_length=1000)
    fetch_documents = serializers.BooleanField(default=True)
    document_limit = serializers.IntegerField(default=10, min_value=1, max_value=50)

class DocumentSearchSerializer(serializers.Serializer):
    """Serializer for document search requests"""
    query = serializers.CharField(max_length=500)
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)
    form_types = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        allow_empty=True
    )
