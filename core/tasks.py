from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from smtplib import SMTPException, SMTPServerDisconnected, SMTPConnectError
import socket
import logging

from .services import InvoiceService

logger = logging.getLogger(__name__)


@shared_task(
    name='send_invoice_email',
    bind=True,
    autoretry_for=(SMTPException, SMTPServerDisconnected, SMTPConnectError, ConnectionError),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,  # Exponential backoff: 1s, 2s, 4s
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def send_invoice_email_task(self, order_id: str):
    """
    Celery task to generate and send invoice email with automatic retry
    
    Args:
        order_id: UUID of the order
        
    Returns:
        dict with success status and message
    """

    print("\n" + "=" * 60)
    print("CELERY TASK STARTED")
    print("=" * 60)
    try:
        logger.info(f"Processing invoice for order {order_id} (Attempt {self.request.retries + 1})")
        
        result = InvoiceService.process_invoice(order_id)
        
        if not result['success']:
            if 'SMTP' in result.get('message', '') or 'Connection' in result.get('message', ''):
                logger.warning(f"SMTP error for order {order_id}, will retry")
                raise SMTPException(result['message'])
        
        logger.info(f"Invoice sent successfully for order {order_id}")
        return result
        
    except (SMTPException, SMTPServerDisconnected, SMTPConnectError, ConnectionError) as e:
        logger.warning(f"SMTP/Connection error for order {order_id}: {str(e)}")
        try:
            # Retry the task
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for order {order_id}")
            return {
                'success': False,
                'message': f'Failed after 3 retries: {str(e)}',
                'order_id': order_id
            }
    
    except Exception as e:
        logger.error(f"Unexpected error processing order {order_id}: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'order_id': order_id
        }


@shared_task(name='send_bulk_invoices')
def send_bulk_invoices_task(order_ids: list):
    """
    Send invoices for multiple orders
    Each order is queued as a separate task for better failure isolation
    
    Args:
        order_ids: List of order UUIDs
        
    Returns:
        dict with queued task info
    """
    task_ids = []
    
    for order_id in order_ids:
        task = send_invoice_email_task.delay(order_id)
        task_ids.append({
            'order_id': order_id,
            'task_id': task.id
        })
    
    return {
        'total': len(order_ids),
        'queued_tasks': task_ids
    }