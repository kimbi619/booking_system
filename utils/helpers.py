from decouple import config
import requests
import logging


logger = logging.getLogger(__name__)

def send_sms(phone_number, message):
    """
    Send an SMS to the specified phone number.
    
    Args:
        phone_number (str): The recipient's phone number.
        message (str): The message to be sent.
    
    Returns:
        bool: True if the SMS was sent successfully, False otherwise.
    """
    url = "https://smsvas.com/bulk/public/index.php/api/v1/sendsms"
    
    payload = {
        "user": "favourexpresssarl@gmail.com",
        "password": "Some@@22024",
        "senderid": "Favour Express",
        "sms": message,
        "mobiles": phone_number
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logger.info(f"SMS sent successfully to {phone_number}")
        return True
    except requests.RequestException as e:
        logger.error(f"Error sending SMS to {phone_number}: {e}")
        return False