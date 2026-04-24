from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from textual.containers import Container
from textual.widgets import Static
from textual.app import ComposeResult


class Switch(Widget, can_focus=True):
    """کامپوننت سوییچ شبیه iOS"""

    DEFAULT_CSS = """
    Switch {
        width: auto;
        height: auto;
        padding: 0 1;
    }
    
    Switch > .switch-track {
        width: 11;
        height: 3;
        background: #3a3a3c;
        border: none;
        padding: 0;
        transition: background 300ms;
    }
    
    Switch > .switch-track.on {
        background: #34c759;
    }
    
    Switch > .switch-track > .switch-thumb {
        width: 5;
        height: 3;
        background: white;
        content-align: center middle;
        transition: offset 300ms;
        offset: 0 0;
    }
    
    Switch > .switch-track.on > .switch-thumb {
        offset: 6 0;
    }
    
    Switch:focus > .switch-track {
        border: tall $accent;
    }
    
    Switch.-disabled {
        opacity: 0.4;
    }
    
    Switch.-disabled > .switch-track {
        background: #2c2c2e;
    }
    """

    value = reactive(False)
    disabled = reactive(False)

    class Changed(Message):
        """پیام تغییر وضعیت سوییچ"""
        def __init__(self, switch: "Switch", value: bool) -> None:
            super().__init__()
            self.switch = switch
            self.value = value
            self.control = switch

    def __init__(
        self,
        value: bool = False,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._initial_value = value
        self.value = value

    def compose(self) -> ComposeResult:
        track_classes = "switch-track on" if self._initial_value else "switch-track"
        
        with Container(classes=track_classes):
            yield Static("●", classes="switch-thumb")

    def watch_value(self, new_value: bool) -> None:
        """وقتی value تغییر می‌کند"""
        if not self.is_mounted:
            return
            
        try:
            track = self.query_one(".switch-track", Container)
            
            if new_value:
                track.add_class("on")
            else:
                track.remove_class("on")
        except Exception:
            pass

    def toggle(self) -> None:
        """تغییر وضعیت سوییچ"""
        if not self.disabled:
            self.value = not self.value
            self.post_message(self.Changed(self, self.value))

    def on_click(self) -> None:
        """کلیک روی سوییچ"""
        self.toggle()

    def action_toggle(self) -> None:
        """اکشن برای کیبورد"""
        self.toggle()

    BINDINGS = [
        ("enter", "toggle", "Toggle"),
        ("space", "toggle", "Toggle"),
    ]
