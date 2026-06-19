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
            'last_name': 'Merchant'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        
        merchant = Merchant.objects.get(username='testmerchant')
        self.assertTrue(merchant.check_password('testpassword123'))

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
            'totalPrice': '19.99',
            'items': [
                {'productVariant': self.variant.id}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 1)
        
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(OrderItem.objects.first().productVariant, self.variant)

    def test_order_creation_fails_out_of_stock(self):
        self.variant.stock = 0
        self.variant.save()
        
        url = reverse('order-list')
        data = {
            'customerName': 'John Doe',
            'customerPhone': '1234567890',
            'customerAddress': '123 Main St',
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
