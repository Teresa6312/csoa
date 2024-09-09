# In a file, e.g., context_processors.py within one of your apps

def default_context(request):
    template_name = request.resolver_match.view_name
    if template_name:
        subtitle = template_name.split(':')[-1].replace('.html', '')
    else:
        subtitle = ''
    return {
        'subtitle': subtitle,
		'is_nav_sidebar_enabled': False,
		'is_popup': False
    }
