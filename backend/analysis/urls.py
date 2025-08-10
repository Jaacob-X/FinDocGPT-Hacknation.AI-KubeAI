from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IterativeAnalysisViewSet

router = DefaultRouter()
router.register(r'iterative', IterativeAnalysisViewSet, basename='iterative-analysis')

urlpatterns = [
    path('', include(router.urls)),
]
