def generate_json_schema(field_definitions):
    """Converts a field definitions structure into a JSON Schema."""
    properties = {}
    required = []

    for field_name, config in field_definitions.items():
        field_type = config['input']
        field_schema = {'title': config['label']}

        # Handle data type mapping
        if field_type == 'decimal':
            field_schema.update({
                'type': 'number',
                'maximum': 10**config['max_digits'] - (10**-config['decimal_places']),
                'minimum': -10**config['max_digits'],
                'multipleOf': 10**-config['decimal_places']
            })
        elif field_type == 'string':
            field_schema['type'] = 'string'
            if 'length' in config:
                field_schema['maxLength'] = config['length']
        elif field_type == 'list':
            field_schema.update({
                'type': 'array',
                'items': generate_json_schema(config['fields'])
            })
        elif field_type == 'file':
            field_schema.update({
                'type': 'string',
                'format': 'binary'
            })

        # Add field to properties
        properties[field_name] = field_schema

        # Handle required fields
        if config.get('required', False):
            required.append(field_name)

    schema = {
        'type': 'object',
        'properties': properties,
        'additionalProperties': False
    }

    if required:
        schema['required'] = required

    return schema