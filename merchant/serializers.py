from django.db import transaction
from rest_framework import serializers
from merchant.models import Merchant, Product, ProductVariant, Order, OrderItem
from merchant.exceptions import OutOfStockException

class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'storeName']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        return Merchant.objects.create_user(**validated_data)

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['merchant']

    def validate(self, attrs):
        name = attrs.get('name')
        request = self.context.get('request')
        if request and name:
            queryset = Product.objects.filter(merchant=request.user, name=name)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({"name": "A product with this name already exists for your store."})
        return attrs

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = '__all__'

    def validate_product(self, value):
        request = self.context.get('request')
        if request and request.user and value.merchant != request.user:
            raise serializers.ValidationError("You do not have permission to add variants to this product.")
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'productVariant', 'quantity', 'unit_price']
        read_only_fields = ['unit_price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customerName', 'customerPhone', 'customerAddress', 'totalPrice', 'merchant', 'items']
        read_only_fields = ['merchant', 'totalPrice']

    def create(self, validated_data):
        items_data = validated_data.pop('items')

        with transaction.atomic():
            total = 0
            order = Order.objects.create(totalPrice=0, **validated_data)

            for item in items_data:
                variant = item['productVariant']
                qty = item.get('quantity', 1)

                variant_id = variant.pk if hasattr(variant, 'pk') else variant
                locked_variant = ProductVariant.objects.select_for_update().get(pk=variant_id)

                # Ensure product is active
                if not locked_variant.product.isActive:
                    raise serializers.ValidationError(f"Product {locked_variant.product.name} is not active.")

                if locked_variant.stock < qty:
                    raise OutOfStockException(f"Variant {locked_variant.color} - {locked_variant.size} does not have enough stock.")

                # determine unit price
                unit_price = locked_variant.priceOverride if locked_variant.priceOverride is not None else locked_variant.product.price

                # decrement stock
                locked_variant.stock -= qty
                locked_variant.save()

                line_total = unit_price * qty
                total += line_total

                OrderItem.objects.create(
                    order=order,
                    productVariant=locked_variant,
                    quantity=qty,
                    unit_price=unit_price
                )

            # save computed total
            order.totalPrice = total
            order.save()

            return order
