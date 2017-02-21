# coding: utf8
import re
import locale
from operator import __and__
from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect
from .models import Object, Region, DeviceType, Device, Task, TaskLabel, UserEx, Action
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.db.models import Q
from datetime import datetime, timedelta
from lt_extend import check_access_mt, check_access_fn, paginator_indexed, check_access
# Create your views here.
ADMIN = UserEx.ADMIN
SUPERVISOR = UserEx.SUPERVISOR
OPERATOR = UserEx.OPERATOR
USER = UserEx.USER

locale.setlocale(locale.LC_TIME, 'uk_UA.UTF-8')


@check_access_fn(USER)
def index(request):
    user_obj = request.user
    date = datetime.now() - timedelta(days=1)
    task_list = Task.objects.filter(~Q(status=Task.CLOSE_N), Q(assignedto=user_obj),
                                    Q(priority=4) | Q(opened__gte=date)).order_by('-priority')
    if check_access(request, SUPERVISOR):
        task_clr_list = Task.objects.filter(Q(status=Task.CLOSE_PEND_N)).order_by('lastactivity')
    else:
        task_clr_list = False

    user_ex_obj = UserEx.objects.get(name=user_obj)
    context = {'tasks': task_list,
               'can_view_clr': user_ex_obj.has_access(SUPERVISOR),
               'clr_tasks': task_clr_list,
               'event_type': Task.EVENT_TYPE,
               'status': Task.STATUS}
    return render(request, 'tmsmain/home.html', context)


def user_login(request):
    if request.method == 'GET':
        return render(request, 'tmsmain/login.html')

    elif request.method == 'POST':
        userlogin = request.POST['user_login']
        userpassword = request.POST['user_password']
        if re.search('^[A-Za-z0-9]{3,}$', userlogin) and re.search('^[A-Za-z0-9]{3,}$', userpassword):
            auth_user = authenticate(username=userlogin, password=userpassword)
            if auth_user:
                if auth_user.is_active:
                    login(request, auth_user)
                    return HttpResponseRedirect(reverse('index'))
                else:
                    context = {'error_message': 'Профіль заблокований, звернітся до адміністратора!'}
                    return render(request, 'tmsmain/login.html', context)
        context = {'error_message': 'Логін/пароль невірний!'}
        return render(request, 'tmsmain/login.html', context)
    else:
        return HttpResponseRedirect(reverse('index'))


def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))


@check_access_fn(USER)
def objects(request, page_n):
    obj = Object.objects.order_by('-name')
    page, indexes = paginator_indexed(obj, 10, page_n)
    context = {'objects': page,
               'indexes': indexes}
    return render(request, 'tmsmain/objects.html', context)


@check_access_fn(USER)
def object_details(request, object_id):
    obj = Object.objects.get(pk=object_id)
    dev = Device.objects.filter(objectid=object_id, type__iscommunicator=False)
    comm = Device.objects.filter(objectid=object_id, type__iscommunicator=True)
    ch_type = DeviceType.CHANNEL_TYPE
    context = {'object': obj,
               'devices': dev,
               'communicators': comm,
               'ch_type': ch_type}
    return render(request, 'tmsmain/object_details.html', context)


@check_access_fn(OPERATOR)
def create_object(request):
    if request.method == 'GET':
        context = {'step': 1}
        return render(request, 'tmsmain/create_object.html', context)

    elif request.method == 'POST':
        if 'step_1' in request.POST:
            obj_number = request.POST['number'].upper()
            objects = Object.objects.filter(number=obj_number)
            if len(objects) > 0:
                context = {'objects':  objects,
                           'number_err': True,
                           'step': 1}
                return render(request, 'tmsmain/create_object.html', context)
            else:
                request.session['temp_data'] = {'number': obj_number}
                regions = Region.objects.order_by('pk')
                obj_types = Object.TYPES
                context = {'step': 2,
                           'number': obj_number,
                           'regions': regions,
                           'obj_types': obj_types}
                return render(request, 'tmsmain/create_object.html', context)

        elif 'step_2' in request.POST:
            obj_number = request.session['temp_data']['number']
            obj_name = request.POST['name']
            obj_type = request.POST['type']
            obj_region = request.POST['region']
            obj_address = request.POST['address']
            obj_contract = request.POST['contract'].upper()
            obj_active = True if 'active' in request.POST else False
            obj_comment = request.POST['comment']
            devices = DeviceType.objects.order_by('iscommunicator', 'pk')
            communicators = DeviceType.objects.order_by('-iscommunicator', 'pk')
            request.session['temp_data'] = {'number': obj_number,
                                            'name': obj_name,
                                            'type': obj_type,
                                            'region': obj_region,
                                            'address': obj_address,
                                            'contract': obj_contract,
                                            'active': obj_active,
                                            'comment': obj_comment}
            context = {'step': 3,
                       'number': obj_number,
                       'name': obj_name,
                       'devices': devices,
                       'communicators': communicators}
            return render(request, 'tmsmain/create_object.html', context)

        elif 'step_3' in request.POST or 'skip_step_3' in request.POST:
            temp_data = request.session['temp_data']
            obj_number = temp_data['number']
            objects = Object.objects.filter(number=obj_number)
            if len(objects) > 0:
                context = {'objects':  objects,
                           'number_err': True,
                           'step': 1}
                return render(request, 'tmsmain/create_object.html', context)

            else:
                obj_region = Region.objects.get(pk=temp_data['region'])
                new_obj = Object(number=obj_number, name=temp_data['name'], type=temp_data['type'],
                                 region=obj_region, address=temp_data['address'],
                                 contract=temp_data['contract'], active=temp_data['active'],
                                 comment=temp_data['comment'], deleted=False)
                new_obj.save()
            if 'step_3' in request.POST:
                dev_type = DeviceType.objects.get(pk=request.POST['dev_type'])
                dev_serial = request.POST['dev_serial']
                dev_rent = True if 'dev_rent' in request.POST else False
                dev_comment = request.POST['dev_comment']
                new_dev = Device(type=dev_type, serial=dev_serial, rent=dev_rent, comment=dev_comment,
                                 objectid=new_obj)
                new_dev.save()
                if 'comm_used' in request.POST:
                    comm_type = DeviceType.objects.get(pk=request.POST['comm_type'])
                    comm_serial = request.POST['comm_serial']
                    comm_rent = True if 'comm_rent' in request.POST else False
                    comm_comment = request.POST['comm_comment']
                    new_comm = Device(type=comm_type, serial=comm_serial, rent=comm_rent, comment=comm_comment,
                                      objectid=new_obj)
                    new_comm.save()
            return HttpResponseRedirect(reverse('tmsmain:objects', args=[1]))
        else:
            return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')


