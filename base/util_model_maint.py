from django.db import models


# def create_model_filters_with_unique_values(model, data):
#     """
#     Generates a dictionary of filters to uniquely identify a model instance based on the provided data.

#     The function prioritizes the model's primary key, then checks for fields marked as unique,
#     and finally considers unique constraints defined in the model's Meta class. Data keys starting
#     with a "-" (e.g., "-fieldname") are used to indicate fields that are part of unique constraints.

#     Args:
#         model (Model): Django model class to create filters for.
#         data (dict): Data containing field values, potentially with "-" prefixes for unique fields.

#     Returns:
#         dict: Filters to uniquely identify an instance, or None if no valid unique constraints are found.
#     """
#     # Check if primary key is present in data (highest priority)
#     pk = model._meta.pk.name
#     keys = data.keys()
#     if pk in keys:
#         return {pk: data[pk]}

#     # Check for unique fields (fields with unique=True) using "-" prefixed keys in data
#     unique_fields = model.get_unique_fields()
#     filters = {}
#     # Extract field names by removing "-" prefix from keys that start with "-"
#     field_keys = [key.replace("-", "") for key in keys if key.startswith("-")]
#     for key in field_keys:
#         if key in model.unique_fields:
#             # Use the original "-field" key to get the value from data
#             filters[key] = data["-%s" % key]
#     if filters != {}:
#         return filters

#     # Check for composite unique constraints (unique_together in Meta)
#     unique_constraints = model.get_unique_constraints()
#     for constraint in unique_constraints:
#         # Ensure all fields in the constraint are present in the data
#         if all(field in field_keys for field in constraint):
#             # Build a filter for each field in the constraint
#             filters.update({field: data["-%s" % field] for field in constraint})
#             return filters
#     return None  # No valid unique constraints found


# def update_model_instance(model, data):
#     """
#     Updates an existing model instance and its relationships using provided data.

#     Mirrors `create_model_instance` patterns with:
#     - "+field" keys create new related instances
#     - Direct field names update existing relationships recursively
#     - ManyToMany relationships handled post-update

#     Args:
#         model (Model): Django model class to update
#         data (dict): Update data with same key conventions as create_model_instance

#     Returns:
#         int: Number of updated rows (1 if successful, 0 if failed)
#     """
#     # Get filters to find target instance
#     filters = create_model_filters_with_unique_values(model, data)
#     if not filters:
#         return 0  # No valid identifier found

#     try:
#         instance = model.objects.get(**filters)
#     except model.DoesNotExist:
#         return 0  # Instance not found

#     update_data = {}
#     m2m_relationships = {}

#     # Process standard fields and relationships
#     for key, value in data.items():
#         # Handle related object creation
#         if key.startswith("+"):
#             field_name = key[1:]
#             try:
#                 field = model._meta.get_field(field_name)
#             except FieldDoesNotExist:
#                 continue

#             if isinstance(field, (models.ForeignKey, models.OneToOneField)):
#                 # Create new related instance using existing pattern
#                 update_data[field_name] = create_model_instance(
#                     field.related_model, value
#                 )
#             continue

#         # Handle ManyToMany separately
#         try:
#             field = model._meta.get_field(key)
#             if isinstance(field, models.ManyToManyField):
#                 m2m_relationships[key] = value
#                 continue
#         except FieldDoesNotExist:
#             pass

#         # Handle existing relationships
#         try:
#             field = model._meta.get_field(key)
#             if isinstance(field, (models.ForeignKey, models.OneToOneField)):
#                 # Recursive update of related instance
#                 related_filters = create_model_filters_with_unique_values(
#                     field.related_model, value
#                 )
#                 if not related_filters:
#                     continue

#                 # Get and update related instance
#                 related_instance = field.related_model.objects.get(**related_filters)
#                 update_count = update_model_instance(field.related_model, value)
#                 if update_count == 1:
#                     update_data[key] = related_instance
#         except (FieldDoesNotExist, ObjectDoesNotExist):
#             pass

#         # Direct field update
#         update_data[key] = value

#     # Perform core update
#     update_count = model.objects.filter(pk=instance.pk).update(**update_data)

#     # Refresh instance for M2M handling
#     instance.refresh_from_db()

#     # Process ManyToMany relationships
#     for field_name, items in m2m_relationships.items():
#         field = model._meta.get_field(field_name)
#         manager = getattr(instance, field_name)
#         new_instances = []

