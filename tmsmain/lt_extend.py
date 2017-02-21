from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from models import UserEx
import re


def check_access_fn(role_required, optional_redirect=None):
    def decorator(func):
        def inner(request, *args, **kwargs):
            if request.user.is_authenticated():
                userex = UserEx.objects.get(name=request.user)
                if userex.has_access(role_required):
                    return func(request, *args, **kwargs)
                else:
                    if optional_redirect is not None:
                        return HttpResponseRedirect(reverse(optional_redirect))
                    else:
                        return HttpResponseRedirect(reverse('tmsmain:access_required'))
            else:
                return HttpResponseRedirect(reverse('tmsmain:login_required'))
        return inner
    return decorator


def check_access_mt(role_required,  optional_redirect=None):
    def decorator(func):
        def inner(self, request, *args, **kwargs):
            if request.user.is_authenticated():
                userex = UserEx.objects.get(name=request.user)
                if userex.has_access(role_required):
                    return func(self, request, *args, **kwargs)
                else:
                    if optional_redirect is not None:
                        return HttpResponseRedirect(reverse(optional_redirect))
                    else:
                        return HttpResponseRedirect(reverse('tmsmain:access_required'))
            else:
                return HttpResponseRedirect(reverse('tmsmain:login_required'))
        return inner
    return decorator


def check_access(request, role_required):
    if request.user.is_authenticated():
        user_ex = UserEx.objects.get(name=request.user)
        if user_ex.has_access(role_required):
            return True
    return False


def paginator_indexed(obj, max_on_page, page_n):
    page_n_int = int(page_n)
    paginator_obj = Paginator(obj, max_on_page)
    if page_n_int > paginator_obj.num_pages:
        page_n_int = paginator_obj.num_pages
    if page_n_int <= 0:
        page_n_int = 1
    page_obj = paginator_obj.page(page_n_int)
    prev = False if page_n_int == 1 else page_n_int-1
    next = page_n_int+1 if page_obj.has_next() else False
    if paginator_obj.num_pages <= 8:
        center = range(1, paginator_obj.num_pages+1)
        first = False
        last = False
    else:
        center_l = 1 if page_n_int <= 4 else page_n_int-3
        center_r = paginator_obj.num_pages if paginator_obj.num_pages-3 <= page_n_int else page_n_int+3
        center = range(center_l, center_r+1)
        first = 1 if center_l > 1 else False
        last = paginator_obj.num_pages if center_r < paginator_obj.num_pages else False
    indexes = {'prev': prev,
               'next': next,
               'center': center,
               'first': first,
               'last': last,
               'current': page_n_int,
               'double_controls': True if len(page_obj) > 4 else False}
    return page_obj, indexes
