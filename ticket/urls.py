from rest_framework.routers import SimpleRouter
from django.urls import path

from . import viewsets


router = SimpleRouter(trailing_slash=False)
router.register(r'events', viewsets.EventViewSet)
router.register(r'orders', viewsets.OrderViewSet)
router.register(r'orders/cancel', viewsets.OrderCancellation)
router.register(r'statistics', viewsets.CustomStatistics, basename='statistics')


urlpatterns = router.urls