@check_access_fn(OPERATOR, optional_redirect='tmsmain:my_tasks')
def tasks(request, page_n=1):

    if 'tab' in request.GET:
        tab = request.GET.get('tab')
        if tab not in ('all_tsk', 'my_tsk'):
            tab = 'all_tsk'
    else:
        tab = 'all_tsk'

    if 'sort' in request.GET:
        sort = request.GET.get('sort')
        if sort == 'asc':
            sort_label = 'asc'
            sort = ''
        else:
            sort_label = 'desc'
            sort = '-'
    else:
        sort_label = 'desc'
        sort = '-'

    order_by_options = {'newest': ('opened', 'Новизною'),
                        'priority': ('priority', 'Пріоритетом'),
                        'type': ('eventtype', 'Типом'),
                        'status': ('status', 'Статусом')}
    if 'order_by' in request.GET:
        order_by = request.GET.get('order_by')
        if order_by in order_by_options.keys():
            order_by, order_by_label = order_by_options[order_by]
        else:
            order_by, order_by_label = order_by_options['newest']
    else:
        order_by, order_by_label = order_by_options['newest']

    filter_build = []
    if 'filter_priority' in request.GET:
        filter_priority = request.GET.get('filter_priority')
        if re.search('^[1-9]+$', filter_priority):
            filter_priority = int(filter_priority)
            if 1 <= filter_priority <= len(Task.PRIORITY):
                filter_build.append(Q(priority=filter_priority))
                filter_priority_label = Task.PRIORITY[filter_priority-1][1]
            else:
                filter_priority_label = 'Не задано'
        else:
            filter_priority_label = 'Не задано'
    else:
        filter_priority_label = 'Не задано'

    if 'filter_type' in request.GET:
        filter_type = request.GET.get('filter_type')
        if re.search('^[1-9]+$', filter_type):
            filter_type = int(filter_type)
            if 1 <= filter_type <= len(Task.EVENT_TYPE):
                filter_build.append(Q(eventtype=filter_type))
                filter_type_label = Task.EVENT_TYPE[filter_type-1][1]
            else:
                filter_type_label = 'Не задано'
        else:
            filter_type_label = 'Не задано'
    else:
        filter_type_label = 'Не задано'

    if 'filter_status' in request.GET:
        filter_status = request.GET.get('filter_status')
        if re.search('^[1-9]+$', filter_status):
            filter_status = int(filter_status)
            if 1 <= filter_status <= len(Task.STATUS):
                filter_build.append(Q(status=filter_status))
                filter_status_label = Task.STATUS[filter_status-1][1]
            else:
                filter_status_label = 'Не задано'
        else:
            filter_status_label = 'Не задано'
    else:
        filter_status_label = 'Не задано'

    if 'filter_assignee' in request.GET:
        filter_assignee = request.GET.get('filter_assignee')
        if re.search('^[1-9]+$', filter_assignee):
            try:
                filter_assignee = User.objects.get(pk=int(filter_assignee))
                filter_build.append(Q(assignedto=filter_assignee))
                filter_assignee_label = filter_assignee.username
            except User.DoesNotExist:
                filter_assignee_label = 'Не задано'
        else:
            filter_assignee_label = 'Не задано'
    else:
        filter_assignee_label = 'Не задано'

    if 'filter_label' in request.GET:
        filter_label = request.GET.get('filter_label')
        if re.search('^[1-9]+$', filter_label):
            try:
                filter_label = TaskLabel.objects.get(pk=int(filter_label))
                filter_build.append(Q(label=filter_label))
                filter_label_label = filter_label.name
            except User.DoesNotExist:
                filter_label_label = 'Не задано'
        else:
            filter_label_label = 'Не задано'
    else:
        filter_label_label = 'Не задано'

    if 'filter_objtype' in request.GET:
        filter_objtype = request.GET.get('filter_objtype')
        if re.search('^[1-9]+$', filter_objtype):
            filter_objtype = int(filter_objtype)
            if 1 <= filter_objtype <= len(Object.TYPES):
                filter_build.append(Q(objectid__type=filter_objtype))
                filter_objtype_label = Object.TYPES[filter_objtype-1][1]
            else:
                filter_objtype_label = 'Усі'
        else:
            filter_objtype_label = 'Усі'
    else:
        filter_objtype_label = 'Усі'

    if 'filter' in request.GET:
        filter_act = request.GET.get('filter')
        if filter_act == 'true':
            filter_act = True
            filter_build.append(~Q(status=Task.CLOSE_N))
        else:
            filter_build = [~Q(status=Task.CLOSE_N)]
            filter_act = False
    else:
        filter_build = [~Q(status=Task.CLOSE_N)]
        filter_act = False

    user_obj = request.user
    my_tsk_list = Task.objects.filter(~Q(status=Task.CLOSE_N), Q(assignedto=user_obj)).order_by('%s%s' % (sort, order_by))
    tsk_list = Task.objects.filter(reduce(__and__, filter_build)).order_by('%s%s' % (sort, order_by))

    tasks_pg, indexes = paginator_indexed(tsk_list, 10, page_n)
    my_tasks_pg, my_indexes = paginator_indexed(my_tsk_list, 10, page_n)
    context = {'tasks': tasks_pg,
               'my_tasks': my_tasks_pg,
               'tasks_count': len(tsk_list),
               'my_tasks_count': len(my_tsk_list),
               'indexes': indexes,
               'my_indexes': my_indexes,
               'order_by_label': order_by_label,
               'sort_label': sort_label,
               'tab': tab,
               'filter_act': filter_act,
               'filter_priority_label': filter_priority_label,
               'filter_type_label': filter_type_label,
               'filter_status_label': filter_status_label,
               'filter_assignee_label': filter_assignee_label,
               'filter_label_label': filter_label_label,
               'filter_objtype_label': filter_objtype_label,
               'users': User.objects.filter(is_active=True),
               'task_label': TaskLabel.objects.order_by('pk'),
               'priority': Task.PRIORITY,
               'event_type': Task.EVENT_TYPE,
               'status_select': Task.STATUS[:Task.STATUS_SELECT_LIMIT],
               'status': Task.STATUS,
               'object_types': Object.TYPES}
    return render(request, 'tmsmain/tasks.html', context)


