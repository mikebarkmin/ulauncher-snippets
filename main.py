from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.event import SystemExitEvent
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ActionList import ActionList
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem

from src.functions import get_snippets, copy_to_clipboard_xsel
from src.items import no_input_item, show_suggestion_items, show_var_input


class SnippetsExtension(Extension):
    def __init__(self):
        super(SnippetsExtension, self).__init__()

        self.state = "select"
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventLister())
        self.subscribe(SystemExitEvent, SystemExitEventListener())

    def reset(self):
        self.snippet = None
        self.variable = None
        self.state = "select"


class ItemEnterEventLister(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        type = data.get("type")

        if type == "select":
            extension.snippet = data.get("snippet")
            extension.state = "var"
        elif type == "cancel":
            extension.reset()
            return SetUserQueryAction("")

        next_variable = extension.snippet.next_variable()
        if extension.state == "var" and next_variable:
            keyword = extension.preferences["snippets_keyword"]
            extension.variable = next_variable
            return ActionList([SetUserQueryAction(keyword + " "), RenderResultListAction(
                show_var_input(extension.snippet,
                               next_variable, next_variable.get("default", ""))
            )])

        copy_mode = extension.preferences["snippets_copy_mode"]
        try:
            snippet = extension.snippet.render(copy_mode=copy_mode)
        except Exception as e:
            return RenderResultListAction([
                ExtensionResultItem(name=str(e), on_enter=DoNothingAction())
            ])
        finally:
            extension.reset()

        if copy_mode == "xsel":
            copy_to_clipboard_xsel(snippet)
            return HideWindowAction()
        else:
            return CopyToClipboardAction(snippet)


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        search = event.get_argument() or str()
        path = extension.preferences["snippets_path"]

        if extension.state == "select":
            return RenderResultListAction(
                show_suggestion_items(
                    get_snippets(path, search))
            )
        elif extension.state == "var":
            return RenderResultListAction(
                show_var_input(extension.snippet, extension.variable, search)
            )
            pass


class SystemExitEventListener(EventListener):
    def on_event(self, event, extension):
        extension.reset()


if __name__ == "__main__":
    SnippetsExtension().run()
