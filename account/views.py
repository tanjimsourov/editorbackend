from rest_framework.generics import GenericAPIView, UpdateAPIView
from rest_framework.response import Response
from account.serializers import *
from rest_framework import response, status, permissions
from django.contrib.auth import authenticate

from .otp import generateKey, verify_otp
# from .sendOtp import send
from .serializers import (RegisterSerializer,)


class RegisterAPIView(GenericAPIView):
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            # key = generateKey()
            # user = User(username=serializer.data['username'],
            #             phone=serializer.data['phone'], otp=key['OTP'],
            #             activation_key=key['totp'], )
            # user.set_password(serializer.data['password'])
            serializer.save()
            # print(key['OTP'])
            # send(serializer.data['phone'], key['OTP'])
            # send otp
            return Response({"username": serializer.data['username'], "token": serializer.data['token'],
                             }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(GenericAPIView):
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username', None)
        password = request.data.get('password', None)
        user = authenticate(username=username, password=password)

        if user:
            if user.is_verified:
                return response.Response({"username": user.username, "token": user.token},
                                         status=status.HTTP_200_OK)
            # send(user.phone, user.otp)
            return response.Response({"message": "Please Verify Your account"}, status=status.HTTP_408_REQUEST_TIMEOUT)
        return response.Response({'message': "Invalid credentials, try again"}, status=status.HTTP_401_UNAUTHORIZED)
