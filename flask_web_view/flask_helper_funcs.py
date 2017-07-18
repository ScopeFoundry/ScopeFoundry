from jinja2 import Environment, FileSystemLoader

def load_template_by_dir(template_dir, filename, context):
    TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(template_dir),
    trim_blocks=False)
    return TEMPLATE_ENVIRONMENT.get_template(filename).render(context)
