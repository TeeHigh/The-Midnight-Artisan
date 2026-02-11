from django.core.management.base import BaseCommand
from core.models import Order
from core.tasks import send_invoice_email_task


class Command(BaseCommand):
    help = 'Queue invoice tasks for orders where invoice was not sent'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of orders to process'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        
        orders = Order.objects.filter(is_invoice_sent=False).order_by('created_at')[:limit]
        
        total = orders.count()
        self.stdout.write(f"Found {total} orders without invoices sent")
        
        queued_count = 0
        
        for order in orders:
            try:
                task = send_invoice_email_task.delay(str(order.id))
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Order {order.id} queued (task: {task.id})")
                )
                queued_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Order {order.id} failed: {str(e)}")
                )
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Queued: {queued_count}/{total}"))