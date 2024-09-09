from django.db.models.signals import post_save, post_delete, pre_save
from django.db import models
from django.dispatch import receiver
from .models import DictionaryItemModel, ModelDictionaryConfigModel, ModelDictionaryItemsConfigModel, DictionaryModel
from .redis import create_redis_key_queryset, create_redis_key_json, delete_redis_key
from django.db.models.signals import post_migrate
from .util import get_related_model_class, get_related_names_for_model, CustomJSONEncoder
import json
import logging
logger = logging.getLogger('django')

@receiver(post_save, sender=DictionaryItemModel)
def dictionary_item_saved(sender, instance, created, **kwargs):
    items = DictionaryItemModel.objects.filter(dictionary = instance.dictionary)
    create_redis_key_queryset('dict_'+instance.dictionary.code, items)
    items = DictionaryItemModel.objects.filter(dictionary = instance.dictionary, is_active=True)
    create_redis_key_queryset('dict_'+instance.dictionary.code+'_active', items)

@receiver(post_delete, sender=DictionaryItemModel)
def dictionary_item_deleted(sender, instance, **kwargs):
    items = DictionaryItemModel.objects.filter(dictionary = instance.dictionary)
    create_redis_key_queryset('dict_'+instance.dictionary.code, items)
    items = DictionaryItemModel.objects.filter(dictionary = instance.dictionary, is_active=True)
    create_redis_key_queryset('dict_'+instance.dictionary.code+'_active', items)

@receiver(post_delete, sender=DictionaryModel)
def dictionary_deleted(sender, instance, **kwargs):
    delete_redis_key('dict_'+instance.code)
    delete_redis_key('dict_'+instance.code+'_active')

@receiver(pre_save, sender=ModelDictionaryConfigModel)
def model_dictionary_save(sender, instance, **kwargs):
    class_name = instance.get_model_class()
    fk_fields = []
    fk_multi_fields = []
    for field in class_name._meta.get_fields():
        if isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField):
            related_name = field.remote_field.related_name
            fk_fields.append({
                "model": field.related_model._meta.label ,
                "field_name": field.name,
                "related_name": related_name if related_name is not None else f"{class_name._meta.model_name}_set",
                "label": field.verbose_name
                })
        elif isinstance(field, models.ManyToManyField):
            related_name = field.remote_field.related_name
            fk_multi_fields.append({
                "model": field.related_model._meta.label,
                "field_name": field.name,
                "related_name": related_name if related_name is not None else f"{class_name._meta.model_name}_set",
                "label": field.verbose_name
                })
    fk, rnf = get_related_names_for_model(class_name)
    fk_fields = fk_fields + fk
    fk_multi_fields = fk_multi_fields + rnf
    if len(fk_fields) > 0:
        instance.fk_fields =  json.loads(json.dumps(fk_fields, cls=CustomJSONEncoder))
    if len(fk_multi_fields) > 0:
        instance.fk_multi_fields = json.loads(json.dumps(fk_multi_fields, cls=CustomJSONEncoder))
    instance.pk_field_name = class_name._meta.pk.name
    instance.model_label = class_name._meta.verbose_name.title() if instance.model_label == 'model' else instance.model_label

@receiver(post_save, sender=ModelDictionaryConfigModel)
def model_dictionary_saved(sender, instance, created, **kwargs):
    class_name = instance.get_model_class()
    if created:
        index = 0
        for field in class_name._meta.fields:
            list_display = True
            fieldsets = True
            if isinstance(field, models.ForeignKey) or isinstance(field, models.ManyToManyField) or isinstance(field, models.OneToOneField):
                list_display = False
                fieldsets = False
            new_item = ModelDictionaryItemsConfigModel.objects.create(dictionary=instance,
                                                            backend_field_name=field.name, add_fieldsets=True, 
                                                            edit_fieldsets=True, fieldsets = fieldsets,
                                                            field_label=field.verbose_name.title(),
                                                            index=index if field.name!='is_active' else 99, list_display = list_display)
            new_item.save()
            index = index + 1
    create_redis_key_json(f"model_dict__{instance.code}", instance.get_field_lists())

# may use the following to get all the related fields
# @receiver(pre_save, sender=ModelDictionaryConfigModel)
# def model_dictionary_create(sender, instance, **kwargs):
#     his = instance.history.all()
#     # make sure only apply when create
#     if len(his) == 0:
#         class_name = instance.get_model_class()
#         fk_fields = []
#         related_name_fields = []
#         for field in class_name._meta.fields:
#             print(field)
#             if isinstance(field, models.ForeignKey) or isinstance(field, models.ManyToManyField):
#                 print(field)
#                 fk_fields.append(field.name)
#         if len(fk_fields) > 0:
#             instance.fk_fields = ','.join(fk_fields)
#         related_name_fields = get_related_names_for_model(class_name)
#         if len(related_name_fields) > 0:
#             instance.related_name_fields = ','.join(related_name_fields)
#         instance.pk_field_name = class_name._meta.pk.name
#         instance.model_label = class_name._meta.label.title()

# @receiver(post_save, sender=ModelDictionaryConfigModel)
# def model_dictionary_saved(sender, instance, created, **kwargs):
#     class_name = instance.get_model_class()
#     index = 0
#     if created:
#         for field in class_name._meta.fields:
#             list_display = True
#             if isinstance(field, models.ForeignKey) or isinstance(field, models.ManyToManyField):
#                 list_display = False
#             new_item = ModelDictionaryItemsConfigModel.objects.create(dictionary=instance,
#                                                             backend_field_name=field.name, 
#                                                             field_label=field.verbose_name.title(),
#                                                             index=index, list_display = list_display)
#             new_item.save()
#             index = index + 1
#         if instance.fk_fields is not None:
#             fk_fields = instance.fk_fields.split(',')
#             for fk in fk_fields:
#                 fk_field = class_name._meta.get_field(fk)
#                 related_model = fk_field.related_model
#                 for related_field in related_model._meta.fields:
#                     new_item = ModelDictionaryItemsConfigModel.objects.create(dictionary=instance,
#                                                                    backend_field_name=f"{fk}__{related_field.name}", 
#                                                                    field_label=f"{fk_field.verbose_name}  {related_field.verbose_name}".title(),
#                                                                    index=index, list_display = False)
#                     new_item.save()
#                     index = index + 1
#             related_name_fields = instance.related_name_fields.split(',')
#             for fk in related_name_fields:
#                 related_model_class = get_related_model_class(class_name, fk)
#                 if related_model_class is not None:
#                     # fk_field = related_model_class._meta.get_field(fk)
#                     # related_model = fk_field.related_model
#                     for related_field in related_model_class._meta.fields:
#                         new_item = ModelDictionaryItemsConfigModel.objects.create(dictionary=instance,
#                                                                     backend_field_name=f"{fk}__{related_field.name}", 
#                                                                     field_label=f"{fk_field.verbose_name}  {related_field.verbose_name}".title(),
#                                                                     index=index, list_display = False, )
#                         new_item.save()
#                         index = index + 1

# #  if there is some data table structure change, need to check if the model configed in ModelDictionaryConfigModel, if it is configed, need to do some handling
# #  for example, what to do if table removed, what to do if add new fields or delete existed fields (FK or not FK), something for the related models configed in ModelDictionaryConfigModel
# @receiver(post_migrate)
# def execute_after_migrate(sender, **kwargs):
#     # Your custom logic here
#     print("Migrations have been applied!")
#     # For example, you could create default data, update model structure, etc.