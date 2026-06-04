from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.core.cache import cache
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # For employees trying to access admin pages, render a custom access denied page
            return render(request, 'helpdesk/access_denied.html', {
                'allowed_roles': allowed_roles,
                'current_role': request.user.role,
            })
        return _wrapped_view
    return decorator


