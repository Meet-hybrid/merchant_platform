from django.db import transaction
from rest_framework import serializers
from merchant.models import Merchant, Product, ProductVariant, Order, OrderItem

class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        return Merchant.objects.create_user(**validated_data)

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = '__all__'

    def validate_product(self, value):
        # Complex Business Rule: Verify that the product belongs to the authenticated merchant.
        request = self.context.get('request')
        if request and request.user and value.merchant != request.user:
            raise serializers.ValidationError("You do not have permission to add variants to this product.")
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'productVariant']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customerName', 'customerPhone', 'customerAddress', 'totalPrice', 'merchant', 'items']
        read_only_fields = ['merchant']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            for item in items_data:
                variant = item['productVariant']
                # Transactional Lock: Locks the variant row to prevent race conditions during concurrent stock updates.
                locked_variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)
                
                # Complex Business Rule: Verify stock availability and decrement count for the ordered item.
                if locked_variant.stock < 1:
                    raise serializers.ValidationError(f"Variant {locked_variant.color} - {locked_variant.size} is out of stock.")
                
                locked_variant.stock -= 1
                locked_variant.save()
                
                OrderItem.objects.create(order=order, productVariant=locked_variant)
            
            return order
