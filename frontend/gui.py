import sys
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

def load_config():
    with open("/app/backend/config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    config = load_config()

    width = config.get("display_width", 720)
    height = config.get("display_height", 720)

    app = QApplication(sys.argv)

    view = QWebEngineView()
    view.resize(width, height)

    # URL des Flask-Backends (Container-Name = backend)
    view.load(QUrl("http://backend:5008"))

    view.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
