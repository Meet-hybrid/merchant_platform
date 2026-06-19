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
