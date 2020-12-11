from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from typing import List
import logging

from src.functions import Snippet

logger = logging.getLogger(__name__)


ICON_FILE = "images/icon.png"


def no_input_item():
    return [
        ExtensionResultItem(icon=ICON_FILE, name="No snippet",
                            on_enter=DoNothingAction())
    ]


def show_var_input(snippet, variable, value):
    value = value.strip()

    if value == "-":
        variable["value"] = variable.get("default", "")
    else:
        variable["value"] = value

    return [
        ExtensionResultItem(
            icon=snippet.icon,
            name=variable.get("label"),
            on_enter=ExtensionCustomAction({}, keep_app_open=True)
        ),
        ExtensionResultItem(
            icon=ICON_FILE,
            name="Cancel",
            on_enter=ExtensionCustomAction(
                {"type": "cancel"}, keep_app_open=True)
        )
    ]


def show_suggestion_items(suggestions: List[Snippet]):

    if len(suggestions) == 0:
        return no_input_item()

    return [
        ExtensionResultItem(
            icon=suggestion.icon,
            name=suggestion.name,
            description=suggestion.description,
            on_enter=ExtensionCustomAction({
                "type": "select",
                "snippet": suggestion
            }, keep_app_open=True),
        )
        for suggestion in suggestions
    ]
