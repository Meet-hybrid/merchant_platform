from django.contrib.auth import authenticate
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from merchant.models import Product, ProductVariant, Order, Merchant
from merchant.serializers import (
    MerchantSerializer, 
    ProductSerializer, 
    ProductVariantSerializer, 
    OrderSerializer
)
from rest_framework.views import APIView
from django.db.models import Sum, F
from merchant.models import OrderItem

class MerchantRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MerchantSerializer(data=request.data)
        if serializer.is_valid():
            merchant = serializer.save()
            token, _ = Token.objects.get_or_create(user=merchant)
            return Response({
                'merchant': serializer.data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MerchantLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Both username and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        merchant = authenticate(username=username, password=password)
        if merchant is not None:
            token, _ = Token.objects.get_or_create(user=merchant)
            return Response({
                'token': token.key,
                'username': merchant.username
            }, status=status.HTTP_200_OK)
            
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(merchant=self.request.user)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user)

class ProductVariantViewSet(viewsets.ModelViewSet):
    serializer_class = ProductVariantSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProductVariant.objects.filter(product__merchant=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(merchant=self.request.user)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user)


class ProductVariantListCreate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id):
        variants = ProductVariant.objects.filter(product_id=product_id, product__merchant=request.user)
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)

    def post(self, request, product_id):
        # ensure product belongs to merchant
        try:
            product = Product.objects.get(pk=product_id, merchant=request.user)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['product'] = product.id
        serializer = ProductVariantSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardStats(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        merchant = request.user

        total_orders = Order.objects.filter(merchant=merchant).count()
        total_revenue = Order.objects.filter(merchant=merchant).aggregate(total=Sum('totalPrice'))['total'] or 0
        total_products = Product.objects.filter(merchant=merchant).count()
        total_active_products = Product.objects.filter(merchant=merchant, isActive=True).count()

        low_stock_variants = list(ProductVariant.objects.filter(product__merchant=merchant, stock__lt=5).values('id','product_id','color','size','stock'))

        # top selling products (by quantity)
        top_products_qs = (
            OrderItem.objects.filter(order__merchant=merchant)
            .values(product_id=F('productVariant__product'))
            .annotate(sold=Sum('quantity'))
            .order_by('-sold')[:5]
        )
        top_selling = []
        for item in top_products_qs:
            try:
                prod = Product.objects.get(pk=item['product_id'])
                top_selling.append({'product_id': prod.id, 'name': prod.name, 'sold': item['sold']})
            except Product.DoesNotExist:
                continue

        return Response({
            'totalOrders': total_orders,
            'totalRevenue': total_revenue,
            'totalProducts': total_products,
            'totalActiveProducts': total_active_products,
            'lowStockVariants': low_stock_variants,
            'topSellingProducts': top_selling,
        })
