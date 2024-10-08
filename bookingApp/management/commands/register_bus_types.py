import json
from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import BusType 
from django.conf import settings

class Command(BaseCommand):
    help = 'Register default bus types'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to the JSON file containing bus type data')

    def handle(self, *args, **options):
        file_path = settings.BASE_DIR / 'bookingApp/management/commands/bus_types.json'
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Invalid JSON in file: {file_path}'))
            return

        with transaction.atomic():
            for bus_type_data in data['bus_types']:
                name = bus_type_data['name']
                capacity = bus_type_data['capacity']
                bus_type = BusType.objects.create_or_update(name=name, capacity=capacity)
                self.stdout.write(self.style.SUCCESS(f'Processed bus type: {name} (Capacity: {capacity})'))

        self.stdout.write(self.style.SUCCESS('Successfully registered default bus types'))