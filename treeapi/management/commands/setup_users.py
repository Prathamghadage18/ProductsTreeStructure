"""
Management command to set up users for the RBAC system.
Usage:
    python manage.py setup_users --create-superuser
    python manage.py setup_users --create-normal-user <username>
    python manage.py setup_users --add-to-allowed <username>
    python manage.py setup_users --list-allowed
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from treeapi.models import AllowedUser


class Command(BaseCommand):
    help = 'Set up users for the RBAC system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a superuser interactively',
        )
        parser.add_argument(
            '--create-normal-user',
            type=str,
            help='Create a normal user with the given username',
        )
        parser.add_argument(
            '--add-to-allowed',
            type=str,
            help='Add an existing user to the allowed users list',
        )
        parser.add_argument(
            '--remove-from-allowed',
            type=str,
            help='Remove a user from the allowed users list',
        )
        parser.add_argument(
            '--list-allowed',
            action='store_true',
            help='List all allowed users',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for new user (only with --create-normal-user)',
        )

    def handle(self, *args, **options):
        if options['create_superuser']:
            self.create_superuser()
        
        elif options['create_normal_user']:
            self.create_normal_user(options['create_normal_user'], options.get('password'))
        
        elif options['add_to_allowed']:
            self.add_to_allowed(options['add_to_allowed'])
        
        elif options['remove_from_allowed']:
            self.remove_from_allowed(options['remove_from_allowed'])
        
        elif options['list_allowed']:
            self.list_allowed()
        
        else:
            self.stdout.write(self.style.WARNING('No action specified. Use --help for options.'))

    def create_superuser(self):
        """Create a superuser interactively."""
        self.stdout.write(self.style.SUCCESS('Creating superuser...'))
        from django.core.management import call_command
        call_command('createsuperuser')

    def create_normal_user(self, username, password=None):
        """Create a normal user and optionally add to allowed users."""
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User "{username}" already exists.'))
            return

        if not password:
            password = input('Enter password: ')
        
        user = User.objects.create_user(username=username, password=password)
        self.stdout.write(self.style.SUCCESS(f'User "{username}" created successfully.'))
        
        # Ask if they want to add to allowed users
        add_to_allowed = input('Add to allowed users list? (y/n): ').lower() == 'y'
        if add_to_allowed:
            self.add_to_allowed(username)

    def add_to_allowed(self, username):
        """Add a user to the allowed users list."""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" does not exist.'))
            return

        if user.is_superuser:
            self.stdout.write(self.style.WARNING(f'User "{username}" is a superuser and does not need to be in allowed users list.'))
            return

        # Check if already in allowed users
        if AllowedUser.objects.filter(user=user).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" is already in allowed users list.'))
            return

        # Check if we have reached the limit
        if AllowedUser.objects.count() >= 9:
            self.stdout.write(self.style.ERROR('Maximum of 9 allowed users reached. Cannot add more.'))
            return

        AllowedUser.objects.create(user=user)
        self.stdout.write(self.style.SUCCESS(f'User "{username}" added to allowed users list.'))

    def remove_from_allowed(self, username):
        """Remove a user from the allowed users list."""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" does not exist.'))
            return

        try:
            allowed_user = AllowedUser.objects.get(user=user)
            allowed_user.delete()
            self.stdout.write(self.style.SUCCESS(f'User "{username}" removed from allowed users list.'))
        except AllowedUser.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'User "{username}" is not in allowed users list.'))

    def list_allowed(self):
        """List all allowed users."""
        allowed_users = AllowedUser.objects.all()
        
        if not allowed_users:
            self.stdout.write(self.style.WARNING('No allowed users found.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Allowed users ({allowed_users.count()}/9):'))
        for allowed_user in allowed_users:
            self.stdout.write(f'  - {allowed_user.user.username} (created: {allowed_user.created_at})')
