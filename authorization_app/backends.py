from hashlib import sha512

from django.contrib.auth.backends import BaseBackend
from core_app.models import User


class LegacyAndDjangoBackend(BaseBackend):
    LEGACY_SALT = "DsaVfeqsJw00XvgZnFxlOFkqaURzLbyI"

    def authenticate(self, request, login=None, password=None, **kwargs):
        if login is None or password is None:
            return None

        try:
            user = User.objects.select_related("idrights").get(login=login)
        except User.DoesNotExist:
            return None

        if not user.is_active:
            return None

        # 1. Сначала пробуем обычную django-проверку
        if user.check_password(password):
            return user

        # 2. Если не подошло — пробуем старый формат
        legacy_hash = self.get_legacy_hash(password)
        if user.password == legacy_hash:
            # Пароль старого формата подошёл.
            # Сразу пересохраняем его в новом django-формате.
            user.set_password(password)
            user.save(update_fields=["password"])
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @classmethod
    def get_legacy_hash(cls, password):
        return sha512((password + cls.LEGACY_SALT).encode("utf-8")).hexdigest()