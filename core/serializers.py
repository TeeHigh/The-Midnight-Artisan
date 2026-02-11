from rest_framework import serializers
from .models import Inventory, Order, OrderItem

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ['id', 'product_name', 'product_price', 'stock_quantity', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_product_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Product price must be greater than 0")
        return value
    
    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value 


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(write_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    price_at_purchase = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_name', 'quantity', 'price_at_purchase', 'subtotal']
        read_only_fields = ['id', 'price_at_purchase', 'subtotal']
    
    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'customer_name', 'customer_email', 'created_at', 'updated_at', 
                'is_invoice_sent', 'items', 'total_amount']
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_invoice_sent', 'total_amount']
    
    def validate_items(self, value):
        """Ensure at least one item is in the order"""
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        return value
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Create the order
        order = Order.objects.create(**validated_data)
        
        # Create each order item
        for item_data in items_data:
            product_id = item_data.pop('product_id')
            
            try:
                product = Inventory.objects.get(id=product_id)
            except Inventory.DoesNotExist:
                order.delete()
                raise serializers.ValidationError(f"Product with id {product_id} does not exist")
            
            # Check stock availability
            if product.stock_quantity < item_data['quantity']:
                order.delete()
                raise serializers.ValidationError(
                    f"Insufficient stock for {product.product_name}. "
                    f"Available: {product.stock_quantity}, Requested: {item_data['quantity']}"
                )
            
            # Create order item with price at purchase time
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                price_at_purchase=product.product_price
            )
            
            # Reduce inventory
            product.stock_quantity -= item_data['quantity']
            product.save()
        
        return order
    
    def update(self, instance, validated_data):
        instance.customer_name = validated_data.get('customer_name', instance.customer_name)
        instance.customer_email = validated_data.get('customer_email', instance.customer_email)
        instance.save()
        return instance