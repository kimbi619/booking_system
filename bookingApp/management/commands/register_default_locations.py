import json
from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import Region, City 
from django.conf import settings

class Command(BaseCommand):
    help = 'Register default locations for Cameroon'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to the JSON file containing location data')

    def handle(self, *args, **options):
        file_path = settings.BASE_DIR / 'bookingApp/management/commands/locations.json' 
        
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
            for region_data in data['regions']:
                region_name = region_data['name']
                region = Region.active.create_or_update(name=region_name)
                self.stdout.write(self.style.SUCCESS(f'Processed region: {region_name}'))

                for city_name in region_data['cities']:
                    city = City.active.create_or_update(name=city_name, region=region, abbr=region_data['abbr'])
                    self.stdout.write(self.style.SUCCESS(f'Processed city: {city_name}'))

        self.stdout.write(self.style.SUCCESS('Successfully registered default locations'))