#         for item in items:
#             if isinstance(item, dict):
#                 # Create/update based on data structure
#                 if any(k.startswith("-") for k in item.keys()):
#                     # Update existing instance
#                     related_instance = field.related_model.objects.get(
#                         **create_model_filters_with_unique_values(
#                             field.related_model, item
#                         )
#                     )
#                     update_model_instance(field.related_model, item)
#                     new_instances.append(related_instance)
#                 else:
#                     # Create new instance
#                     new_instances.append(
#                         create_model_instance(field.related_model, item)
#                     )
#             else:
#                 # Assume ID or direct instance
#                 new_instances.append(item)

#         manager.set(new_instances)

#     return update_count


# def create_model_instance(model, data):
#     """
#     Creates a new model instance with nested relationship handling using provided data.

#     Handles ForeignKey and OneToOneField relationships recursively. Data keys starting
#     with "+" (e.g., "+fieldname") indicate that a new related instance should be created.
#     Regular field names are used to reference existing related instances via unique identifiers.

#     Args:
#         model (Model): Django model class to create
#         data (dict): Data for instance creation. Keys may include:
#             - "fieldname": Value for direct fields or filters to find existing related instances
#             - "+fieldname": Data to create new related instances

#     Returns:
#         Model: The created instance

#     Raises:
#         ValueError: If referenced related instances can't be found
#         ObjectDoesNotExist: If unique filters don't match existing instances
#     """
#     creation_data = {}
#     model_fields = {field.name: field for field in model._meta.get_fields()}

#     for key, value in data.items():
#         # Handle related object creation first
#         if key.startswith("+"):
#             field_name = key[1:]  # Remove '+' prefix
#             if field_name not in model_fields:
#                 continue  # Ignore non-existent fields
#             field = model_fields[field_name]
#             if isinstance(field, (models.ForeignKey, models.OneToOneField)):
#                 # Recursively create nested related instance
#                 creation_data[field_name] = create_model_instance(
#                     field.related_model, value
#                 )
#             continue
#         if key.startswith("~"):
#             field_name = key[1:]  # Remove '~' prefix
#             if field_name not in model_fields:
#                 continue  # Ignore non-existent fields
#             field = model_fields[field_name]
#             if isinstance(
#                 field, (models.ForeignKey, models.OneToOneField)
#             ) and isinstance(value, dict):
#                 # found related instance
#                 creation_data[field_name] = field.related_model.objects.get(**value)
#             continue
#         # Handle existing relationship references
#         elif key in model_fields and isinstance(
#             model_fields[key], (models.ForeignKey, models.OneToOneField)
#         ):
#             field = model_fields[key]
#             # Find existing related instance using unique filters
#             filters = create_model_filters_with_unique_values(
#                 field.related_model, value
#             )
#             if not filters:
#                 raise ValueError(f"No valid unique identifier provided for {key}")
#             try:
#                 creation_data[key] = field.related_model.objects.get(**filters)
#             except field.related_model.DoesNotExist:
#                 raise ValueError(f"Related {key} instance not found")
#             continue
#         # Ignore non-existent fields or ManyToMany relationships for now
#         elif key not in model_fields or isinstance(
#             model_fields[key], models.ManyToManyField
#         ):
#             continue
#         # Direct field assignment
#         else:
#             creation_data[key] = value  # what if manyToManyField? or oneToMany?

#     # Handle ManyToMany relationships after main instance creation
#     m2m_relationships = {}
#     for field in model._meta.many_to_many:
#         if field.name in data:
#             m2m_relationships[field.name] = data[field.name]

#     # Create main instance
#     instance = model.objects.create(**creation_data)

#     # Process ManyToMany relationships
#     for field_name, relationship_data in m2m_relationships.items():
#         field = model_fields[field_name]
#         related_instances = []

#         for item in relationship_data:
#             if isinstance(item, dict):
#                 # Create new related instances for M2M
#                 related_instance = create_model_instance(field.related_model, item)
#                 related_instances.append(related_instance)
#             else:
#                 # Use existing instances
#                 item_instance = field.related_model.objects.get(pk=item)
#                 if item_instance:
#                     related_instances.append(item_instance)
#                 else:
#                     raise ValueError(
#                         f"Related instance not found for FIELD: {field_name} with PK: {item}"
#                     )
#         getattr(instance, field_name).set(related_instances)

#     return instance
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
            instance.update(**processed_data)
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
