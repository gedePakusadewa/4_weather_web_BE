from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import UserSerializer, SettingSerializer
from rest_framework import status, generics
from django.contrib.auth.models import User
from weather.models import Setting as SettingModel
from rest_framework.authtoken.models import Token

from django.shortcuts import get_object_or_404

from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

import requests
from django.http import JsonResponse

from weather.constants.general import ProfileConstants, EnvConstants, GeneralConstants, UserConstants, SettingConstants

class LogIn(generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    demo_username = getattr(settings, EnvConstants.USERNAME_DEMO, None)

    def post(self, request):
        try:
            is_demo = request.data['isDemo']

            if is_demo:
                user = get_object_or_404(User, username=self.demo_username)
            else:
                user = get_object_or_404(User, username=request.data['username'])

            if not is_demo and not user.check_password(request.data['password']):
                return Response(
                    { GeneralConstants.MESSAGE:UserConstants.NOT_FOUND },
                    status=status.HTTP_404_NOT_FOUND
                )

            token, created = Token.objects.get_or_create(user=user)
            serializer = UserSerializer(instance=user)

            return Response({
                GeneralConstants.TOKEN:token.key,
                UserConstants.USER:serializer.data
            })
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:GeneralConstants.ERROR_IN_LOG_IN },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SignUp(generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)

            if serializer.is_valid():
                serializer.save()
                user = User.objects.get(username=request.data['username'])
                user.set_password(request.data['password'])
                user.save()  
                token = Token.objects.create(user=user)

                # default data for setting
                # default_setting = {
                #     "city":"JAKARTA",
                #     "unit":"CELCIUS",
                #     "user_id":user.id
                # }
                # serializer_setting = SettingSerializer(data=default_setting)

                # if serializer_setting.is_valid():
                #     serializer_setting.save()
                # else:
                #     return Response(serializer_setting.errors, status=status.HTTP_400_BAD_REQUEST)

                return Response({
                    GeneralConstants.TOKEN:token.key,
                    UserConstants.USER:serializer.data
                })
            
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:GeneralConstants.ERROR_IN_SIGN_UP },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        

class LogOut(generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            request.user.auth_token.delete()

            return Response(
                { GeneralConstants.SUCCESS:GeneralConstants.SUCCESS_LOG_OUT },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:GeneralConstants.ERROR_IN_SIGN_UP },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class Weather(generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_setting(self, user_id):
        try:        
            return SettingModel.objects.get(user_id=user_id)
        except Exception as e:
            return None

    def get(self, request):
        try:
            weather_url = getattr(settings, EnvConstants.WEATHER_API, None)
            weather_api_key = getattr(settings, EnvConstants.WEATHER_API_KEY, None)

            user_id = Token.objects.get(key=request.auth.key).user_id
            settingData = self.get_setting(user_id)            

            url = weather_url + "?key=" + weather_api_key + "&q=" + settingData.city + "&aqi=no&alerts=no&days=8"
            response = requests.get(url)
            data = response.json()
            
            data["unit_degree"] = settingData.unit
            
            return JsonResponse(data)
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:GeneralConstants.ERROR_GETTING_WEATHER },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class Setting(generics.GenericAPIView):
    serializer_class = SettingSerializer
    queryset = SettingModel.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_id = Token.objects.get(key=request.auth.key).user_id
            settingData = self.get_setting(user_id)

            if settingData == None:
                request.data["user"] = user_id
                
                serializer_class = self.serializer_class(data=request.data)

                if serializer_class.is_valid():
                    serializer_class.save()

                    return Response(
                        serializer_class.data,
                        status=status.HTTP_201_CREATED
                    )
            else:
                serializer_class = self.serializer_class(settingData, data=request.data, partial=True)

                if serializer_class.is_valid():
                    serializer_class.save()

                    return Response(
                        serializer_class.data,
                        status=status.HTTP_200_OK
                    )
            
            return Response(
                serializer_class.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:GeneralConstants.ERROR_IN_SETTING },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        

    def get_setting(self, user_id):
        try:        
            return SettingModel.objects.get(user_id=user_id)
        except Exception as e:
            return None
    
    def get(self, request):        
        user_id = Token.objects.get(key=request.auth.key).user_id
        settingData = self.get_setting(user_id)

        if not settingData:
            return Response(
                { GeneralConstants.MESSAGE:SettingConstants.NOT_FOUND },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer_class = self.serializer_class(settingData)
        
        return Response(serializer_class.data)
    
class Profile(generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_setting(self, user_id):
        try:        
            return SettingModel.objects.get(user_id=user_id)
        except Exception as e:
            return None

    def get(self, request):
        try:
            user_id = Token.objects.get(key=request.auth.key).user_id
            settingData = self.get_setting(user_id)
            user = User.objects.get(pk=user_id)

            if not settingData:
                return Response(
                    { GeneralConstants.MESSAGE:SettingConstants.NOT_FOUND },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not user:
                return Response(
                    { GeneralConstants.MESSAGE:UserConstants.NOT_FOUND },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer_setting = SettingSerializer(settingData)
            serializer_user = self.serializer_class(instance=user)

            return Response({
                UserConstants.USER : serializer_user.data,
                SettingConstants.SETTING : serializer_setting.data})
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:ProfileConstants.ERROR_IN_PROFILE },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        try:
            user_id = Token.objects.get(key=request.auth.key).user_id
            user = User.objects.get(pk=user_id)

            if user is not None:
                serializer_user = self.serializer_class(user, data=request.data, partial=True)

                if  serializer_user.is_valid():
                    serializer_user.save()

                    return Response(status=status.HTTP_200_OK)
                
            return Response(
                serializer_user.errors,
                status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:ProfileConstants.ERROR_IN_PROFILE },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def delete(self, request):
        try:
            user_id = Token.objects.get(key=request.auth.key).user_id
            user = User.objects.get(pk=user_id)
            if not user:
                return Response(
                    { GeneralConstants.MESSAGE:UserConstants.NOT_FOUND },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            settingData = self.get_setting(user_id)
            if not settingData:
                return Response(
                    { GeneralConstants.MESSAGE:SettingConstants.NOT_FOUND },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            user.delete()
            settingData.delete()
            
            return Response(
                { GeneralConstants.MESSAGE:GeneralConstants.DELETE_SUCCED },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                { GeneralConstants.MESSAGE:ProfileConstants.ERROR_IN_PROFILE },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

