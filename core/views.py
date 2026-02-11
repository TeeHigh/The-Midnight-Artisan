from rest_framework import generics, status
from .tasks import send_invoice_email_task
from .models import Order, Inventory
from .serializers import OrderSerializer, InventorySerializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from celery.exceptions import OperationalError
import logging


class CreateProductView(generics.ListCreateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        return Response(
            {
                'message': 'Product created successfully',
                'data': serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class CreateOrListOrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]

    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        print("=" * 50)
        print("1. CREATE VIEW CALLED")
        print("=" * 50)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        print(f"2. ORDER CREATED: {order.id}")
        print(f"   Customer: {order.customer_name}")
        print(f"   Email: {order.customer_email}")
        
        logger = logging.getLogger(__name__)

        try:
            # task = send_invoice_email_task.delay(str(order.id))

            print("3. ATTEMPTING TO QUEUE TASK...")
            task = send_invoice_email_task.delay(str(order.id))
            print(f"4. TASK QUEUED SUCCESSFULLY: {task.id}")
            
            return Response(
                {
                    'message': 'Order created successfully. Invoice will be sent shortly.',
                    'data': serializer.data,
                    'task_id': task.id
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        except OperationalError as e:
            logger.error(f"Failed to queue invoice task for order {order.id}: {str(e)}")
            
            return Response(
                {
                    'message': 'Order created successfully, but invoice queuing failed. Please retry later.',
                    'data': serializer.data,
                    'warning': 'Task queue unavailable'
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )

    def perform_create(self, serializer):
        return serializer.save()  


class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'