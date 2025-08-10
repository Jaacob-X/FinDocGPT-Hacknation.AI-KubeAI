from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, QueryViewSet, HealthCheckView, CogneeServiceView

router = DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'queries', QueryViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/cognee/', CogneeServiceView.as_view(), name='cognee-service'),
]
