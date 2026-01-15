import flet as ft
from src.ui.app_layout import EGMApp

import logging
logging.basicConfig(level=logging.INFO)

def main(page: ft.Page):
    page.title = "Open EGM-4 Interface"
    
    app = EGMApp(page)
    page.add(app.build())

if __name__ == '__main__':
    ft.app(target=main)
