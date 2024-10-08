from django.shortcuts import render
from rest_framework.views import APIView, Response, status
from rest_framework.generics import GenericAPIView
from django.contrib.auth import authenticate

# Create your views here.
from .models import User
from core.utils import Util
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from FavourExpressAPI.settings import FRONTEND_URL


from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes


from rest_framework.parsers import MultiPartParser
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse

import jwt
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
import random
from utils.helpers import send_sms
from utils.workers import send_sms_with_template
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


class VerifyEmail(GenericAPIView):
    def get(self, request):
        token = request.GET.get('token')
        try:
            response = jwt.decode(token,settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=response['user_id'])
            
            if not user.email_verified:
                user.email_verified = True
                user.is_active = True
                user.save()
            return Response({"success": "account verified"}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError as invalidToken:
            return Response({"error": "Activation time out"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            print(e)
            return Response({"error": e}, status=status.HTTP_403_FORBIDDEN)



class Utils: 
    def get_user_by_phone(phone):
        user = User.objects.filter(phone=phone).first()  
        return user  


class ListUsers(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_id = request.user.id
        # Filter all active users except for current user
        users = User.objects.filter(is_active=True).exclude(id=user_id).order_by('last_login')
        serializer = RegisterSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK) 
    



class RegisterAPIView(GenericAPIView):

    serializer_class = RegisterSerializer

    def generate_verification_code(self):
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    

    def sendRegisterSMS(self, user):

        data = {
            'msg': 'Account created successfully',
        }
        send_sms_with_template(data, [user["phone"]])


    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            try:
                user = serializer.save()
                
                verification_code = self.generate_verification_code()
                user.phone_verification_code = verification_code
                user.save()

                self.sendRegisterSMS(serializer.data)

                if send_sms(user.phone, verification_code):
                    return Response({
                        'message': 'User registered successfully. Please check your phone for the verification code.',
                        'user': serializer.data
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        'message': 'User registered successfully, but there was an error sending the verification SMS. Please try to resend the code.',
                        'user': serializer.data
                    }, status=status.HTTP_201_CREATED)
                
            except IntegrityError:
                return Response({
                    'message': 'A user with this phone number already exists.',
                }, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class LoginAPIView(GenericAPIView):

    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')

        if not phone or not password:
            return Response({'error': 'Both phone and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, phone=phone, password=password)

        if user is not None:

            refresh = RefreshToken.for_user(user)
            user_serializer = LoginSerializer(user)

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        
        else:
            logger.warning(f"Failed login attempt for phone: {phone}")
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        
class UserView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = RegisterSerializer(user)

        return Response(serializer.data, status=status.HTTP_200_OK)
    



class RequestPasswordReset(GenericAPIView):

    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        try:
            email = request.data.get('email')
            
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                user_id_bytes = force_bytes(user.id)
                uidb64 = urlsafe_base64_encode(user_id_bytes)
                token = PasswordResetTokenGenerator().make_token(user)

                relativeLink = f'/reset-password?uid={uidb64}&token={token}'
                absurl = FRONTEND_URL + relativeLink

                data = {
                    'email_subject': 'Reset password',
                }
                
                context = {
                    'user': LoginSerializer(user).data,
                    'reset_url': absurl
                }

                # send_email_with_template.delay(data, 'reset_password.html', context, [user.email])
            else:
                return Response({"message": "User with the given email does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as errors:
            return Response({"error": str(errors)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"success": "we have sent you a link to reset your password"}, status=status.HTTP_200_OK)


class ChangePassword(GenericAPIView):
    def post(self, request):
        uidb64 = request.GET.get('uid')
        token = request.GET.get('token')
        new_password = request.data.get('password')
        
        if not uidb64 or not token or not new_password:
            return Response({"error": "Request not valid, check the documentations"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = str(urlsafe_base64_decode(uidb64), 'utf-8')   
            user = User.objects.get(id=uid)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid user id"}, status=status.HTTP_400_BAD_REQUEST)

        if PasswordResetTokenGenerator().check_token(user, token):
            user.set_password(new_password)
            user.save()

            return Response({"success": "Password reset successfully"}, status=status.HTTP_200_OK)

        else:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)



class PasswordTokenCheck(GenericAPIView):

    def get(self, request, uidb64, token):

        data = request.data
        print(data)

        return Response({"success": "we have sent you a link to reset your password"}, status=status.HTTP_200_OK)


class UpdateUserInformation(GenericAPIView):
    parser_classes = [MultiPartParser] 
    serializer_class = UserUpdateSerializer 
    permission_classes = [IsAuthenticated]

    def get_object(self, user_id):
        try:
            user = User.objects.get(id=user_id)
            if self.request.user != user and not self.request.user.is_staff:
                raise PermissionDenied("You don't have permission to access this user's information.")
            return user
        except User.DoesNotExist:
            return None
    
    def get(self, request, user_id):
        user = self.get_object(user_id)
        if not user:
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


    def patch(self, request, user_id):

        user = self.get_object(user_id)
        if not user:
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer_class(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class VerifyPhoneAPIView(APIView):

    def post(self, request):
        phone = request.data.get('phone')
        code = request.data.get('code')
        
        try:
            user = User.objects.get(phone=phone, phone_verification_code=code)
            user.phone_verified = True

            user.phone_verification_code = None
            
            user.save()

            return Response({'message': 'Phone number verified successfully.'}, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({'error': 'Invalid phone number or verification code.'}, status=status.HTTP_400_BAD_REQUEST)