class MyTasks(View):
    @check_access_mt(USER)
    def get(self, request, page_n=1):

        if 'sort' in request.GET:
            sort = request.GET.get('sort')
            if sort == 'asc':
                sort_label = 'asc'
                sort = ''
            else:
                sort_label = 'desc'
                sort = '-'
        else:
            sort_label = 'desc'
            sort = '-'

        order_by_options = {'newest': ('opened', 'Новизною'),
                            'priority': ('priority', 'Пріоритетом'),
                            'type': ('eventtype', 'Типом'),
                            'status': ('status', 'Статусом')}
        if 'order_by' in request.GET:
            order_by = request.GET.get('order_by')
            if order_by in order_by_options.keys():
                order_by, order_by_label = order_by_options[order_by]
            else:
                order_by, order_by_label = order_by_options['newest']
        else:
            order_by, order_by_label = order_by_options['newest']

        user_obj = request.user
        my_tsk_list = Task.objects.filter(~Q(status=Task.CLOSE_N), Q(assignedto=user_obj)).order_by('%s%s' % (sort, order_by))
        my_tasks_pg, my_indexes = paginator_indexed(my_tsk_list, 10, page_n)
        context = {'my_tasks': my_tasks_pg,
                   'my_tasks_count': len(my_tsk_list),
                   'my_indexes': my_indexes,
                   'order_by_label': order_by_label,
                   'sort_label': sort_label,
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS}
        return render(request, 'tmsmain/my_tasks.html', context)


