from django.core.management.base import BaseCommand
from core_app.models import User, Rights


class Command(BaseCommand):
    help = "Create admin user with Rights='Администратор'"

    def add_arguments(self, parser):
        parser.add_argument("--login", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--lastname", default="Админов")
        parser.add_argument("--firstname", default="Админ")
        parser.add_argument("--middlename", default="")
        parser.add_argument("--birthdate", default=None)  
        parser.add_argument("--gender", default=None)    

    def handle(self, *args, **options):
        login = options["login"]
        password = options["password"]

        if User.objects.filter(login=login).exists():
            self.stdout.write(self.style.ERROR(f"User with login '{login}' already exists"))
            return

        admin_right, _ = Rights.objects.get_or_create(rightsname="Администратор")

        user = User(
            login=login,
            lastname=options["lastname"],
            firstname=options["firstname"],
            middlename=options["middlename"] or None,
            idrights=admin_right,
        )

        if options["birthdate"]:
            user.birthdate = options["birthdate"]  

        g = options["gender"]
        if g is not None:
            if str(g).lower() in ("1", "true", "t", "yes", "y"):
                user.gender = True
            elif str(g).lower() in ("0", "false", "f", "no", "n"):
                user.gender = False

        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created admin user: login={user.login}, rights={user.idrights.rightsname}"
        ))