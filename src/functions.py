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
from jinja2 import Template, environment, Environment
from pathlib import Path
from urllib.parse import unquote
from ulauncher.utils.fuzzy_search import get_score
from typing import List, Dict, Callable
from subprocess import Popen, PIPE

from .filters import camelcase, pascalcase, kebabcase, snakecase


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
    '[[2020-12-09]] <== <button class="date_button_today">Today</button> ==> [[2020-12-11]]'

    >>> s = Snippet('test-snippets/frontmatter.j2', 'test-snippets')
    >>> s.render()
    'Here is the content\\n\\n2020-12-10\\n\\nHi'

    >>> s = Snippet('test-snippets/react/component.j2', 'test-snippets')
    >>> s.variables["name"]["value"] = "My Component"
    >>> s.render()
    'import React from "react"\\n\\nconst MyComponent = () => ();\\n\\nexport default MyComponent'

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
    '€\\nMike Barkmin'

    >>> s = Snippet('test-snippets/filters.j2', 'test-snippets')
    >>> s.render()
    '*****'

    """

    def __init__(self, path: str, root_path: str = ""):
        snippet = frontmatter.load(path)
        icon = snippet.get("icon")

        if icon:
            self.icon = os.path.join(root_path, icon)
        else:
            self.icon = "images/icon.png"

        self.globals_path = os.path.join(root_path, "globals.py")
        self.filters_path = os.path.join(root_path, "filters.py")
        self.variables = snippet.get("vars", {})
        file_name = str(Path(path).relative_to(root_path))
        self.name = snippet.get("name", file_name[:-3])
        self.path = path
        self.description = snippet.get("description", snippet.content[:40])

    def render(self, args=[], copy_mode="gtk") -> str:
        snippet = frontmatter.load(self.path)

        filters = {}
        if os.path.exists(self.filters_path):
            filters = import_file("filters", self.filters_path).filters
            # filters need to be added before creating a template
            environment.DEFAULT_FILTERS = {
                **environment.DEFAULT_FILTERS,
                **filters
            }

        template = Template(snippet.content)

        globals = {}
        if os.path.exists(self.globals_path):
            globals = import_file("globals", self.globals_path).globals

        return template.render(
            date=date,
            clipboard=output_from_clipboard_xsel if copy_mode == "xsel" else output_from_clipboard_gtk,
            random_int=random_int,
            random_item=random_item,
            random_uuid=random_uuid,
            vars=self.get_variable,
            **globals
        )

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


def fuzzyfinder(input, collection, accessor=lambda x: x, sort_results=True):
    """
    Args:
        input (str): A partial string which is typically entered by a user.
        collection (iterable): A collection of strings which will be filtered
                               based on the `input`.
        accessor (function): If the `collection` is not an iterable of strings,
                             then use the accessor to fetch the string that
                             will be used for fuzzy matching.
        sort_results(bool): The suggestions are sorted by considering the
                            smallest contiguous match, followed by where the
                            match is found in the full string. If two suggestions
                            have the same rank, they are then sorted
                            alpha-numerically. This parameter controls the
                            *last tie-breaker-alpha-numeric sorting*. The sorting
                            based on match length and position will be intact.
    Returns:
        suggestions (generator): A generator object that produces a list of
            suggestions narrowed down from `collection` using the `input`.


    >>> list(fuzzyfinder("al", ["hi", "hu", "hallo", "false"]))
    ['false', 'hallo']
    """
    suggestions = []
    input = str(input) if not isinstance(input, str) else input
    pat = '.*?'.join(map(re.escape, input))
    # lookahead regex to manage overlapping matches
    pat = '(?=({0}))'.format(pat)
    regex = re.compile(pat, re.IGNORECASE)
    for item in collection:
        r = list(regex.finditer(accessor(item)))
        if r:
            # find shortest match
            best = min(r, key=lambda x: len(x.group(1)))
            suggestions.append(
                (len(best.group(1)), best.start(), accessor(item), item))

    if sort_results:
        return (z[-1] for z in sorted(suggestions))
    else:
        return (z[-1] for z in sorted(suggestions, key=lambda x: x[:2]))


def random_uuid() -> str:
    return uuid.uuid4().hex


def random_int(min: int, max: int) -> int:
    return random.randint(min, max)


def random_item(list: List[str]) -> str:
    return random.choice(list)


def copy_to_clipboard_xsel(text: str):
    p = Popen(['xsel', '-bi'], stdin=PIPE)
    p.communicate(input=text.encode("utf-8"))


def output_from_clipboard_xsel() -> str:
    p = Popen(['xsel', '-bo'], stdout=PIPE, universal_newlines=True)
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
    search_pattern = os.path.join(path, "**", "*.j2")
    logger.info(search_pattern)
    files = glob.glob(search_pattern, recursive=True)
    suggestions = fuzzyfinder(search, files)

    return [
        Snippet(path=f, root_path=path) for f in suggestions
    ]


if __name__ == "__main__":
    import doctest
    from freezegun import freeze_time
    freezer = freeze_time("2020-12-10 12:00:01")
    freezer.start()
    doctest.testmod()
    freezer.stop()
