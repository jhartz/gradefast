"""
Utility functions used throughout GradeFast.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import json
import sys
import time
import uuid
from typing import Any, Union


def required_package_error(module_name: str, package_name: str = None) -> None:
    if not package_name:
        package_name = module_name
    required_package_warning(
        module_name,
        "Please install '" + package_name + "' and try again.")
    sys.exit(1)


def required_package_warning(module_name: str, msg: str = None) -> None:
    print("==> Couldn't find", module_name, "module!")
    if msg:
        print("==>", msg)


try:
    import mistune
    _markdown = mistune.Markdown(renderer=mistune.Renderer(hard_wrap=True))
    has_markdown = True
except ImportError:
    required_package_warning("mistune", "Comments and hints will not be Markdown-parsed.")
    mistune = None
    has_markdown = False


def markdown_to_html(text: str, inline_only: bool = False) -> str:
    """
    Convert a string (possibly containing Markdown syntax) to an HTML string. If a Markdown parser
    is not available, then just HTML-escape the string.

    WARNING: This does NOT properly escape all HTML! It is valid to have normal HTML in Markdown,
    so don't rely on this function to escape possibly malicious user input for you.

    :param text: The Markdown text to convert.
    :param inline_only: If True, then we will replace paragraph elements with simple line breaks.
    :return: HTML equivalent of the text parameter.
    """
    text = text.rstrip()
    if not has_markdown:
        html = text.replace("&", "&amp;")   \
                   .replace("\"", "&quot;") \
                   .replace("<", "&lt;")    \
                   .replace(">", "&gt;")    \
                   .replace("\n", "<br>")
    else:
        html = _markdown(text)
        if inline_only:
            html = html.replace('<p>', '').replace('</p>', '<br>')
        else:
            html = html.replace('<p>', '<p style="margin: 3px 0">')

        # WARNING: MyCourses (Desire2Learn platform) will cut out any colors provided in "rgba"
        # format for any CSS properties in the "style" attribute
        CODE_STYLE = "background-color: #f5f5f5; padding: 1px 3px; border: 1px solid #cccccc; " \
                     "border-radius: 4px;"
        # Make <code> tags prettier
        html = html.replace(
            '<code>',
            '<code style="' + CODE_STYLE + '">')
        # Except where we have a case of <pre><code>, then apply it to the <pre> instead
        html = html.replace(
            '<pre><code style="' + CODE_STYLE + '">',
            '<pre style="' + CODE_STYLE + '"><code>')

    html = html.rstrip()
    if html.endswith('<br>'):
        html = html[:-4].rstrip()

    return html


def markdown_to_html_inline(text: str) -> str:
    return markdown_to_html(text, True)


class GradeBookJSONEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder that encodes UUIDs as a string containing the hex version of the UUID.
    """

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)

        # If the object has a to_json method, use that
        if hasattr(o, "to_json") and callable(o.to_json):
            return o.to_json()

        return super().default(o)


_json_encoder_instance = None


def to_json(o: object, **kwargs: Any) -> str:
    """
    Convert an object to a JSON string. For usage, see json.dumps(...).
    """
    if kwargs:
        encoder = GradeBookJSONEncoder(**kwargs)
    else:
        global _json_encoder_instance
        if _json_encoder_instance is None:
            _json_encoder_instance = GradeBookJSONEncoder()
        encoder = _json_encoder_instance
    return encoder.encode(o)


def from_json(s: str, **kwargs: Any) -> object:
    """
    Convert a JSON string to an object representation. For usage, see json.loads(...).
    """
    return json.loads(s, **kwargs)


JSONDecodeError = json.JSONDecodeError


def timestamp_to_str(timestamp: Union[int, float]) -> str:
    return time.strftime("%a %b %d %Y %I:%M:%S %p %Z", time.localtime(timestamp))
