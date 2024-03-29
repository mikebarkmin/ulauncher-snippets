# type: ignore[misc]
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

import re
import time
import random
import uuid
import os
import glob
import dateparser
import logging
import frontmatter
import subprocess
from jinja2 import Template, environment, Environment
from pathlib import Path
from urllib.parse import unquote
from ulauncher.utils.fuzzy_search import get_score
from typing import List, Dict, Callable, NewType

from .filters import camelcase, pascalcase, kebabcase, snakecase

MimeType = NewType("MimeType", str)

logger = logging.getLogger(__name__)

environment.DEFAULT_FILTERS["camelcase"] = camelcase
environment.DEFAULT_FILTERS["pascalcase"] = pascalcase
environment.DEFAULT_FILTERS["kebabcase"] = kebabcase
environment.DEFAULT_FILTERS["snakecase"] = snakecase
environment.DEFAULT_FILTERS["urldecode"] = unquote


class Snippet:
    """
    >>> s = Snippet('test-snippets/date.j2', 'test-snippets')
    >>> s.render()
    ('text/plain', '[[2020-12-09]] <== <button class="date_button_today">Today</button> ==> [[2020-12-11]]')

    >>> s = Snippet('test-snippets/frontmatter.j2', 'test-snippets')
    >>> s.render()
    ('text/plain', 'Here is the content\\n\\n2020-12-10\\n\\nHi')

    >>> s = Snippet('test-snippets/markdown.j2', 'test-snippets')
    >>> s.render()
    ('text/html', '<p>A snippet with <a href="https://daringfireball.net/projects/markdown/">Markdown</a> in it.</p>')

    >>> s = Snippet('test-snippets/copy-to-path.j2', 'test-snippets')
    >>> s.variables["name"]["value"] = "test"
    >>> s.render_to_file_path()
    '~/test.ulauncher-snippets.test.md'

    >>> s = Snippet('test-snippets/markdown-extensions.j2', 'test-snippets')
    >>> s.render()
    ('text/html', '<p>A snippet with <a class="wikilink" href="/Markdown/">Markdown</a> in it.</p>')

    >>> s = Snippet('test-snippets/react/component.j2', 'test-snippets')
    >>> s.variables["name"]["value"] = "My Component"
    >>> s.render()
    ('text/plain', 'import React from "react"\\n\\nconst MyComponent = () => ();\\n\\nexport default MyComponent')

    >>> s = Snippet('test-snippets/frontmatter.j2', 'test-snippets')
    >>> s.next_variable()
    {'label': 'Name of the component'}

    >>> s.variables["name"]["value"] = "Set"
    >>> s.next_variable()
    {'label': 'With default', 'default': 'Hi'}

    >>> s.get_variable("name")
    'Set'

    >>> s.get_variable("other_var")
    'Hi'

    >>> s = Snippet('test-snippets/globals.j2', 'test-snippets')
    >>> s.render()
    ('text/plain', '€\\nMike Barkmin')

    >>> s = Snippet('test-snippets/filters.j2', 'test-snippets')
    >>> s.render()
    ('text/plain', '*****')
    """

    def __init__(self, path: str, root_path: str = ""):
        snippet = frontmatter.load(path)
        icon = snippet.get("icon")

        if icon:
            self.icon = os.path.join(root_path, icon)
        else:
            # Icon is allowed to be relative for ulauncher itself, but breaks with
            # GdkPixbuf.Pixbuf.new_from_file() used to construct notifications.
            # Making the path absolute avoids this problem.
            script_path = os.path.dirname(os.path.abspath(__file__))
            self.icon = os.path.join(script_path, "..", "images/icon.png")

        self.globals_path = os.path.join(root_path, "globals.py")
        self.filters_path = os.path.join(root_path, "filters.py")
        self.variables = snippet.get("vars", {})
        file_name = str(Path(path).relative_to(root_path))
        self.name = snippet.get("name", file_name[:-3])
        self.path = path
        self.description = snippet.get("description", snippet.content[:40])
        self.is_markdown = snippet.get("markdown", False)
        self.file_path_template = snippet.get("file_path_template")
        self.file_overwrite = snippet.get("file_overwrite", False)
        self.markdown_extensions = snippet.get(
            "markdown_extensions", ["extra", "sane_lists"]
        )

    def render_to_file_path(self, args=[], copy_mode="gtk"):
        file_path = self._render(self.file_path_template, args, copy_mode)
        file_path = os.path.expanduser(file_path)
        (mime_type, content) = self.render(args, copy_mode)
        if not os.path.exists(file_path):
            with open(file_path, "w+") as f:
                f.write(content)
        else:
            raise FileExistsError(file_path)

        return file_path

    def _render(self, template_str: str, args=[], copy_mode="gtk"):
        filters = {}
        if os.path.exists(self.filters_path):
            filters = import_file("filters", self.filters_path).filters
            # filters need to be added before creating a template
            environment.DEFAULT_FILTERS = {**environment.DEFAULT_FILTERS, **filters}

        template = Template(template_str)

        globals = {}
        if os.path.exists(self.globals_path):
            globals = import_file("globals", self.globals_path).globals

        clipboard_func = output_from_clipboard_gtk
        if copy_mode == "xsel":
            clipboard_func = output_from_clipboard_xsel
        elif copy_mode == "wl":
            clipboard_func = output_from_clipboard_wl

        rendered_snippet = template.render(
            date=date,
            clipboard=clipboard_func,
            random_int=random_int,
            random_item=random_item,
            random_uuid=random_uuid,
            vars=self.get_variable,
            **globals
        )

        return rendered_snippet

    def render(self, args=[], copy_mode="gtk") -> (MimeType, str):
        snippet = frontmatter.load(self.path)

        rendered_snippet = self._render(snippet.content, args, copy_mode)

        if self.is_markdown:
            try:
                # By importing this conditionally here we can keep this an
                # optional dependency, only needed for people who want to use
                # Markdown-rendered snippets.
                import markdown
            except ImportError as e:
                raise Exception("Missing python-markdown package") from e
            rendered_snippet = markdown.markdown(
                rendered_snippet,
                extensions=self.markdown_extensions,
                output_format="html5",
            )
            return ("text/html", rendered_snippet)
        else:
            return ("text/plain", rendered_snippet)

    def next_variable(self):
        for id, variable in self.variables.items():
            if not variable.get("value"):
                return variable
        return None

    def get_variable(self, name):
        var = self.variables.get(name)
        default = var.get("default", "")
        value = var.get("value", default)
        return value

    def __repr__(self):
        return self.name


