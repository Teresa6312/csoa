from django.db import models
import logging

logger = logging.getLogger("django")

def update_or_create(model, data):
    """
    Unified create/update handler with nested relationship management.

    Behavior:
    - Fields starting with "-" are used as unique filters
    - Non-prefixed fields are used for updates/creation
    - Automatically creates if no filters provided
    - Updates existing instance if filters match
    - Handles nested relationships recursively

    Args:
        model (Model): Django model class to operate on
        data (dict): Data payload with optional "-" prefixed filters

    Returns:
        tuple: (instance, created) where:
            - instance: Created/updated model instance
            - created: Boolean indicating if new record was created
    """
    try:
        # Separate filters and update data
        filters = {k[1:]: v for k, v in data.items() if k.startswith("-")}
        update_data = {k: v for k, v in data.items() if not k.startswith("-")}

        # Try to find existing instance
        instance = model.objects.get(**filters) if filters else None
        created = False

        if update_data == {}:
            return instance, created

        # Prepare creation/update data
        processed_data = {}
        m2m_relationships = {}
        child_relationships = {}
        model_fields = {f.name: f for f in model._meta.get_fields()}

        for key, value in update_data.items():
            field = model_fields.get(key)

            if not field:
                processed_data[key] = value
                continue

            # Handle related fields
            if isinstance(field, models.ForeignKey | models.OneToOneField):
                # Recursive update/create for related instance
                related_instance, _ = update_or_create(field.related_model, value)
                processed_data[key] = related_instance
            elif isinstance(field, models.ManyToManyField):
                # Store for post-save processing
                m2m_relationships[key] = value
            elif getattr(field, "related_model", None) is not None:
                # Handle child relationships
                if field.field is not None:
                    related_field = field.field.attname
                    child_relationships[key] = {
                        "model": field.related_model,
                        "field": related_field,
                        "data": value,
                    }
            elif getattr(field, "related_model", None) is None:
                processed_data[key] = value

        # Create or update main instance
        if instance:
            for attribute, value in processed_data.items():
                setattr(instance, attribute, value)
            instance.save()
        else:
            # Create new instance with combined data
            instance = model.objects.create(**processed_data)
            created = True

        # Process ManyToMany relationships
        for field_name, items in m2m_relationships.items():
            field = model_fields[field_name]
            manager = getattr(instance, field_name)
            related_instances = []

            for item in items:
                # Recursive processing of M2M items
                ri, _ = update_or_create(field.related_model, item)
                related_instances.append(ri)

            manager.set(related_instances)

        # Process child relationships
        for field_name, item in child_relationships.items():
            data = item["data"]
            model_class = item["model"]
            if isinstance(data, list):
                data = [dict(d, **{item["field"]: instance.pk}) for d in data]
                bluk_update_or_create(model_class, data)
            elif isinstance(data, dict):
                data[item["field"]] = instance.pk
                update_or_create(model_class, data)
            else:
                logger.error(
                    f"Invalid data type for child relationship {model_class}.{field_name}: {data}"
                )
                raise ValueError(
                    f"Invalid data type for child relationship {model_class}.{field_name}: {data}"
                )
        return instance, created
    except model.DoesNotExist:
        raise model.DoesNotExist(
            f"Instance not found for filters: {filters} in {model.__name__}"
        )
    except Exception as e:
        raise e

def bluk_update_or_create(model_class, data_list):
    """
    Bulk update or create handler for a list of data payloads.

    Args:
        model_class (Model): Django model class to operate on
        data_list (list): List of data payloads

    Returns:
        tuple: (instance_pks, created_count, updated_count) where:
            - instance_pks: List of primary keys of processed instances
            - created_count: Number of instances created
            - updated_count: Number of instances updated
    """
    instance_pks = []
    created_count = 0
    updated_count = 0
    for item in data_list:
        instance, created = update_or_create(model_class, item)
        if created:
            created_count += 1
        else:
            updated_count += 1
        if instance is not None:
            instance_pks.append(instance.pk)
    return instance_pks, created_count, updated_count  # Return values

def get_field_keyset(data, parent_key=None):
    """
    Recursively extract a set of field keys from nested data structures.

    Args:
        data (dict or list): The data structure to extract keys from.
        parent_key (str, optional): The parent key to prepend to nested keys.

    Returns:
        set: A set of field keys.
    """
    key_set = set()
    if isinstance(data, list):
# Iterate through list items
        for d in data:
            if isinstance(d, dict):
                key_set = key_set.union(get_field_keyset(d, parent_key))
    elif isinstance(data, dict):
# Iterate through dictionary items
        for field in data.keys():
            name = field.replace("-", "") if field.startswith("-") else field
            p_key = parent_key + "__" + name if parent_key is not None else name
            if isinstance(data[field], (list, dict)):
# Recursively process nested structures
                key_set = key_set.union(
                    get_field_keyset(
                        data[field],
                        p_key,
                    )
                )
            else:
# Add key to set
                if parent_key:
                    key_set.add(parent_key + "__" + name)
                else:
                    key_set.add(name)
    return key_set