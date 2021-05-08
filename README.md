# Snippets Ulauncher extension

![Demo](demo.gif)

This Ulauncher extension enables you to copy snippets to your clipboard.

## Requirements

Before installing, make sure to install all the needed Python packages for your system:
```
pip3 install --user dateparser jinja2 python-frontmatter
```

If you want to use the xsel mode, which runs more reliable on my system you need to install xsel and select copy mode xsel in the extension settings.

```
sudo apt install xsel
```

If you want to use the wl mode, which runs more reliable on wayland systems you need to install wl-clipboard and select copy mode wl in the extension settings.

```
sudo apt install wl-clipboard
```

## Install

Then open Ulauncher preferences window > extensions > add extension and paste the following URL:

```
https://github.com/mikebarkmin/ulauncher-snippets
```

## Usage

For your snippets to be loaded place j2-files in your snippets directory. You can configure the directory in the extension settings. Type `snip` in Ulauncher and select the snippet you want to use.

## Snippets

### Frontmatter

You can define a frontmatter for your snippet like so:

```
---
name: "Frontmatter Snippet"
description: "This is a description"
icon: "test-snippets/test.png"
vars:
    name: 
        label: "Name of the component"
        default: "NewComponent"
    other_var:
        label: "A var with no default"
markdown: false
markdown_extensions: []
---

My snippet {{ date('now') }}!
```

Each key of the frontmatter does have a fallback:

* `name`: Filename (e.g., date.j2 => date)
* `description`: First 40 characters of your snippet
* `icon`: The snippets extensions icon
* `vars`: An empty dictionary
* `markdown`: Indicates this snippet should render markdown. Disabled by default.
* `markdown_extensions`: Sets the [Markdown extensions] to use when `markdown` is enabled.

If you define vars for your snippet the user will get inputs for each one and you can you them in your snippet. See below Placeholder -> Variables. To use the default value you need to input `-`.

### Markdown snippets

> **Note:** Markdown snippets only work in `xsel` and `wl` modes.

Normally, snippets are rendered as plain text.

When `markdown: true` is specified, you can write snippets in markdown which will be rendered to HTML (using [Python-Markdown]) before being put on the clipboard.
This allows rich text snippets in applications that understand HTML clipboard content.

By default, all of the [extra][markdown-extra] extensions as well as the [sane lists][markdown-sane-lists] extension are enabled.
It's possible to override this by specifying a list of extensions in `markdown_extensions` yourself.

### Placeholder

Placeholder need to be surrounded by `{{ placeholder }}`.

#### Variables

You can provide variables to the snippets. These are available via the following:

```
{{ vars("name") }}
```

#### Date

You can have a date placeholder which will be replaced by a date. The format is the following:

```
{{ date("date_expression", "date_format")}}
```

* date_expression can be any format supported by [dateparser](https://dateparser.readthedocs.io/en/latest/)
* date_format can be any format supported by [strftime](http://strftime.org/)

For example: `{{ date("now", "%Y-%M-%d") }}` => 2020-12-10

#### Clipboard

The clipboard offset allows you to specify which clipboard items you want to insert.

For example: `{{ clipboard() }}`

#### Random

You can have a random placeholder which replace by a random value.

* Random UUID: `{{ random_uuid() }}`
* Random Integer: `{{ random_int(min, max) }}`
* Random Item from List: `{{ random_item(["apple", "banana"]) }}`

### Filters

Placeholders can be modified by filters. Filters are separated from the placeholder by a pipe symbol `|` and may have optional arguments in parentheses.

For example `{{ clipboard | escape | title }}` will convert the characters &, <, >, ‘, and ” in string s to HTML-safe sequences (escape) and will convert it to titlecase.

Here you can find a [list of builtin filters](https://jinja.palletsprojects.com/en/2.11.x/templates/#list-of-builtin-filters).

Additionally, you can use:

* camelcase: A title -> aTitle
* pascalcase: A title -> ATitle
* snakecase: A title -> a_title
* kebabcase: A title -> a-title
* urldecode: Replace %xx escapes with their single-character equivalent (see [urllib](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.unquote))

### Advance

Snippets are basically [Jinja2](https://jinja.palletsprojects.com/en/2.11.x/templates/) templates. This means that you can do very fancy stuff. Like conditional snippets or loop. See their documentation for more information.

#### Custom Filters

Custom filters are just regular Python functions that take the left side of the filter as the first argument and the arguments passed to the filter as extra arguments or keyword arguments. For example:

```python
def replace_with_symbol(text: str, symbol: str) -> str:
    return symbol * len(text)

filters = {
    "replace_with_symbol": replace_with_symbol
}
```

```j2
{{ "Hello"|replace_with_symbol("*") }}
```

Results in:

```
*****
```

#### Custom Globals

You can provide global variables and functions to your snippets by creating a `globals.py` file in your snippets directory. This files needs to have at least one dictionary `globals`. For example:

```python
import urllib.request
import json

def get_temperature(long: float, lat: float) -> float:
    with urllib.request.urlopen("https://my-weather-service.org") as url:
        data = json.loads(url.read().decode())
        return f"{data['temp']}"

globals = {
    "name": "Mike Barkmin"
    "temperature": get_temperature
}
```

```j2
{{ name }}
{{ temperature() }} °C
```

Results in:

```
Mike Barkmin
18.5 °C
```


#### Difference between Filters and Globals

I guess in the context of ulauncher-snippets there is no big different between them. There is only a conceptual difference. If you want to dive deeper into the [jinja2 documentation](https://jinja.palletsprojects.com/en/2.11.x/api/#custom-filters) you find that filters can also be passed the current template context or environment. I do not know if this is of interest for this extensions but it is there
## Snippet Repositories

This is a list of public repositories with snippets for inspiration.

- https://github.com/mikebarkmin/ulauncher-snippets-files/

Leave a pull request if you want your snippet repository to be listed.

## Developer

### Run Test

Currently, doctest is used for the `functions` module. To run the tests execute the following command:

```
python3 -m src.functions
``` 

[Python-Markdown]: https://python-markdown.github.io/
[Markdown extensions]: https://python-markdown.github.io/extensions/
[Markdown-extra]: https://python-markdown.github.io/extensions/extra/
[Markdown-sane-lists]: https://python-markdown.github.io/extensions/sane_lists/
