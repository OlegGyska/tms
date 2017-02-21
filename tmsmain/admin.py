from django.contrib import admin

from .models import Region
from .models import Object
from .models import SimCard
from .models import DeviceType
from .models import Device
from .models import ReplacedEquipment
from .models import TaskLabel
from .models import Task
from .models import TempEquipment
from .models import Action
from .models import Request
from .models import UserEx

# Register your models here.

admin.site.register(Region)
admin.site.register(Object)
admin.site.register(SimCard)
admin.site.register(DeviceType)
admin.site.register(Device)
admin.site.register(ReplacedEquipment)
admin.site.register(TaskLabel)
admin.site.register(Task)
admin.site.register(TempEquipment)
admin.site.register(Action)
admin.site.register(Request)
admin.site.register(UserEx)
