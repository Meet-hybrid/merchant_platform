from rest_framework.exceptions import APIException
from rest_framework import status

class OutOfStockException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'The requested product variant is out of stock.'
    default_code = 'out_of_stock'

    def __init__(self, detail=None, code=None):
        message = detail if detail is not None else self.default_detail
        self.detail = {
            'error_type': 'inventory_shortage',
            'message': message,
            'code': code or self.default_code
        }