class TasksArchive(View):
    @check_access_mt(OPERATOR)
    def get(self, request, page_n=1):

        if 'sort' in request.GET:
            sort = request.GET.get('sort')
            if sort == 'asc':
                sort_label = 'asc'
                sort = ''
            else:
                sort_label = 'desc'
                sort = '-'
        else:
            sort_label = 'desc'
            sort = '-'

        order_by_options = {'closed': ('closed', 'Датою закриття'),
                            'priority': ('priority', 'Пріоритетом'),
                            'type': ('eventtype', 'Типом'),
                            'status': ('status', 'Статусом')}
        if 'order_by' in request.GET:
            order_by = request.GET.get('order_by')
            if order_by in order_by_options.keys():
                order_by, order_by_label = order_by_options[order_by]
            else:
                order_by, order_by_label = order_by_options['closed']
        else:
            order_by, order_by_label = order_by_options['closed']

        filter_build = []
        if 'filter_priority' in request.GET:
            filter_priority = request.GET.get('filter_priority')
            if re.search('^[1-9]+$', filter_priority):
                filter_priority = int(filter_priority)
                if 1 <= filter_priority <= len(Task.PRIORITY):
                    filter_build.append(Q(priority=filter_priority))
                    filter_priority_label = Task.PRIORITY[filter_priority-1][1]
                else:
                    filter_priority_label = 'Не задано'
            else:
                filter_priority_label = 'Не задано'
        else:
            filter_priority_label = 'Не задано'

        if 'filter_type' in request.GET:
            filter_type = request.GET.get('filter_type')
            if re.search('^[1-9]+$', filter_type):
                filter_type = int(filter_type)
                if 1 <= filter_type <= len(Task.EVENT_TYPE):
                    filter_build.append(Q(eventtype=filter_type))
                    filter_type_label = Task.EVENT_TYPE[filter_type-1][1]
                else:
                    filter_type_label = 'Не задано'
            else:
                filter_type_label = 'Не задано'
        else:
            filter_type_label = 'Не задано'

        if 'filter_assignee' in request.GET:
            filter_assignee = request.GET.get('filter_assignee')
            if re.search('^[1-9]+$', filter_assignee):
                try:
                    filter_assignee = User.objects.get(pk=int(filter_assignee))
                    filter_build.append(Q(assignedto=filter_assignee))
                    filter_assignee_label = filter_assignee.username
                except User.DoesNotExist:
                    filter_assignee_label = 'Не задано'
            else:
                filter_assignee_label = 'Не задано'
        else:
            filter_assignee_label = 'Не задано'

        if 'filter_label' in request.GET:
            filter_label = request.GET.get('filter_label')
            if re.search('^[1-9]+$', filter_label):
                try:
                    filter_label = TaskLabel.objects.get(pk=int(filter_label))
                    filter_build.append(Q(label=filter_label))
                    filter_label_label = filter_label.name
                except User.DoesNotExist:
                    filter_label_label = 'Не задано'
            else:
                filter_label_label = 'Не задано'
        else:
            filter_label_label = 'Не задано'

        if 'filter' in request.GET:
            filter_act = request.GET.get('filter')
            if filter_act == 'true':
                filter_act = True
                filter_build.append(Q(status=Task.CLOSE_N))
            else:
                filter_build = [Q(status=Task.CLOSE_N)]
                filter_act = False
        else:
            filter_build = [Q(status=Task.CLOSE_N)]
            filter_act = False

        tsk_list = Task.objects.filter(reduce(__and__, filter_build)).order_by('%s%s' % (sort, order_by))
        tasks_pg, indexes = paginator_indexed(tsk_list, 10, page_n)
        context = {'tasks': tasks_pg,
                   'indexes': indexes,
                   'tasks_count': len(tsk_list),
                   'filter_act': filter_act,
                   'filter_priority_label': filter_priority_label,
                   'filter_type_label': filter_type_label,
                   'filter_assignee_label': filter_assignee_label,
                   'filter_label_label': filter_label_label,
                   'order_by_label': order_by_label,
                   'sort_label': sort_label,
                   'priority': Task.PRIORITY,
                   'users': User.objects.filter(is_active=True),
                   'task_label': TaskLabel.objects.order_by('pk'),
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS}
        return render(request, 'tmsmain/tasks_archive.html', context)


@check_access_fn(OPERATOR)
def create_task(request):
    if request.method == 'GET':
        context = {'step': 1}
        return render(request, 'tmsmain/create_task.html', context)

    elif request.method == 'POST':
        if 'step_1' in request.POST:
            obj_list = Object.objects.filter(number__icontains=request.POST['number'])[:30]
            context = {'step': 2,
                       'objects': obj_list}
            return render(request, 'tmsmain/create_task.html', context)

        elif 'step_2' in request.POST:
            obj_id = request.POST['object_id']
            request.session['temp_data'] = obj_id
            obj = Object.objects.get(pk=obj_id)
            labels = TaskLabel.objects.filter(deleted=False).order_by('pk')
            users = User.objects.filter(is_active=True).order_by('pk')
            context = {'step': 3,
                       'object': obj,
                       'event_types': Task.EVENT_TYPE,
                       'priority': Task.PRIORITY,
                       'labels': labels,
                       'users': users}
            return render(request, 'tmsmain/create_task.html', context)

        elif 'step_3' in request.POST:
            event_date = request.POST['event_date']
            event_time = request.POST['event_time']
            event_type = request.POST['event_type']
            description = request.POST['description']
            task_label = request.POST['label']
            task_priority = request.POST['priority']
            assigned_to = request.POST['assigned_to']
            if len(event_date) > 1:
                try:
                    event_date = datetime.strptime('{0} {1}'.format(event_date, event_time), '%d.%m.%Y %H.%M.%S')
                except ValueError:
                    obj = Object.objects.get(pk=request.session['temp_data'])
                    labels = TaskLabel.objects.filter(deleted=False).order_by('pk')
                    users = User.objects.filter(is_active=True).order_by('pk')
                    context = {'step': 3, 'object': obj, 'event_types': Task.EVENT_TYPE, 'priority': Task.PRIORITY,
                               'labels': labels, 'users': users, 'event_type': int(event_type), 'description': description,
                               'task_label': int(task_label), 'task_priority': int(task_priority),
                               'assigned_to': int(assigned_to), 'error_message': 'Невірно задана дата або час!'}
                    return render(request, 'tmsmain/create_task.html', context)
            else:
                event_date = datetime.now()
            create_date = datetime.now()
            obj = Object.objects.get(pk=request.session['temp_data'])
            u_assigned_to = User.objects.get(pk=assigned_to)
            task_lbl = TaskLabel.objects.get(pk=task_label)
            tsk = Task(objectid=obj, eventtype=event_type, eventtime=event_date, label=task_lbl,
                       description=description, creator=request.user, priority=task_priority, status=Task.ACTIVE_N,
                       assignedto=u_assigned_to, lastactivity=create_date, delaytill=create_date, closed=create_date,
                       opened=create_date)
            tsk.save()
            return HttpResponseRedirect(reverse('tmsmain:tasks'))
        else:
            return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')


