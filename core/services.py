# your_app/services.py
from decimal import Decimal
from datetime import datetime
from django.core.mail import EmailMessage
from smtplib import SMTPServerDisconnected, SMTPConnectError, SMTPException
import logging
import socket

from .models import Order

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for generating and sending invoices"""
    
    @staticmethod
    def generate_invoice_text(order: Order) -> str:
        """Generate a simple text-based invoice"""
        print(f"   → Generating invoice text for order {order.id}")

        
        invoice_lines = []
        invoice_lines.append("=" * 60)
        invoice_lines.append("INVOICE")
        invoice_lines.append("=" * 60)
        invoice_lines.append("")
        invoice_lines.append(f"Order ID: {order.id}")
        invoice_lines.append(f"Date: {order.created_at.strftime('%B %d, %Y %I:%M %p')}")
        invoice_lines.append("")
        invoice_lines.append("-" * 60)
        invoice_lines.append("CUSTOMER INFORMATION")
        invoice_lines.append("-" * 60)
        invoice_lines.append(f"Name: {order.customer_name}")
        invoice_lines.append(f"Email: {order.customer_email}")
        invoice_lines.append("")
        invoice_lines.append("-" * 60)
        invoice_lines.append("ORDER ITEMS")
        invoice_lines.append("-" * 60)
        invoice_lines.append(f"{'Item':<30} {'Qty':<5} {'Price':<10} {'Subtotal':<10}")
        invoice_lines.append("-" * 60)
        
        for item in order.items.all():
            invoice_lines.append(
                f"{item.product.product_name:<30} "
                f"{item.quantity:<5} "
                f"${item.price_at_purchase:<9.2f} "
                f"${item.subtotal:<9.2f}"
            )
        
        invoice_lines.append("-" * 60)
        invoice_lines.append(f"{'TOTAL':<46} ${order.total_amount:>9.2f}")
        invoice_lines.append("=" * 60)
        invoice_lines.append("")
        invoice_lines.append("Thank you for your order!")
        invoice_lines.append("")
        
        invoice_text = "\n".join(invoice_lines)
        print(f"   → Invoice text generated ({len(invoice_text)} characters)")
        return invoice_text
    
    @staticmethod
    def send_invoice_email(order: Order, invoice_text: str) -> bool:
        """
        Send invoice via email
        Raises SMTP exceptions for Celery to handle retries
        """
        # print(f"   → Attempting to send email to {order.customer_email}")
        # print(f"   → Email backend: {__import__('django.conf').conf.settings.EMAIL_BACKEND}")

        try:
            subject = f"Invoice for Order #{str(order.id)[:8]}"
            
            email = EmailMessage(
                subject=subject,
                body=invoice_text,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
                to=[order.customer_email],
            )
            
            result = email.send(fail_silently=False)

            logger.info(f"Email sent successfully to {order.customer_email}")
            return True
            
        except (SMTPException, SMTPServerDisconnected, SMTPConnectError, ConnectionError) as e:
            logger.error(f"SMTP error sending email to {order.customer_email}: {str(e)}")
            raise  # Re-raise for Celery to catch and retry
            
        except Exception as e:
            logger.error(f"Unexpected error sending email to {order.customer_email}: {str(e)}")
            raise
    
    @staticmethod
    def process_invoice(order_id: str) -> dict:
        """Complete invoice processing workflow"""

        try:
            order = Order.objects.get(id=order_id)
            
            # Generate invoice
            invoice_text = InvoiceService.generate_invoice_text(order)

            InvoiceService.send_invoice_email(order, invoice_text)
            
            # Mark invoice as sent
            order.is_invoice_sent = True
            order.save()
            
            result = {
                'success': True,
                'message': f'Invoice sent to {order.customer_email}',
                'order_id': str(order.id)
            }
            return result
                
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found")

            error = f'Order {order_id} not found'

            return {
                'success': False,
                'message': f'Order {order_id} not found',
                'order_id': order_id
            }
        except (SMTPException, SMTPServerDisconnected, SMTPConnectError, ConnectionError) as e:
            # SMTP errors - let Celery retry
            logger.error(f"SMTP error for order {order_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing order {order_id}: {str(e)}")

            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'message': str(e),
                'order_id': order_id
            }