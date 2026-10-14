
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _



class UserManager(BaseUserManager):

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):

        if not email:
            raise ValueError("Email address is required.")

        email = self.normalize_email(email).lower()
        user  = self.model(email=email, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        if not password:
            raise ValueError("Superuser password is required.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.STAFF)

        if extra_fields["is_staff"] is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):

    class Role(models.TextChoices):
        STAFF   = "staff", "Staff"
        MEMBER  = "member", "Member"

    full_name = models.CharField(_("full name"), max_length=255, blank=True,null=True)
    email     = models.EmailField(_("email address"), unique=True, blank=False, null=False)
    role      = models.CharField("role",max_length=10,choices=Role.choices,default=Role.MEMBER,blank=False,null=False)
    is_active = models.BooleanField(_("active"), default=True)
    is_staff  = models.BooleanField(_("staff status"), default=False)
    is_admin  = models.BooleanField(_("admin status"), default=False)
    password  = models.CharField(_("password"), max_length=128, blank=False, null=False)
    objects   = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_user_email_ci",
            ),
        ]

    def __str__(self):
        return self.email
