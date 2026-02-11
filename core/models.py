import uuid
from django.db import models

class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_name = models.CharField(max_length=100)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Inventories"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product_name} - ${self.product_price} - Stock: {self.stock_quantity}"


class Order(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  customer_name = models.CharField(max_length=100)
  customer_email = models.EmailField()
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  is_invoice_sent = models.BooleanField(default=False)
    
  class Meta:
      ordering = ['-created_at']
  
  def __str__(self):
      return f"Order {self.id} - {self.customer_name} - Invoice Sent: {self.is_invoice_sent}"
  
  @property
  def total_amount(self):
      """Calculate total order amount"""
      return sum(item.subtotal for item in self.items.all())



class OrderItem(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
  product = models.ForeignKey(Inventory, on_delete=models.PROTECT)
  quantity = models.PositiveIntegerField()
  price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
  
  class Meta:
      unique_together = ['order', 'product']  # Prevent duplicate products in same order
  
  def __str__(self):
      return f"{self.product.product_name} (x{self.quantity}) for Order {self.order.id}"
  
  @property
  def subtotal(self):
      """Calculate subtotal for this item"""
      return self.price_at_purchase * self.quantity