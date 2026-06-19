from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from merchant.models import Merchant, Product, ProductVariant, Order, OrderItem

class MerchantAuthTests(APITestCase):
    def test_registration(self):
        url = reverse('merchant-register')
        data = {
            'username': 'testmerchant',
            'email': 'merchant@test.com',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'Merchant',
            'storeName': 'Test Store'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        
        merchant = Merchant.objects.get(username='testmerchant')
        self.assertTrue(merchant.check_password('testpassword123'))
        self.assertEqual(merchant.storeName, 'Test Store')

    def test_login(self):
        Merchant.objects.create_user(username='loginmerchant', password='password123')
        url = reverse('merchant-login')
        data = {
            'username': 'loginmerchant',
            'password': 'password123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

class ProductAndVariantTests(APITestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create_user(username='merchant1', password='password123')
        self.token = Token.objects.create(user=self.merchant)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        self.other_merchant = Merchant.objects.create_user(username='merchant2', password='password123')
        self.other_token = Token.objects.create(user=self.other_merchant)

    def test_create_product(self):
        url = reverse('product-list')
        data = {
            'name': 'Laptop',
            'description': 'A nice laptop',
            'price': '999.99',
            'category': 'Electronics',
            'images': ['http://image.com/1.png'],
            'isActive': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Product.objects.first().merchant, self.merchant)

    def test_product_unique_name_per_merchant(self):
        Product.objects.create(merchant=self.merchant, name='Laptop', price=999.99, category='Electronics')
        url = reverse('product-list')
        data = {
            'name': 'Laptop',
            'price': '899.99',
            'category': 'Electronics'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_product_ownership_validation_for_variant(self):
        other_product = Product.objects.create(merchant=self.other_merchant, name='Phone', price=499.99, category='Electronics')
        url = reverse('variant-list')
        data = {
            'product': other_product.id,
            'color': 'Black',
            'size': 'Standard',
            'stock': 10,
            'priceOverride': '479.99'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('product', response.data)

    def test_nested_create_variant_for_product(self):
        product = Product.objects.create(merchant=self.merchant, name='Shirt', price=29.99, category='Clothing')
        url = reverse('product-variants', kwargs={'product_id': product.id})
        data = {
            'color': 'Blue',
            'size': 'L',
            'stock': 5,
            'priceOverride': '27.99'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProductVariant.objects.filter(product=product).count(), 1)

    def test_list_variants_for_product(self):
        product = Product.objects.create(merchant=self.merchant, name='Shoes', price=49.99, category='Footwear')
        ProductVariant.objects.create(product=product, color='Black', size='M', stock=10)
        url = reverse('product-variants', kwargs={'product_id': product.id})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class OrderTests(APITestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create_user(username='merchant', password='password123')
        self.token = Token.objects.create(user=self.merchant)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        self.product = Product.objects.create(merchant=self.merchant, name='Shirt', price=19.99, category='Clothing')
        self.variant = ProductVariant.objects.create(product=self.product, color='Red', size='M', stock=2)

    def test_order_creation_decrements_stock(self):
        url = reverse('order-list')
        data = {
            'customerName': 'John Doe',
            'customerPhone': '1234567890',
            'customerAddress': '123 Main St',
            'items': [
                {'productVariant': self.variant.id, 'quantity': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        print('DEBUG_ORDER_RESPONSE', response.status_code, response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 0)
        
        order = Order.objects.first()
        self.assertEqual(order.totalPrice, Decimal('39.98'))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(OrderItem.objects.first().quantity, 2)
        self.assertEqual(OrderItem.objects.first().unit_price, Decimal('19.99'))

    def test_order_creation_fails_out_of_stock(self):
        self.variant.stock = 0
        self.variant.save()
        
        url = reverse('order-list')
        data = {
            'customerName': 'Michael Philip',
            'customerPhone': '1234567890',
            'customerAddress': '312 Herbert Macaulay ',
            'totalPrice': '0.00',
            'items': [
                {'productVariant': self.variant.id}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify custom error structure is returned
        self.assertEqual(response.data['error_type'], 'inventory_shortage')
        self.assertEqual(response.data['code'], 'out_of_stock')
        
        # Verify transaction rolled back completely
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_orders_dashboard_stats(self):
        product = Product.objects.create(merchant=self.merchant, name='Pants', price=29.99, category='Clothing', isActive=True)
        variant = ProductVariant.objects.create(product=product, color='Blue', size='L', stock=3)
        order_data = {
            'customerName': 'Meet Hybrid',
            'customerPhone': '555-5555',
            'customerAddress': '456 Park Ave',
            'items': [
                {'productVariant': variant.id, 'quantity': 1}
            ]
        }
        self.client.post(reverse('order-list'), order_data, format='json')

        url = reverse('dashboard-stats')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totalOrders'], 1)
        self.assertEqual(response.data['totalRevenue'], Decimal('29.99'))
        self.assertEqual(response.data['totalProducts'], 2)
        self.assertEqual(response.data['totalActiveProducts'], 2)
        self.assertIn('lowStockVariants', response.data)
        self.assertIn('topSellingProducts', response.data)
