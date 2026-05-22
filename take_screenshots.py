#!/usr/bin/env python
"""Launches the StyleSwitcher GUI and saves a screenshot of each tab."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from app.main import StyleSwitcherUI

OUT_DIR = os.path.join(os.path.dirname(__file__), "docs", "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

LOG = open(os.path.join(OUT_DIR, "log.txt"), "w")
LOG.write("starting\n"); LOG.flush()

app = QApplication(sys.argv)
LOG.write("app created\n"); LOG.flush()
ui = StyleSwitcherUI(app)
LOG.write("ui created\n"); LOG.flush()
ui.resize(900, 700)
ui.show()

tab_names = ["display", "game", "input", "sound", "system"]

def do_screenshots():
    for i, name in enumerate(tab_names):
        ui.tabs.setCurrentIndex(i)
        app.processEvents()
        px = ui.grab()
        px.save(os.path.join(OUT_DIR, f"{name}.png"))
        print(f"Saved {name}.png")
    app.quit()

QTimer.singleShot(500, do_screenshots)
sys.exit(app.exec_())
