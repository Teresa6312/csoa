
from functools import wraps
from django.core.cache import cache
import inspect
import logging

logger = logging.getLogger('django')

def global_cache_decorator(cache_key, timeout=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            func_module = inspect.getmodule(func)
            logger.debug(f'{func_module.__name__}.{func_name}')
            filter = ''
            for key in kwargs.keys():
                if inspect.isclass(kwargs.get(key)):
                    filter = f"{filter}:{kwargs.get(key)._meta.label}"
                else:
                    filter = f"{filter}:{kwargs.get(key)}"
            for key in args:
                if inspect.isclass(key):
                    filter = f"{filter}:{key._meta.label}"
                else:
                    filter = f"{filter}:{key}"
            data = cache.get(f"{cache_key}[{filter}]") if filter != '' else cache.get(cache_key)
            if data is None:
                data = func(*args, **kwargs)
                key = f"{cache_key}[{filter}]" if filter != '' else cache_key
                cache.set(key, data, timeout)
            return data
        return wrapper
    return decorator

def global_class_cache_decorator(cache_key, timeout=3600):
    def decorator(func):
        @classmethod
        @wraps(func)
        def wrapper(cls, *args, **kwargs):  # cls will be passed from @classmethod
            func_name = func.__name__
            func_module = inspect.getmodule(func)
            logger.debug(f'{func_module.__name__}.{func_name}')
            filter = ''
            for key in kwargs.keys():
                if inspect.isclass(kwargs.get(key)):
                    filter = f"{filter}:{kwargs.get(key)._meta.label}"
                else:
                    filter = f"{filter}:{kwargs.get(key)}"
            for key in args:
                if inspect.isclass(key):
                    filter = f"{filter}:{key._meta.label}"
                else:
                    filter = f"{filter}:{key}"
            # Use a cache key, with class name to ensure uniqueness if needed
            data = cache.get(f"{cache_key}[{filter}]") if filter != '' else cache.get(cache_key)
            if data is None:
                data = func(cls, *args, **kwargs)  # Call the class method
                key = f"{cache_key}[{filter}]" if filter != '' else cache_key
                cache.set(key, data, timeout)
            return data
        return wrapper
    return decorator

def global_instance_cache_decorator(cache_key, timeout=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(record, *args, **kwargs):  # cls will be passed from @classmethod
            func_name = func.__name__
            func_module = inspect.getmodule(func)
            logger.debug(f'{func_module.__name__}.{func_name}')
            filter = record.pk
            for key in kwargs.keys():
                if inspect.isclass(kwargs.get(key)):
                    filter = f"{filter}:{kwargs.get(key)._meta.label}"
                else:
                    filter = f"{filter}:{kwargs.get(key)}"
            for key in args:
                if inspect.isclass(key):
                    filter = f"{filter}:{key._meta.label}"
                else:
                    filter = f"{filter}:{key}"
            # Use a cache key, with class name to ensure uniqueness if needed
            data = cache.get(f"{cache_key}[{filter}]")
            if data is None:
                data = func(record, *args, **kwargs)  # Call the instance method from model
                key = f"{cache_key}[{filter}]"
                cache.set(f"{cache_key}[{filter}]", data, timeout)
            return data
        return wrapper
    return decorator

# def global_cache_decorator(cache_key, timeout=300):
#     def decorator(func):
#         @classmethod
#         @wraps(func)
#         def cls_method(cls, *args, **kwargs):  # cls will be the class itself
#             # Use a cache key to ensure uniqueness
#             data = cache.get(cache_key)
#             if data is None:
#                 data = func(cls, *args, **kwargs)  # Call the original function
#                 cache.set(cache_key, data, timeout)
#             return data
#         return cls_method
#     return decorator