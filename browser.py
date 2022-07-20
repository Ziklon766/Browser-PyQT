import os
import sys

from PyQt5.QtCore import QEventLoop, QObject, QSize, Qt, QUrl
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
)

AUTHOR_URL = "https://vk.com/zzz_well"
AUTHOR_NAME = "Точёная София"
BROWSER_NAME = "MyBrowser"


# Утилиты для загрузки иконок
def get_icon_path(name):
    return os.path.join("images", name)


def get_icon(name):
    return QIcon(get_icon_path(name))


def get_pixmap(name):
    return QPixmap(get_icon_path(name))


class AboutDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()

        title = QLabel(BROWSER_NAME)
        font = title.font()
        font.setPointSize(20)
        title.setFont(font)

        layout.addWidget(title)

        logo = QLabel()
        logo.setPixmap(get_pixmap("author.png"))
        layout.addWidget(logo)

        layout.addWidget(QLabel("Version 1.0"))
        layout.addWidget(QLabel(f"{AUTHOR_NAME} 2021"))

        # Выравниваем все элементы по центру
        for i in range(0, layout.count()):
            layout.itemAt(i).setAlignment(Qt.AlignHCenter)

        layout.addWidget(self.buttonBox)

        self.setLayout(layout)


# Так как в Qt при печати через QWebEnginePage приложение иногда крашиться, используем решение из
# https://forum.qt.io/topic/114374/printing-html-using-qwebengineview-fails-pyqt5/2
class PrintHandler(QObject):
    def __init__(self, page):
        super().__init__()
        self.page = page

    def printPreview(self):
        printer = QPrinter()
        preview = QPrintPreviewDialog(printer, self.page.view())
        preview.paintRequested.connect(self.printDocument)
        preview.exec_()

    def printDocument(self, printer):
        # Создаем цикл событий для того, чтобы дождаться результата печати
        loop = QEventLoop()

        def printPreview(ok):
            loop.quit()  # останавливаем цикл, чтобы не зависло

        self.page.print(printer, printPreview)  # помещаем в очередь событий
        # запускаем
        loop.exec_()


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # вкладки, каждый элемент это объект QWebEngineView
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.new_tab_double_click)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)

        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        navtb = QToolBar("Навигация")
        navtb.setIconSize(QSize(16, 16))
        self.addToolBar(navtb)

        btn_back = QAction(get_icon("left.png"), "Назад", self)
        btn_back.setStatusTip("Вернуться к предыдущей странице")
        btn_back.triggered.connect(lambda: self.tabs.currentWidget().back())
        navtb.addAction(btn_back)

        btn_next = QAction(get_icon("right.png"), "Вперед", self)
        btn_next.setStatusTip("Перейти к следующей странице")
        btn_next.triggered.connect(lambda: self.tabs.currentWidget().forward())
        navtb.addAction(btn_next)

        btn_reload = QAction(get_icon("reload.png"), "Перезагрузить", self)
        btn_reload.setStatusTip("Перезагрузить страницу")
        btn_reload.triggered.connect(lambda: self.tabs.currentWidget().reload())
        navtb.addAction(btn_reload)

        btn_home = QAction(get_icon("home.png"), "Домой", self)
        btn_home.setStatusTip("Вернуться на домашнюю страницу")
        btn_home.triggered.connect(lambda: self.navigate_home())
        navtb.addAction(btn_home)

        navtb.addSeparator()

        self.httpsicon = QLabel()
        self.httpsicon.setPixmap(
            get_pixmap("http.png")
        )  # меняется в зависимости от состояния соединения
        navtb.addWidget(self.httpsicon)

        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.urlbar)

        stop_btn = QAction(get_icon("stop.png"), "Стоп", self)
        stop_btn.setStatusTip("Остановить загрузку страницы")
        stop_btn.triggered.connect(lambda: self.tabs.currentWidget().stop())
        navtb.addAction(stop_btn)

        menu_file = self.menuBar().addMenu("&Файл")

        # Создаем меню и добавляем в него пункты
        action_new_tab = QAction(get_icon("new_tab.png"), "Новая вкладка", self)
        action_new_tab.setStatusTip("Создать новую вкладку")
        action_new_tab.triggered.connect(
            lambda: self.add_new_tab()
        )  # полагаемся на аргументы по умолчанию
        menu_file.addAction(action_new_tab)

        action_open_file = QAction(get_icon("open.png"), "Открыть файл...", self)
        action_open_file.setStatusTip("Открыть файл с устройства")
        action_open_file.triggered.connect(self.open_file)
        menu_file.addAction(action_open_file)

        action_save_file = QAction(
            get_icon("save.png"),
            "Сохранить страницу как...",
            self,
        )
        action_save_file.setStatusTip("Сохранить страницу как файл")
        action_save_file.triggered.connect(self.save_file)
        menu_file.addAction(action_save_file)

        print_action = QAction(get_icon("printer.png"), "Печать...", self)
        print_action.setStatusTip("Распечатать текущую страницу")
        print_action.triggered.connect(self.print_page)
        menu_file.addAction(print_action)

        menu_help = self.menuBar().addMenu("&Помощь")

        about_action = QAction(get_icon("question.png"), "О создателе", self)
        about_action.setStatusTip("О создателе")
        about_action.triggered.connect(self.about)
        menu_help.addAction(about_action)

        navigate_to_author = QAction(get_icon("author.png"), "Страница создателя", self)
        navigate_to_author.setStatusTip("Перейти на страницу создателя")
        navigate_to_author.triggered.connect(self.navigate_to_author)
        menu_help.addAction(navigate_to_author)

        self.add_new_tab(QUrl("http://www.google.com"), "Homepage")

        self.show()

        self.setWindowIcon(get_icon("icon.svg"))

    def title_changed(self, title):
        self.setWindowTitle(f"{title} - {BROWSER_NAME}")

    # Функция создания новой вкладки (QWebEngineView)
    def add_new_tab(self, qurl=None, label="Blank"):
        if qurl is None:
            qurl = QUrl("")

        browser = QWebEngineView()
        browser.setUrl(qurl)
        # У каждого объекта QWebEngineView есть свой обработчик событий, привязываем нужные методы к каждому
        browser.titleChanged.connect(self.title_changed)
        i = self.tabs.addTab(browser, label)

        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(
            lambda _: self.tabs.setTabText(i, browser.page().title())
        )

    # Добавление вкладки двойным кликом
    def new_tab_double_click(self, i):
        if i == -1:  # если мы кликнули не по существующей вкладке, создаём её
            self.add_new_tab()

    # Смена текущей вкладки, обновляем urlbar с новой ссылкой
    def current_tab_changed(self, i):
        qurl = self.tabs.currentWidget().url()
        self.update_urlbar(qurl, self.tabs.currentWidget())
        self.title_changed(self.tabs.currentWidget().page().title())

    # Закрытие текущей вкладки
    def close_current_tab(self, i):
        if (
            self.tabs.count() <= 1
        ):  # всегда оставляем хотя бы одну вкладку, чтобы не усложнять обработку пустого списка вкладок
            return

        self.tabs.removeTab(i)

    def navigate_to_author(self):
        self.tabs.currentWidget().setUrl(QUrl(AUTHOR_URL))

    def about(self):
        dlg = AboutDialog()
        dlg.exec_()

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл", "", "*.htm *.html" "All files (*.*)"
        )

        if filename:
            with open(filename, "r") as f:
                html = f.read()

            self.tabs.currentWidget().setHtml(html)
            self.update_urlbar(QUrl(filename), self.tabs.currentWidget())
            self.title_changed(filename)

    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить страницу как", "", "*.htm *html;;" "Все файлы (*.*)"
        )

        if filename:
            # В Qt необходимо использовать callback-функции, которые вызваны по завершению (асинхронно)
            self.tabs.currentWidget().page().toHtml(
                lambda html: self.save_html(filename, html)
            )

    def save_html(self, filename, html):
        with open(filename, "w") as f:
            f.write(html)

    def print_page(self):
        page = self.tabs.currentWidget().page()
        handler = PrintHandler(page)
        handler.printPreview()

    def navigate_home(self):
        self.tabs.currentWidget().setUrl(QUrl("http://www.google.com"))

    def navigate_to_url(self):
        q = QUrl(self.urlbar.text())
        if q.scheme() == "":
            q.setScheme("http")

        self.tabs.currentWidget().setUrl(q)

    def update_urlbar(self, q, browser=None):
        if (
            browser != self.tabs.currentWidget()
        ):  # если вызвано для неактивной вкладки, небезопасно обрабатывать
            return

        if q.scheme() == "https":
            self.httpsicon.setPixmap(get_pixmap("https.png"))
        else:
            self.httpsicon.setPixmap(get_pixmap("http.png"))
        self.urlbar.setText(q.toString())
        self.urlbar.setCursorPosition(0)


# запускаем только если вызваны напрямую, чтобы разрешить импортировать наши классы из других файлов
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(BROWSER_NAME)
    app.setOrganizationName(AUTHOR_NAME)
    app.setOrganizationDomain(AUTHOR_URL)

    window = MainWindow()
    window.showMaximized()

    app.exec_()
