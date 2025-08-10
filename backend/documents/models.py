from django.db import models
from django.utils import timezone

class Document(models.Model):
    """Model for storing document metadata"""
    
    DOCUMENT_TYPES = [
        ('10-K', '10-K Annual Report'),
        ('10-Q', '10-Q Quarterly Report'),
        ('8-K', '8-K Current Report'),
        ('DEF 14A', 'Proxy Statement'),
        ('OTHER', 'Other Document'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Processing'),
        ('PROCESSING', 'Processing'),
        ('STORED', 'Stored in RAG'),
        ('ERROR', 'Processing Error'),
    ]
    
    accession_number = models.CharField(max_length=50, unique=True)
    form_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    company_name = models.CharField(max_length=200)
    ticker = models.CharField(max_length=10, blank=True)
    cik = models.CharField(max_length=20)
    filing_date = models.DateField()
    period_of_report = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    content_size = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    stored_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-filing_date', '-created_at']
    
    def __str__(self):
        return f"{self.form_type} - {self.company_name} ({self.filing_date})"
    
    def mark_as_stored(self):
        """Mark document as successfully stored in RAG"""
        self.status = 'STORED'
        self.stored_at = timezone.now()
        self.save()
    
    def mark_as_error(self):
        """Mark document as having processing error"""
        self.status = 'ERROR'
        self.save()

class Query(models.Model):
    """Model for storing user queries and their results"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('ERROR', 'Error'),
    ]
    
    query_text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    documents_found = models.IntegerField(default=0)
    documents_processed = models.IntegerField(default=0)
    
    # Results
    strategy_result = models.JSONField(null=True, blank=True)
    research_result = models.JSONField(null=True, blank=True)
    risk_result = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Query: {self.query_text[:50]}... ({self.status})"