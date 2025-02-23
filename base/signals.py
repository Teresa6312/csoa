from django.db.models.signals import post_save, pre_save
from django.db import models
from django.dispatch import receiver
from .models import ModelDictionaryConfigModel, ModelDictionaryItemsConfigModel
from django.db.models.signals import post_migrate
from base.util import get_related_names_for_model, CustomJSONEncoder
import json
import logging
from django.utils import timezone

logger = logging.getLogger('django')

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
        if instance.json_form is not None:
            for item in instance.json_form.form_section_form_template.filter(is_active=True):
                for key in item.json_template.keys():
                    index = index + 1
                    new_item = ModelDictionaryItemsConfigModel.objects.create(
                                                                    dictionary=instance,
                                                                    backend_field_name= "section_data_%s__%s"% (item.index, key),
                                                                    add_fieldsets=False, 
                                                                    edit_fieldsets=False,
                                                                    fieldsets = False,
                                                                    field_label=item.json_template[key]['label'],
                                                                    index=index, 
                                                                    list_display = True if item.index == 0 and item.json_template[key]['input']!='list' else False
                                                                 )
            


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
#  for example, what to do if table removed, what to do if add new fields or delete existed fields (FK or not FK), something for the related models configed in ModelDictionaryConfigModel

@receiver(post_migrate)
def execute_after_migrate(sender, **kwargs):
    objects = ModelDictionaryConfigModel.objects.filter(is_active=True)
    # Update the 'updated_at' field for each object
    for obj in objects:
        logger.info(f"update ModelDictionaryConfigModel:'{obj}' after migrate")
        obj.updated_at = timezone.now()
        obj.save()