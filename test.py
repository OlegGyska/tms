from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

users = User.objects.all()

groups = user.groups.all()


Permission(name='test', content_type='tmsmain.test_perm', codename='test_perm')

ValueError: Cannot assign "'tmsmain.test_perm'": "Permission.content_type" must be a "ContentType" instance.
