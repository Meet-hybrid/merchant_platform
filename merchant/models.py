from django.db import models
from django.contrib.auth.models import AbstractUser

class Merchant(AbstractUser):
    storeName = models.CharField(max_length=255, blank=True)

class Product(models.Model):
    merchant = models.ForeignKey(
        Merchant, 
        on_delete=models.CASCADE, 
        related_name='products'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    images = models.JSONField(default=list, blank=True)
    isActive = models.BooleanField(default=True)

    class Meta:
        unique_together = ('merchant', 'name')

class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='variants'
    )
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=50)
    stock = models.IntegerField(default=0)
    priceOverride = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )

    class Meta:
        unique_together = ('product', 'color', 'size')

class Order(models.Model):
    merchant = models.ForeignKey(
        Merchant, 
        on_delete=models.PROTECT, 
        related_name='orders'
    )
    customerName = models.CharField(max_length=255)
    customerPhone = models.CharField(max_length=20)
    customerAddress = models.TextField()
    totalPrice = models.DecimalField(max_digits=12, decimal_places=2)

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    productVariant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.PROTECT, 
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
