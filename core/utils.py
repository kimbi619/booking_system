from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils import timezone, dateparse, dateformat
from datetime import timedelta

class Util:
    @staticmethod
    def send_email(data):
        email = EmailMultiAlternatives(
            subject=data['email_subject'], 
            body=data['email_body'],
            to=[data['to_email']]
        )
        email.send() 

    @staticmethod
    def get_last_30_days():
        return timezone.now() - timedelta(days=30)