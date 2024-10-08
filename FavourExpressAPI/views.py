from django.shortcuts import render

from django.utils import translation
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions



def not_found(request, exception):
    return render(request, '404.html', status=404)

def index(request):
    return render(request, 'index.html')