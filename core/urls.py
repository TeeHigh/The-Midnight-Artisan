from django.urls import path
from .views import CreateOrListOrderView, CreateProductView, OrderDetailView

urlpatterns = [
    path('orders/', CreateOrListOrderView.as_view(), name='create-order'),
    path('orders/<uuid:id>/', OrderDetailView.as_view(), name='order-detail'),
    path('inventory/', CreateProductView.as_view(), name='create-product'),
]