class ViewTask(View):
    @check_access_mt(USER)
    def get(self, request, task_id):
        tsk_obj = Task.objects.get(pk=task_id)
        actions = Action.objects.filter(taskid=tsk_obj).order_by('time')
        request.session['return_adr'] = 'tmsmain:view_task'
        context = {'task': tsk_obj,
                   'actions': actions,
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS,
                   'action_type': Action.TYPE,
                   'double_controls': True if len(actions) >= 4 else False,
                   'task_closed': True if tsk_obj.status == Task.CLOSE_N else False}
        return render(request, 'tmsmain/view_task.html', context)

    @check_access_mt(USER)
    def post(self, request, task_id):
        if 'action' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_add_action', args=[task_id]) + '#add_action_bookmark')
        elif 'close' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_close', args=[task_id]) + '#close_bookmark')
        elif 'manage' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_manage', args=[task_id]))
        elif 'reopen' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_reopen', args=[task_id]) + '#reopen_bookmark')
        else:
            return HttpResponseRedirect('/')


class TaskAddAction(View):
    @check_access_mt(USER)
    def get(self, request, task_id):
        tsk_obj = Task.objects.get(pk=task_id)
        actions = Action.objects.filter(taskid=tsk_obj).order_by('time')
        context = {'task': tsk_obj,
                   'actions': actions[len(actions)-3:] if len(actions) > 3 else actions,
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS,
                   'action_type': Action.TYPE,
                   'action_types': Action.TYPE[:Action.TYPE_SELECT_LIMIT],
                   'step': 1}
        return render(request, 'tmsmain/task_add_action.html', context)

    @check_access_mt(USER)
    def post(self, request, task_id):
        if 'save' in request.POST:
            tsk_obj = Task.objects.get(pk=task_id)
            act_type = request.POST['action_type']
            act_description = request.POST['action_comment']
            act_time = datetime.now()
            tsk_obj.lastactivity = act_time
            tsk_obj.save()
            action_obj = Action(taskid=tsk_obj, time=act_time, type=act_type, by=request.user, comment=act_description,
                                opttime=act_time, optvalue=1)
            action_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:view_task', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


class TaskClose(View):
    @check_access_mt(SUPERVISOR)
    def get(self, request, task_id):
        tsk_obj = Task.objects.get(pk=task_id)
        actions = Action.objects.filter(taskid=tsk_obj).order_by('time')
        context = {'task': tsk_obj,
                   'actions': actions[len(actions)-3:] if len(actions) > 3 else actions,
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS,
                   'action_type': Action.TYPE}
        return render(request, 'tmsmain/task_close.html', context)

    @check_access_mt(SUPERVISOR)
    def post(self, request, task_id):
        if 'close' in request.POST:
            tsk_obj = Task.objects.get(pk=task_id)
            act_time = datetime.now()
            tsk_obj.status = Task.CLOSE_N
            tsk_obj.lastactivity = act_time
            tsk_obj.closed = act_time
            tsk_obj.save()
            act_description = u'Завдання виконано. Коментар: ' + request.POST['action_comment']
            action_obj = Action(taskid=tsk_obj, time=act_time, type=Action.CLOSE_N, by=request.user,
                                comment=act_description[:250], opttime=act_time, optvalue=1)
            action_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:view_task', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


class TaskReopen(View):
    @check_access_mt(OPERATOR)
    def get(self, request, task_id):
        tsk_obj = Task.objects.get(pk=task_id)
        users = User.objects.filter(is_active=True).order_by('pk')
        actions = Action.objects.filter(taskid=tsk_obj).order_by('time')
        context = {'task': tsk_obj,
                   'users': users,
                   'priority': Task.PRIORITY,
                   'actions': actions[len(actions)-3:] if len(actions) > 3 else actions,
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS,
                   'action_type': Action.TYPE}
        return render(request, 'tmsmain/task_reopen.html', context)

    @check_access_mt(OPERATOR)
    def post(self, request, task_id):
        if 'reopen' in request.POST:
            tsk_obj = Task.objects.get(pk=task_id)
            act_time = datetime.now()
            tsk_obj.status = Task.ACTIVE_N
            tsk_obj.lastactivity = act_time
            tsk_obj.assignedto = User.objects.get(pk=request.POST['assigned_to'])
            tsk_obj.priority = request.POST['priority']
            tsk_obj.save()
            act_description = u'Завдання відкрито повторно. Коментар: ' + request.POST['action_comment']
            action_obj = Action(taskid=tsk_obj, time=act_time, type=Action.REOPEN_N, by=request.user,
                                comment=act_description[:250], opttime=act_time, optvalue=1)
            action_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:view_task', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


