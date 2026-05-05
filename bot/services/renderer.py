from jinja2 import Environment, FileSystemLoader
import os
import logging

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

# Singleton environment — created once, reused for every render call
_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)


def render_template(template_name: str, data: dict, is_preview: bool = False) -> str:
    """
    Render a Jinja2 template with structured data.
    The template_name should match a file in the templates/ folder (without .html).
    All memecoin variants use the same 'memecoin' template.
    """
    if template_name.startswith("memecoin"):
        template_name = "memecoin"

    template = _env.get_template(f"{template_name}.html")
    return template.render(**data, is_preview=is_preview)

def save_preview(html_content: str, project_id) -> str:
    """
    Save rendered HTML to a preview file.
    project_id can be an int (final build) or a string like 'section_header' (section preview).
    """
    preview_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'previews')
    os.makedirs(preview_dir, exist_ok=True)
    
    file_path = os.path.join(preview_dir, f'preview_{project_id}.html')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return file_path
