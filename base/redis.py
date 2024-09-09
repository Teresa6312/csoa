import redis
from django.conf import settings
from celery import shared_task
import json
from .util import CustomJSONEncoder

def get_redis_connection():
    return redis.StrictRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB
    )

def get_redis_data(key):
    redis_conn = get_redis_connection()
    redis_data = redis_conn.get(key)
    if redis_data:
        redis_data = redis_data.decode('utf-8')  # Decode bytes to string if necessary
    return redis_data

# @shared_task: This decorator is necessary here because create_redis_key is a Celery task that can be executed asynchronously or on a schedule. 
# @shared_task
def create_redis_key(key, value, ex=None):
    redis_conn = get_redis_connection()
    if ex is not None:
        ex = ex * 60 # ex should be count in minutes
    redis_conn.set(key, value, ex=ex)
    return f"Key {key} set to {value} with expiration {ex} minutes"

def create_redis_key_json(key, value, ex=None):
    redis_conn = get_redis_connection()
    if ex is not None:
        ex = ex * 60 # ex should be count in minutes
    redis_conn.set(key, json.dumps(value, cls=CustomJSONEncoder), ex=ex)
    return f"Key {key} set to {value} with expiration {ex} minutes"

def create_redis_key_queryset(key, value, ex=None):
    redis_conn = get_redis_connection()
    if ex is not None:
        ex = ex * 60 # ex should be count in minutes
    redis_conn.set(key, json.dumps(list(value.values()), cls=CustomJSONEncoder), ex=ex)
    return f"Key {key} set to {value} with expiration {ex} minutes"

def get_redis_data_json(key):
    redis_conn = get_redis_connection()
    redis_data = redis_conn.get(key)
    if redis_data:
        redis_data = redis_data.decode('utf-8')  # Decode bytes to string if necessary
        redis_data = json.loads(redis_data)
    return redis_data

def delete_redis_key(key):
    redis_conn = get_redis_connection()
    redis_conn.delete(key)

# from django.core.cache import cache

# def get_data():
#     data = cache.get('my_data')
#     if not data:
#         # 数据不在缓存中，从数据库或其他地方获取数据
#         data = MyModel.objects.all()
#         # 将数据缓存 5 分钟
#         cache.set('my_data', data, 60 * 5)
#     return data
# {% load cache %}

# {% cache 900 some_cache_key %}
#     <div>
#         <!-- 一些需要缓存的模板代码 -->
#     </div>
# {% endcache %}


# from django.core.cache import cache
# from django.db import models

# class MyModel(models.Model):
#     name = models.CharField(max_length=100)

# def get_my_model_data():
#     cache_key = 'my_model_data'
#     data = cache.get(cache_key)
#     if not data:
#         data = MyModel.objects.all()
#         cache.set(cache_key, data, 60 * 10)  # 缓存 10 分钟
#     return data
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.core.cache import cache
# from .models import MyModel

# @receiver(post_save, sender=MyModel)
# @receiver(post_delete, sender=MyModel)
# def clear_cache(sender, **kwargs):
#     cache.delete('my_model_data')

# 你可以将 cache_page 和 cache_control 结合使用来实现更复杂的缓存策略。例如，缓存页面但确保每个用户的响应是独立缓存的：

# @cache_page(60 * 15)  # 缓存 15 分钟
# @cache_control(private=True, max_age=900)  # 响应在客户端缓存 15 分钟
# def user_dashboard(request):
#     return HttpResponse(f"User dashboard for {request.user.username}")
# 禁止缓存
# 有时你可能希望确保响应不会被缓存，可以使用 no_store 参数：

# @cache_control(no_store=True)
# def sensitive_view(request):
#     return HttpResponse("This response should not be cached anywhere.")

# @shared_task
# def create_redis_key(key, value, ex=None, override=True):
#     redis_conn = get_redis_connection()
    
#     if override:
#         redis_conn.set(key, value, ex=ex)  # Set the key with an expiration time
#         return f"Key {key} set to {value} with expiration {ex} seconds"
#     else:
#         result = redis_conn.setnx(key, value)  # Set the key only if it does not exist
#         if result:
#             if ex:
#                 redis_conn.expire(key, ex)  # Set expiration if key was newly created
#             return f"Key {key} set to {value} with expiration {ex} seconds"
#         else:
#             return f"Key {key} already exists and was not overwritten"
 
