# from userManagement.models import Department, Team, Company
# from .redis import create_redis_key, get_redis_connection, get_redis_data
# from celery import shared_task

# # @shared_task: This decorator is necessary here because create_redis_key is a Celery task that can be executed asynchronously or on a schedule.
# @shared_task
# def get_redis_data_test():
#     redis_data = get_redis_data('your_key_name')
#     print(redis_data)

# @shared_task
# def set_key():
#     redis_conn = get_redis_connection()
#     key = 'your_key_name'
#     value = 'your_value'
#     redis_conn.set(key,value)
#     return f"Key {key} set to {value}"

# @shared_task
# def daily_task_update_dict():
#     company_list = Company.objects.all()
#     create_redis_key.delay('company_list', list(company_list.values()))
#     # company_list_active = company_list.filter(is_active = 1)
#     # create_redis_key.delay('company_list_active', list(company_list_active.values()))

#     # department_list = Department.objects.all()
#     # create_redis_key.delay('company_list', list(department_list.values()))
#     # department_list_active = department_list.filter(is_active = 1)
#     # create_redis_key.delay('company_list_active', list(department_list_active.values()))

#     # team_list = Team.objects.all()
#     # create_redis_key.delay('company_list', list(team_list.values()))
#     # team_list_active = team_list.filter(is_active = 1)
#     # create_redis_key.delay('company_list_active', list(team_list_active.values()))

# from datetime import datetime

# @shared_task
# def add(x, y):
#     start_time = datetime.now()
#     print(f"Task started at: {start_time}")

#     # Task implementation here
#     result = x + y

#     end_time = datetime.now()
#     print(f"Task ended at: {end_time}")
#     return result


# @shared_task
# def mul(x, y):
#     return x * y


# @shared_task
# def xsum(numbers):
#     return sum(numbers)

# @shared_task
# def count_widgets():
#     return Company.objects.count()
