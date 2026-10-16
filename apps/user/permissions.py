from rest_framework.permissions import DjangoModelPermissions


class UserModelPermissions(DjangoModelPermissions):
    """DjangoModelPermissions that also require ``view_user`` for reads.

    The default map lets any authenticated user GET; user records hold personal data,
    so listing/retrieving them is a management action too. Superusers always pass.
    """

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
    }
