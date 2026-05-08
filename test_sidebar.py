"""Test the sidebar menu directly"""

from textual.app import App
from tui.sidebar_menu import SidebarMainMenuScreen

class TestApp(App):
    def __init__(self):
        self.user = {"id": 1, "username": "admin"}
        super().__init__()
    
    def on_mount(self):
        self.push_screen(SidebarMainMenuScreen())

if __name__ == "__main__":
    app = TestApp()
    app.run()