def import_file(full_name, path):
    """Import a python module from a path. 3.4+ only.

    Does not call sys.modules[full_name] = path
    """
    from importlib import util

    spec = util.spec_from_file_location(full_name, path)
    mod = util.module_from_spec(spec)

    spec.loader.exec_module(mod)
    return mod


def get_name_from_path(path: str, exclude_ext=True, root_path="") -> str:
    """
    >>> get_name_from_path("~/home/test/bla/hallo.md", root_path="~/home/test")
    'bla/hallo'

    >>> get_name_from_path("~/home/Google Drive/Brain 1.0", False, root_path="~/home/Google Drive")
    'Brain 1.0'
    """
    base = os.path.relpath(path, root_path)
    if exclude_ext:
        split = os.path.splitext(base)
        return split[0]
    return base


def fuzzyfinder(search: str, items: List[str], root_path: str) -> List[str]:
    """
    >>> fuzzyfinder("hallo", ["hi", "hu", "hallo", "false"])
    ['hallo', 'false', 'hi', 'hu']
    """
    scores = []
    for i in items:
        score = get_score(search, get_name_from_path(i, root_path=root_path))
        scores.append((score, i))

    scores = sorted(scores, key=lambda score: score[0], reverse=True)

    return list(map(lambda score: score[1], scores))


def random_uuid() -> str:
    return uuid.uuid4().hex


def random_int(min: int, max: int) -> int:
    return random.randint(min, max)


def random_item(list: List[str]) -> str:
    return random.choice(list)


def copy_to_clipboard_xsel(text: str, mimetype: MimeType):
    try:
        # xsel does not support setting a mimetype, so try to use xclip when available but fall back to xsel.
        subprocess.run(
            ["xclip", "-target", mimetype, "-selection", "clipboard"],
            input=text,
            encoding="utf-8",
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.run(["xsel", "-bi"], input=text, encoding="utf-8", check=True)


def copy_to_clipboard_wl(text: str, mimetype: MimeType):
    subprocess.run(
        ["wl-copy", "--type", mimetype], input=text, encoding="utf-8", check=True
    )


def output_from_clipboard_xsel() -> str:
    p = subprocess.Popen(
        ["xsel", "-bo"], stdout=subprocess.PIPE, universal_newlines=True
    )
    out, err = p.communicate()

    if err:
        return ""
    return convert_clipboard(out)


def output_from_clipboard_wl() -> str:
    p = subprocess.Popen(["wl-paste"], stdout=subprocess.PIPE, universal_newlines=True)
    out, err = p.communicate()

    if err:
        return ""
    return convert_clipboard(out)


def output_from_clipboard_gtk() -> str:
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    text = clipboard.wait_for_text()

    if text is not None:
        return convert_clipboard(text)

    return ""


def convert_clipboard(text: str) -> str:
    """
    >>> convert_clipboard("x-special/nautilus-clipboard\\ncopy\\nfile:///home/root/Screenshot%20on%202020-11-22%2013-22-51.png\\nfile:///home/root/Screenshot%20on%202020-11-20%2020-07-20.png")
    '/home/root/Screenshot on 2020-11-22 13-22-51.png\\n/home/root/Screenshot on 2020-11-20 20-07-20.png'
    """
    if text.startswith("x-special/nautilus-clipboard"):
        out = ""
        lines = text.split("\n")
        for line in lines[2:]:
            out += unquote(line[7:]) + "\n"
        return out[:-1]

    return text


def date(expression: str, format: str = "%Y-%m-%d") -> str:
    """
    >>> date("last year", "%Y")
    '2019'

    >>> date("", "%B")
    ''
    """
    dt = dateparser.parse(expression)
    if dt is not None:
        formatted_dt = dt.strftime(format)
        return formatted_dt
    return ""


def get_snippets(path: str, search: str) -> List[Snippet]:
    """
    >>> get_snippets("test-snippets", "react")
    [react/component]
    """
    path = os.path.expanduser(path)
    search_pattern = os.path.join(path, "**", "*.j2")
    logger.info(search_pattern)
    files = glob.glob(search_pattern, recursive=True)
    suggestions = fuzzyfinder(search, files, path)

    snippets = []
    for f in suggestions:
        try:
            s = Snippet(path=f, root_path=path)
            snippets.append(s)
        except:
            continue
    return snippets


if __name__ == "__main__":
    import doctest
    from freezegun import freeze_time

    freezer = freeze_time("2020-12-10 12:00:01")
    freezer.start()
    doctest.testmod()
    freezer.stop()
