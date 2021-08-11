import logging

import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify, GdkPixbuf

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

from src.functions import get_snippets, copy_to_clipboard_xsel, copy_to_clipboard_wl
from src.items import no_input_item, show_suggestion_items, show_var_input
from src.html_to_text import html_to_text


logger = logging.getLogger(__name__)


class SnippetsExtension(Extension):
    def __init__(self):
        super(SnippetsExtension, self).__init__()

        self.state = "select"
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventLister())
        self.subscribe(SystemExitEvent, SystemExitEventListener())

        Notify.init("ulauncher-snippets")

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

        try:
            copy_mode = extension.preferences["snippets_copy_mode"]
            if extension.snippet.file_path_template:
                file_path = extension.snippet.render_to_file_path(copy_mode=copy_mode)
                self._notify(extension, file_path)
                return HideWindowAction()
            else:
                (mimetype, snippet) = extension.snippet.render(copy_mode=copy_mode)

                action = None
                if copy_mode == "xsel":
                    copy_to_clipboard_xsel(snippet, mimetype)
                    action = HideWindowAction()
                elif copy_mode == "wl":
                    copy_to_clipboard_wl(snippet, mimetype)
                    action = HideWindowAction()
                else:
                    action = CopyToClipboardAction(snippet)

                self._notify(extension, snippet, mimetype)
                return action
        except Exception as e:
            logger.exception(e)
            return RenderResultListAction([
                ExtensionResultItem(name=str(e), on_enter=DoNothingAction())
            ])
        finally:
            extension.reset()

    def _notify(self, extension, snippet, mimetype):
        notification_behavior = extension.preferences["notification_behavior"]
        if notification_behavior == "disabled":
            return

        notification = Notify.Notification.new("Snippet copied to clipboard")
        notification.set_urgency(0) # lowest priority

        try:
            image = GdkPixbuf.Pixbuf.new_from_file(extension.snippet.icon)
            notification.set_image_from_pixbuf(image)
        except:
            logger.exception("Failed to set notification icon")

        if notification_behavior == "no_content":
            return notification.show()

        if notification_behavior == "with_content":
            body = html_to_text(snippet) if mimetype == "text/html" else snippet
            notification.update("Snippet copied to clipboard", body)

        return notification.show()


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        search = event.get_argument() or str()
        path = extension.preferences["snippets_path"]

        if extension.state == "select":
            return RenderResultListAction(
                show_suggestion_items(
                    get_snippets(path, search)),
                    extension.preferneces.get("number_of_results", 8)
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
