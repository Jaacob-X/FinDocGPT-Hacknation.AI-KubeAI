from django.contrib import admin
from .models import IterativeAnalysis

@admin.register(IterativeAnalysis)
class IterativeAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'query_preview', 'company_filter', 'status', 'total_iterations', 'final_completeness_score', 'created_at']
    list_filter = ['status', 'created_at', 'company_filter']
    search_fields = ['query', 'company_filter']
    readonly_fields = ['created_at', 'completed_at', 'final_analysis', 'iteration_history']
    
    def query_preview(self, obj):
        return obj.query[:50] + "..." if len(obj.query) > 50 else obj.query
    query_preview.short_description = 'Query'
    
    fieldsets = (
        ('Query Information', {
            'fields': ('query', 'company_filter')
        }),
        ('Results', {
            'fields': ('status', 'final_analysis', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_iterations', 'documents_analyzed', 'rag_queries_executed', 'final_completeness_score')
        }),
        ('History', {
            'fields': ('iteration_history',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
