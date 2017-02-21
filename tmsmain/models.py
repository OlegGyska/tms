# coding: utf8
from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Region(models.Model):
    name = models.CharField(max_length=25)


class Object(models.Model):
    TYPES = ((1, "Охоронний"),
             (2, "Пожежний"),
             (3, "Охоронно-пожежний"),
             (4, "Непультовий")
             )

    number = models.CharField(max_length=7)
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=150)
    region = models.ForeignKey(Region, on_delete=models.SET(1))
    type = models.IntegerField(choices=TYPES)
    contract = models.CharField(max_length=12)
    active = models.BooleanField()
    deleted = models.BooleanField()
    comment = models.TextField()


class UserEx(models.Model):
    ROLES = ((1, 'Адміністратор'),
             (2, 'Супервізор'),
             (3, 'Оператор'),
             (4, 'Користувач')
             )
    ADMIN = 1
    SUPERVISOR = 2
    OPERATOR = 3
    USER = 4

    name = models.OneToOneField(User, related_name='ex', on_delete=models.CASCADE)
    role = models.IntegerField(choices=ROLES)
    canclose = models.BooleanField()  # for future usage
    fired = models.BooleanField()  # for future usage

    def has_access(self, role):
        if self.role <= role:
            return True
        else:
            return False


class SimCard(models.Model):
    objectid = models.ForeignKey(Object, on_delete=models.SET(1))
    number = models.IntegerField()
    iccid = models.CharField(max_length=19)
    comment = models.CharField(max_length=200)
    suspended = models.BooleanField()
    lost = models.BooleanField()


class DeviceType(models.Model):
    CHANNEL_TYPE = ((1, 'GPRS'),
                    (2, 'GPRS + Ethernet'),
                    (3, 'Радіо'),
                    (4, 'Лінія'),
                    (5, 'Зовнішній комм.'),
                    )

    name = models.CharField(max_length=25)
    channeltype = models.IntegerField(choices=CHANNEL_TYPE)
    dualsim = models.BooleanField()
    iscommunicator = models.BooleanField()
    deleted = models.BooleanField()


class Device(models.Model):
    type = models.ForeignKey(DeviceType, on_delete=models.SET(1))
    objectid = models.ForeignKey(Object, on_delete=models.SET(1))
    rent = models.BooleanField()
    serial = models.CharField(max_length=16)
    comment = models.CharField(max_length=200)


class ReplacedEquipment(models.Model):
    TYPE = ((1, 'Сповіщувач'),
            (2, 'Акумулятор'),
            (3, 'Комунікатор'),
            (4, 'Прилад'),
            (5, 'Інше'),
            )

    objectid = models.ForeignKey(Object, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    type = models.IntegerField(choices=TYPE)
    date = models.DateTimeField()
    quantity = models.IntegerField()
    comment = models.CharField(max_length=200)


class TaskLabel(models.Model):
    name = models.CharField(max_length=25)
    deleted = models.BooleanField()


class Task(models.Model):
    EVENT_TYPE = ((1, 'Хибна подія'),
                  (2, 'Несправність'),
                  (3, 'Зв\'язок'),
                  (4, 'Заява замовника'),
                  (5, 'Внутрішнє завдання'),
                  (6, 'Інше')
                  )

    PRIORITY = ((1, 'Низький'),
                (2, 'Звичайний'),
                (3, 'Високий'),
                (4, 'Критичний')
                )

    STATUS_SELECT_LIMIT = 5
    ACTIVE_N = 1
    PEND_N = 3
    CLOSE_N = 6
    CLOSE_PEND_N = 2

    STATUS = ((1, 'Активне'),
              (2, 'Очікується підтвердження'),
              (3, 'Відтермін. до:'),
              (4, 'Очікуються дії замовника'),
              (5, 'Очікується забезпечення'),
              (6, 'Виконано'))

    objectid = models.ForeignKey(Object, on_delete=models.CASCADE)
    eventtime = models.DateTimeField()
    eventtype = models.IntegerField(choices=EVENT_TYPE)
    label = models.ForeignKey(TaskLabel, on_delete=models.SET(1))
    description = models.CharField(max_length=250)
    creator = models.ForeignKey(User, related_name='task_creator', on_delete=models.SET(1))
    priority = models.IntegerField(choices=PRIORITY)
    status = models.IntegerField(choices=STATUS)
    assignedto = models.ForeignKey(User, related_name='task_assignedto', on_delete=models.SET(1))
    lastactivity = models.DateTimeField()
    delaytill = models.DateTimeField()
    opened = models.DateTimeField()
    closed = models.DateTimeField()


class TempEquipment(models.Model):
    TYPE = ((1, 'Сповіщувач'),
            (2, 'Акумулятор'),
            (3, 'Комунікатор'),
            (4, 'Прилад'),
            (5, 'Інше'),
            )

    objectid = models.ForeignKey(Object, on_delete=models.SET(1))
    taskid = models.ForeignKey(Task, on_delete=models.SET(1))
    name = models.CharField(max_length=50)
    type = models.IntegerField(choices=TYPE)
    quantity = models.IntegerField()
    comment = models.CharField(max_length=200)


class Action(models.Model):
    TYPE_SELECT_LIMIT = 9
    CLOSE_N = 10
    PEND_N = 11
    CH_STATUS_N = 12
    CH_ASSIGN_N = 13
    CH_PRIORITY_N = 14
    CH_LABEL_N = 15
    REOPEN_N = 16

    TYPE = ((1, 'Виконання'),
            (2, 'Інформація'),
            (3, 'Повторна подія'),
            (4, 'Запит на закриття'),
            (5, 'Заміна обладнання'),
            (6, 'Запит дії/забезпечення'),
            (7, 'Встановлено підмінне обл.'),
            (8, 'Знято підмінне обл.'),
            (9, 'Передано в користування'),
            (10, 'Закриття завдання'),
            (11, 'Відтермінування'),
            (12, 'Зміна статусу'),
            (13, 'Зміна виконавця'),
            (14, 'Зміна пріоритету'),
            (15, 'Зміна мітки'),
            (16, 'Повторне відкриття')
            )

    taskid = models.ForeignKey(Task, on_delete=models.CASCADE)
    time = models.DateTimeField()
    type = models.IntegerField(choices=TYPE)
    by = models.ForeignKey(User, on_delete=models.SET(1))
    comment = models.CharField(max_length=250)
    opttime = models.DateTimeField()
    optvalue = models.IntegerField()


class Request(models.Model):
    TYPES = ((1, 'Запит дії'),
             (2, 'Запит інформації'),
             (3, 'Запит забезпечення'),
             (4, 'Особистий запит'),
             (5, 'Інше'),
             )

    standalone = models.BooleanField()
    taskid = models.IntegerField()
    type = models.IntegerField(choices=TYPES)
    by = models.ForeignKey(User, related_name='request_by', on_delete=models.SET(1))
    to = models.ForeignKey(User, related_name='request_to', on_delete=models.SET(1))
    description = models.CharField(max_length=240)
    reply = models.CharField(max_length=240)
    opendate = models.DateTimeField()
    closedate = models.DateTimeField()
    closed = models.BooleanField()
    private = models.BooleanField()