class TaskManage(View):
    @check_access_mt(OPERATOR)
    def get(self, request, task_id):
        tsk_obj = Task.objects.get(pk=task_id)
        actions = Action.objects.filter(taskid=tsk_obj).order_by('time')
        context = {'task': tsk_obj,
                   'actions': actions[len(actions)-3:] if len(actions) > 3 else actions,
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS,
                   'priority': Task.PRIORITY,
                   'action_type': Action.TYPE}
        return render(request, 'tmsmain/task_manage.html', context)

    @check_access_mt(OPERATOR)
    def post(self, request, task_id):
        if 'change_label' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_change_label', args=[task_id]))
        elif 'change_assign' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_change_assign', args=[task_id]))
        elif 'change_status' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_change_status', args=[task_id]))
        elif 'change_priority' in request.POST:
            return HttpResponseRedirect(reverse('tmsmain:task_change_priority', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


class TaskChangeLabel(View):
    @check_access_mt(OPERATOR)
    def get(self, request, task_id):
        context = {'task': Task.objects.get(pk=task_id),
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS,
                   'labels': TaskLabel.objects.order_by('pk')}
        return render(request, 'tmsmain/task_change_label.html', context)

    @check_access_mt(OPERATOR)
    def post(self, request, task_id):
        if 'change_label_step2' in request.POST:
            tsk_obj = Task.objects.get(pk=task_id)
            label_obj = TaskLabel.objects.get(pk=request.POST['new_label'])
            act_time = datetime.now()
            tsk_obj.label = label_obj
            tsk_obj.lastactivity = act_time
            tsk_obj.save()
            act_description = u'Мітку змінено на "{0}"  Коментар: '.format(label_obj.name)\
                              + request.POST['action_comment']
            action_obj = Action(taskid=tsk_obj, time=act_time, type=Action.CH_LABEL_N, by=request.user,
                                comment=act_description[:250], opttime=act_time, optvalue=1)
            action_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:view_task', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


class TaskChangeAssign(View):
    @check_access_mt(OPERATOR)
    def get(self, request, task_id):
        context = {'task': Task.objects.get(pk=task_id),
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS,
                   'users': User.objects.filter(is_active=True).order_by('pk')}
        return render(request, 'tmsmain/task_change_assign.html', context)

    @check_access_mt(OPERATOR)
    def post(self, request, task_id):
        if 'change_assign_step2' in request.POST:
            tsk_obj = Task.objects.get(pk=task_id)
            user_obj = User.objects.get(pk=request.POST['new_user'])
            act_time = datetime.now()
            tsk_obj.assignedto = user_obj
            tsk_obj.lastactivity = act_time
            tsk_obj.save()
            act_description = u'Виконавця змінено на "{0}"  Коментар: '.format(user_obj.username)\
                              + request.POST['action_comment']
            action_obj = Action(taskid=tsk_obj, time=act_time, type=Action.CH_ASSIGN_N, by=request.user,
                                comment=act_description[:250], opttime=act_time, optvalue=1)
            action_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:view_task', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


class TaskChangeStatus(View):
    @check_access_mt(OPERATOR)
    def get(self, request, task_id):
        context = {'task': Task.objects.get(pk=task_id),
                   'event_type': Task.EVENT_TYPE,
                   'status': Task.STATUS[:Task.STATUS_SELECT_LIMIT],
                   'step': 1}
        return render(request, 'tmsmain/task_change_status.html', context)

    @check_access_mt(OPERATOR)
    def post(self, request, task_id):
        if 'change_status_step2' in request.POST:
            request.session['status'] = request.POST['new_status']
            context = {'task': Task.objects.get(pk=task_id),
                       'event_type': Task.EVENT_TYPE,
                       'status': Task.STATUS[:Task.STATUS_SELECT_LIMIT],
                       'step': 2,
                       'input_date': True if int(request.POST['new_status']) == Task.PEND_N else False,
                       'date_input_error': False,
                       'comment_pre': ''}
            return render(request, 'tmsmain/task_change_status.html', context)
        elif 'change_status_step3' in request.POST:
            new_status = int(request.session['status'])
            if new_status == Task.PEND_N:
                try:
                    pend_to = datetime.strptime('{0} 08.00.00'.format(request.POST['pend_to']), '%d.%m.%Y %H.%M.%S')
                except ValueError:
                    context = {'task': Task.objects.get(pk=task_id),
                               'event_type': Task.EVENT_TYPE,
                               'status': Task.STATUS[:Task.STATUS_SELECT_LIMIT],
                               'step': 2,
                               'input_date': True,
                               'date_input_error': True,
                               'comment_pre': request.POST['action_comment']}
                    return render(request, 'tmsmain/task_change_status.html', context)
            else:
                pend_to = datetime.now()
            tsk_obj = Task.objects.get(pk=task_id)
            act_time = datetime.now()
            tsk_obj.status = new_status
            tsk_obj.delaytill = pend_to
            tsk_obj.lastactivity = act_time
            tsk_obj.save()
            act_description = u'Статус змінено на "{0}{1}"  Коментар: '.format(Task.STATUS[new_status-1][1],
                              pend_to.strftime('%d.%b.%y') if new_status == Task.PEND_N else '')\
                              + request.POST['action_comment']
            action_obj = Action(taskid=tsk_obj, time=act_time, type=Action.CH_STATUS_N, by=request.user,
                                comment=act_description[:250], opttime=pend_to, optvalue=1)
            action_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:view_task', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


class TaskChangePriority(View):
    @check_access_mt(OPERATOR)
    def get(self, request, task_id):
        context = {'task': Task.objects.get(pk=task_id),
                   'event_type': Task.EVENT_TYPE,
                   'priority': Task.PRIORITY}
        return render(request, 'tmsmain/task_change_priority.html', context)

    @check_access_mt(OPERATOR)
    def post(self, request, task_id):
        if 'change_priority_step2' in request.POST:
            tsk_obj = Task.objects.get(pk=task_id)
            act_time = datetime.now()
            new_priority = int(request.POST['new_priority'])
            tsk_obj.priority = new_priority
            tsk_obj.lastactivity = act_time
            tsk_obj.save()
            act_description = u'Пріоритет змінено на "{0}"  Коментар: '.format(Task.PRIORITY[new_priority-1][1])\
                              + request.POST['action_comment']
            action_obj = Action(taskid=tsk_obj, time=act_time, type=Action.CH_PRIORITY_N, by=request.user,
                                comment=act_description[:250], opttime=act_time, optvalue=1)
            action_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:view_task', args=[task_id]))
        else:
            return HttpResponseRedirect('/')


@check_access_fn(ADMIN)
def devices(request):
    dev = Device.objects.order_by('pk')
    ch_types = DeviceType.CHANNEL_TYPE
    context = {'devices': dev,
               'ch_type': ch_types}
    return render(request, 'tmsmain/devices.html', context)


@check_access_fn(ADMIN)
def admin_tools(request):
    return render(request, 'tmsmain/admin_tools.html')


@check_access_fn(ADMIN)
def regions(request):
    reg_list = Region.objects.order_by('pk')
    context = {'reg_list': reg_list}
    return render(request, 'tmsmain/regions.html', context)


@check_access_fn(ADMIN)
def add_region(request):
    if request.method == 'GET':
        reg_list = Region.objects.order_by('pk')
        context = {'reg_list': reg_list}
        return render(request, 'tmsmain/add_region.html', context)

    elif request.method == 'POST':
        reg_name = request.POST['region_name']
        new_reg = Region(name=reg_name)
        new_reg.save()
        return HttpResponseRedirect(reverse('tmsmain:regions'))
    else:
        return HttpResponseRedirect('/')


@check_access_fn(ADMIN)
def edit_region(request, region_id):
    if request.method == 'GET':
        region = Region.objects.get(pk=region_id)
        context = {'region': region}
        return render(request, 'tmsmain/edit_region.html', context)

    elif request.method == 'POST':
        if 'save' in request.POST:
            region = Region.objects.get(pk=region_id)
            region.name = request.POST['region_name']
            region.save()
            return HttpResponseRedirect(reverse('tmsmain:regions'))

        elif 'delete' in request.POST:
            if region_id == 1:
                return HttpResponseRedirect(reverse('tmsmain:regions'))
            else:
                region = Region.objects.get(pk=region_id)
                region.delete()
                return HttpResponseRedirect(reverse('tmsmain:regions'))
        else:
            return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')


@check_access_fn(ADMIN)
def device_types(request):
    device_list = DeviceType.objects.order_by('iscommunicator', 'pk')
    context = {'device_list': device_list,
               'ch_type': DeviceType.CHANNEL_TYPE}
    return render(request, 'tmsmain/device_types_list.html', context)


@check_access_fn(ADMIN)
def add_device_type(request):
    if request.method == 'GET':
        device_list = DeviceType.objects.order_by('pk')
        context = {'device_list': device_list,
                   'ch_type': DeviceType.CHANNEL_TYPE}
        return render(request, 'tmsmain/add_device_type.html', context)

    elif request.method == 'POST':
        device_type_name = request.POST['type_name']
        channel = request.POST['channel_type']
        print channel
        sim = True if 'dual_sim' in request.POST else False
        comm = True if 'comm' in request.POST else False
        new_dt = DeviceType(name=device_type_name, channeltype=channel, dualsim=sim, iscommunicator=comm, deleted=False)
        new_dt.save()
        return HttpResponseRedirect(reverse('tmsmain:device_types'))
    else:
        return HttpResponseRedirect('/')


@check_access_fn(ADMIN)
def task_labels(request):
    labels_list = TaskLabel.objects.order_by('pk')
    context = {'labels_list': labels_list}
    return render(request, 'tmsmain/task_labels.html', context)


@check_access_fn(ADMIN)
def add_task_label(request):
    if request.method == 'GET':
        labels_list = TaskLabel.objects.order_by('pk')
        context = {'labels_list': labels_list}
        return render(request, 'tmsmain/add_task_label.html', context)

    elif request.method == 'POST':
        label_name = request.POST['label_name']
        new_label = TaskLabel(name=label_name, deleted=False)
        new_label.save()
        return HttpResponseRedirect(reverse('tmsmain:task_labels'))
    else:
        return HttpResponseRedirect('/')


@check_access_fn(ADMIN)
def edit_task_label(request, label_id):
    if request.method == 'GET':
        label = TaskLabel.objects.get(pk=label_id)
        context = {'label': label}
        return render(request, 'tmsmain/edit_task_label.html', context)

    elif request.method == 'POST':
        if 'save' in request.POST:
            label = TaskLabel.objects.get(pk=label_id)
            label.name = request.POST['label_name']
            label.save()
            return HttpResponseRedirect(reverse('tmsmain:task_labels'))

        elif 'delete' in request.POST:
            if label_id == 1:
                return HttpResponseRedirect(reverse('tmsmain:task_labels'))
            else:
                label = TaskLabel.objects.get(pk=label_id)
                label.delete()
                return HttpResponseRedirect(reverse('tmsmain:task_labels'))
        else:
            return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')


class AddUser(View):
    def get(self, request):
        context = {'user_roles': UserEx.ROLES
                   }
        return render(request, 'tmsmain/add_user.html', context)

    def post(self, request):
        if 'save' in request.POST:
            username = request.POST['username']
            email = request.POST['email']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            user_role = int(request.POST['role'])
            canclose = True if 'canclose' in request.POST else False
            is_admin = True if 'is_admin' in request.POST else False
            context = {'user_roles': UserEx.ROLES,
                       'username': username,
                       'email': email,
                       'first_name': first_name,
                       'last_name': last_name,
                       'user_role': user_role,
                       'canclose': canclose,
                       'is_admin': is_admin
                       }

            if re.search('^[A-Za-z0-9]{3,}$', username):
                password_a = request.POST['password_a']
                password_b = request.POST['password_b']
                if password_a == password_b:
                    user_obj = User(username=username, first_name=first_name, last_name=last_name, email=email,
                                    is_superuser=is_admin, is_active=True)
                    user_obj.save()
                    user_obj.set_password(password_a)
                    user_obj.save()
                    userex_obj = UserEx(name=user_obj, role=user_role, canclose=canclose, fired=False)
                    userex_obj.save()
                else:
                    context['error_message'] = 'Паролі не співпадають, будь ласка введіть повторно!'
                    return render(request, 'tmsmain/add_user.html', context)
            else:
                context['error_message'] = 'Недопустимий логін!\n Логін повинен складатися з латинських літер'\
                                           ' та цифр, та бути не коротшим 3-х символів!'
                return render(request, 'tmsmain/add_user.html', context)

            return HttpResponseRedirect(reverse('tmsmain:users'))
        else:
            return HttpResponseRedirect('/')


@check_access_fn(ADMIN)
def users(request):
    users_list = User.objects.order_by('pk')
    context = {'users_list': users_list}
    return render(request, 'tmsmain/users_list.html', context)


@check_access_fn(ADMIN)
def edit_user(request, user_id):
    if request.method == 'GET':
        user_obj = User.objects.get(pk=user_id)
        userex_obj = UserEx.objects.get(name=user_obj)
        context = {'user': user_obj,
                   'userex': userex_obj,
                   'user_roles': UserEx.ROLES}
        return render(request, 'tmsmain/edit_user.html', context)

    elif request.method == 'POST':
        if 'save' in request.POST:
            user_obj = User.objects.get(pk=user_id)
            user_obj.username = request.POST['user_name']
            user_obj.first_name = request.POST['user_first_name']
            user_obj.last_name = request.POST['user_last_name']
            user_obj.email = request.POST['user_email']
            user_obj.is_superuser = True if 'user_admin' in request.POST else False
            user_obj.is_active = True if 'user_active' in request.POST else False
            user_obj.save()
            userex_obj = UserEx.objects.get(name=user_obj)
            userex_obj.role = request.POST['user_role']
            userex_obj.canclose = True if 'user_canclose' in request.POST else False
            userex_obj.save()
            return HttpResponseRedirect(reverse('tmsmain:users'))

        elif 'delete' in request.POST:
            if user_id == 1:
                return HttpResponseRedirect(reverse('tmsmain:users'))
            else:
                user_obj = User.objects.get(pk=user_id)
                user_obj.is_active = False
                user_obj.save()
                userex_obj = UserEx.objects.get(name=user_obj)
                userex_obj.fired = True
                userex_obj.save()
                return HttpResponseRedirect(reverse('tmsmain:users'))
        else:
            return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')


class ChangeUserPassword(View):
    @check_access_mt(ADMIN)
    def get(self, request, user_id):
        user_obj = User.objects.get(pk=user_id)
        userex_obj = UserEx.objects.get(name=user_obj)
        context = {'is_admin': True if userex_obj.role == ADMIN else False,
                   'user_obj': user_obj}
        return render(request, 'tmsmain/change_user_password.html', context)

    @check_access_mt(ADMIN)
    def post(self, request, user_id):
        if 'save' in request.POST:
            user_obj = User.objects.get(pk=user_id)
            userex_obj = UserEx.objects.get(name=user_obj)
            if userex_obj.role == ADMIN:
                old_password = request.POST['old_password']
                if re.search('^[A-Za-z0-9]{3,}$', old_password):
                    auth_user = authenticate(username=user_obj.username, password=old_password)
                    if not auth_user:
                        context = {'is_admin': True,
                                   'user_obj': user_obj,
                                   'error_message': 'Старий пароль введено невірно!'}
                        return render(request, 'tmsmain/change_user_password.html', context)
                else:
                    context = {'is_admin': True,
                               'user_obj': user_obj,
                               'error_message': 'Старий пароль введено невірно!'}
                    return render(request, 'tmsmain/change_user_password.html', context)
            new_pass_a = request.POST['new_password']
            new_pass_b = request.POST['confirm_new_password']
            if re.search('^[A-Za-z0-9]{6,}$', new_pass_a):
                if new_pass_a == new_pass_b:
                    user_obj.set_password(new_pass_a)
                    user_obj.save()
                    return HttpResponseRedirect(reverse('tmsmain:users'))
                else:
                    context = {'is_admin': True if userex_obj.role == ADMIN else False,
                               'user_obj': user_obj,
                               'error_message': 'Нові паролі не співпадають, будь ласка введіть повторно!'}
                    return render(request, 'tmsmain/change_user_password.html', context)
            else:
                context = {'is_admin': True if userex_obj.role == ADMIN else False,
                           'user_obj': user_obj,
                           'error_message': 'Пароль повинен бути не коротшим 6 знаків,'
                                            ' містити цифри і латинські літери!'}
                return render(request, 'tmsmain/change_user_password.html', context)
        else:
            return HttpResponseRedirect('/')


def error_page(request, error_n):
    return render(request, 'tmsmain/error.html', {'error_n': int(error_n)})


def login_required(request):
    return render(request, 'tmsmain/login_required.html')


def access_required(request):
    return render(request, 'tmsmain/access_required.html')
