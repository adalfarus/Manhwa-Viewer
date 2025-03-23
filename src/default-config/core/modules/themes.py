from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


class Theme:
    def __init__(self, stylesheet, app_style, theme_style):
        self.stylesheet = stylesheet
        self.app_style = app_style
        self.theme_style = theme_style


class DynamicTheme:
    def __init__(self, stylesheet_template: str, app_style, theme_style):
        self.app_style = app_style
        self.theme_style = theme_style
        self.stylesheet_template: str = stylesheet_template

    @property
    def stylesheet(self):
        return self.get_dynamic_lineedit_stylesheet()

    def get_dynamic_lineedit_stylesheet(self):
        # Get the application palette for the current theme
        palette = QApplication.palette()

        # Fetch colors from the palette to adapt to light or dark mode
        base_color = palette.color(QPalette.ColorRole.Base).name()                # LineEdit background
        text_color = palette.color(QPalette.ColorRole.Text).name()                # Text color
        window_color = palette.color(QPalette.ColorRole.Window).name()
        selection_background = palette.color(QPalette.ColorRole.Highlight).name() # Selection background
        selection_text = palette.color(QPalette.ColorRole.HighlightedText).name() # Selected text color
        hover_background = palette.color(QPalette.ColorRole.Dark).name() # Hover background color
        disabled_text_color = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name()
        highlight_color = palette.color(QPalette.ColorRole.Highlight).name()
        highlighted_text_color = palette.color(QPalette.ColorRole.HighlightedText).name()
        alternate_base_color = palette.color(QPalette.ColorRole.AlternateBase).name()
        focus_border = palette.color(QPalette.ColorRole.Dark).name()              # Focus border color
        hover_border = "#888888"                                        # Hover border color (static)
        normal_border = "#808080"                                       # Default border color (static)
        text_color = palette.color(QPalette.Text).name()
        window_color = palette.color(QPalette.Window).name()
        disabled_text_color = palette.color(QPalette.Disabled, QPalette.Text).name()
        disabled_bg_color = palette.color(QPalette.Disabled, QPalette.Window).name()
        base_color = palette.color(QPalette.Base).name()
        alternate_base_color = palette.color(QPalette.ColorRole.Mid).name()
        highlight_color = palette.color(QPalette.Highlight).name()
        highlighted_text_color = palette.color(QPalette.HighlightedText).name()
        dark_color = palette.color(QPalette.Dark).name()
        mid_color = palette.color(QPalette.Mid).name()
        light_color = palette.color(QPalette.Light).name()

        # Return a stylesheet with dynamic colors for QLineEdit with ID `search_widget_line_edit`
        return self.stylesheet_template.format(
            base_color=base_color,
            window_color=window_color,
            text_color=text_color,
            disabled_text_color=disabled_text_color,
            highlight_color=highlight_color,
            highlighted_text_color=highlighted_text_color,
            alternate_base_color=alternate_base_color,
            focus_border=focus_border,
            normal_border=normal_border,
            hover_border=hover_border,
            dark_color=dark_color,
            mid_color=mid_color,
            light_color=light_color,
            disabled_bg_color=disabled_bg_color
        )


def generate_theme_stylesheet(
        text_color="#FFFFFF",
        background_color="#333333",
        disabled_text_color="#7F7F7F",
        disabled_background_color="#444444",
        border_color="#808080",
        hover_background="#555555",
        selection_background="#555555",
        selection_text_color="white",
        focus_background="#333333",
        highlight_border="#AAAAAA",
        button_background="#444444",
        scrollbar_handle="#666666"
):
    return f"""
        QWidget {{
            color: {text_color};
            background-color: {background_color};
        }}
        QWidget:disabled {{
            color: {disabled_text_color};
            background-color: {disabled_background_color};
        }}
        QWidget#transparentImage {{
            background: transparent;
        }}

        QComboBox {{
            border: 1px solid {border_color};
            border-radius: 5px;
            padding: 5px;
            background-color: {button_background};
            selection-background-color: {selection_background};
            selection-color: {selection_text_color};
        }}
        QComboBox::drop-down {{
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url(data/arrow-down.png);
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {border_color};
            background-color: {button_background};
            border-radius: 5px;
            margin-top: -5px;
        }}

        QCheckBox {{
            border-radius: 5px;
        }}

        QLabel {{
            border-radius: 5px;
            padding: 5px;
            background-color: {hover_background};
        }}

        ImageLabel {{
            padding: 0;
            background-color: transparent;
        }}

        QPushButton {{
            border: 1px solid {highlight_border};
            border-radius: 5px;
            padding: 5px;
            background-color: {button_background};
        }}
        QPushButton:hover {{
            background-color: {hover_background};
        }}

        QToolButton {{
            border: 1px solid {highlight_border};
            border-radius: 5px;
            background-color: {button_background};
        }}
        QToolButton:hover {{
            background-color: {hover_background};
        }}

        QScrollBar:horizontal {{
            border: none;
            background-color: transparent;
            height: 15px;
            border-radius: 7px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {scrollbar_handle};
            min-height: 15px;
            min-width: 40px;
            border-radius: 7px;
        }}
        QScrollBar::handle:hover {{
            background-color: {hover_background};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        QScrollBar:vertical {{
            border: none;
            background-color: transparent;
            width: 15px;
            border-radius: 7px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {scrollbar_handle};
            min-height: 20px;
            border-radius: 7px;
        }}
        QScrollBar::handle:hover {{
            background-color: {hover_background};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar::corner {{
            background: {background_color};
            border: none;
        }}

        QLineEdit#search_widget_line_edit {{
            border: 1px solid {border_color};
            border-radius: 5px;
            padding: 5px;
            background-color: {button_background};
            color: {text_color};
            selection-background-color: {selection_background};
            selection-color: {selection_text_color};
        }}
        QLineEdit#search_widget_line_edit:hover {{
            background-color: {hover_background};
            border: 1px solid {highlight_border};
        }}
        QLineEdit#search_widget_line_edit:focus {{
            border: 1px solid {highlight_border};
            background-color: {focus_background};
        }}
    """


themes = {
    "Cherry Blossom": {
        "text_color": "#4E2A2A",
        "background_color": "#FFE0E6",
        "disabled_text_color": "#A68A8A",
        "disabled_background_color": "#FFD4DA",
        "border_color": "#E9A0A7",
        "hover_background": "#FFCCD3",
        "selection_background": "#E9A0A7",
        "selection_text_color": "#4E2A2A",
        "focus_background": "#FFD4DA",
        "highlight_border": "#E58A8F",
        "button_background": "#FFD4DA",
        "scrollbar_handle": "#E58A8F",
    },
    "Blue Ocean": {
        "text_color": "#FFFFFF",
        "background_color": "#1C3A5F",
        "disabled_text_color": "#8395A7",
        "disabled_background_color": "#2B4B7B",
        "border_color": "#4A69A0",
        "hover_background": "#2D4C7A",
        "selection_background": "#3B5C88",
        "selection_text_color": "#FFFFFF",
        "focus_background": "#243C65",
        "highlight_border": "#5A79B1",
        "button_background": "#2B4B7B",
        "scrollbar_handle": "#4A69A0",
    },
    "Red Rage": {
        "text_color": "#FFFFFF",
        "background_color": "#440000",
        "disabled_text_color": "#AA6666",
        "disabled_background_color": "#550000",
        "border_color": "#AA3333",
        "hover_background": "#660000",
        "selection_background": "#AA3333",
        "selection_text_color": "#FFFFFF",
        "focus_background": "#550000",
        "highlight_border": "#FF6666",
        "button_background": "#550000",
        "scrollbar_handle": "#AA3333",
    },
    "Soft Gray": {
        "text_color": "#333333",
        "background_color": "#F0F0F0",
        "disabled_text_color": "#A0A0A0",
        "disabled_background_color": "#E0E0E0",
        "border_color": "#C0C0C0",
        "hover_background": "#D0D0D0",
        "selection_background": "#B0B0B0",
        "selection_text_color": "#333333",
        "focus_background": "#E0E0E0",
        "highlight_border": "#A0A0A0",
        "button_background": "#E0E0E0",
        "scrollbar_handle": "#C0C0C0",
    },
}


class Themes:
    """This is automatically used, if you have more than one word like light_light, the first will be in parentheses.
    The only app styles there are are 'windowsvista', 'Windows' and 'Fusion' of which only the last two are unique.
    If light or dark are in your theme name ' Theme' will be added at the end. Also anything with leading or ending __
    will be filtered out."""
    modern = Theme(None, "Fusion", "os")
    chiseled = Theme(None, "Windows", "os")
    light = Theme("""
            QWidget {
                color: rgb(0, 0, 0);
                background-color: #f0f0f0;           
            }
            QWidget:disabled {
                color: rgb(127, 127, 127);
                background-color: #e0e0e0;
            }
            QWidget#transparentImage {
                background: transparent;
            }
            QWidget#sideMenu {
                background: rgb(232, 230, 230); /*#e8e6e6#ededed*/
            }
            QCheckBox{
                /*background-color: #e0e0e0;*/
                border-radius: 5px;           
            }
            QRadioButton{
                /*background-color: #e0e0e0;*/
                border-radius: 5px;           
            }
            QLabel {
                border-radius: 5px;
                padding: 5px;
                background-color: #d6d6d6; /*Before #d0d0d0, made it 6 lighter*/
            }
            ImageLabel {
                padding: 0;
                background-color: transparent;
            }
            QPushButton {
                border: 1px solid #808080;
                border-radius: 5px;
                padding: 5px;
                background-color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
            QToolButton {
                border: 1px solid #808080;
                border-radius: 5px;
                background-color: #e0e0e0;
            }
            QToolButton:hover {
                background-color: #c0c0c0;
            }
            /*QCheckBox::indicator:hover {
                background-color: rgba(192, 192, 192, 50);
            }*/
            QScrollBar:horizontal {
                border: none;
                background-color: transparent;
                height: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background-color: #aaaaaa;
                min-height: 15px;
                min-width: 40px;
                border-radius: 7px;
            }
            QScrollBar::handle:hover {
                background-color: #888888;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }

            QScrollBar:vertical {
                border: none;
                background-color: transparent;
                width: 15px;
                border-radius: 7px;
                /*border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;*/
            }
            QScrollBar::handle:vertical {
                background-color: #aaaaaa;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:hover {
                background-color: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar::corner {
                background: #f0f0f0;
                border: none;
            }
        """, "Fusion", "light")
    light_light = Theme("""
                QWidget {
                    color: rgb(0, 0, 0);
                    background-color: #f0f0f0;           
                }
                QWidget:disabled {
                    color: rgb(127, 127, 127);
                    background-color: #e0e0e0;
                }
                QComboBox {
                    border: 1px solid #808080;
                    border-radius: 5px;
                    padding: 5px;
                    background-color: #e0e0e0;
                    selection-background-color: #c0c0c0;
                    selection-color: black;
                }
                QComboBox::drop-down {
                    border: none;
                    background: transparent;
                }
                QComboBox::down-arrow {
                    image: url(data/arrow-down.png);
                }
                QComboBox QAbstractItemView {
                    border: 1px solid #808080;
                    background-color: #e0e0e0;
                    border-radius: 5px;
                    margin-top: -5px;
                }
                QCheckBox{
                    /*background-color: #e0e0e0;*/
                    border-radius: 5px;           
                }
                QLabel {
                    border-radius: 5px;
                    padding: 5px;
                    background-color: #d6d6d6; /*Before #d0d0d0, made it 6 lighter*/
                }
                ImageLabel {
                    padding: 0;
                    background-color: transparent;
                }
                QWidget#transparentImage {
                    background: transparent;
                }
                QPushButton {
                    border: 1px solid #808080;
                    border-radius: 5px;
                    padding: 5px;
                    background-color: #e0e0e0;
                }
                QPushButton:hover {
                    background-color: #c0c0c0;
                }
                QToolButton {
                    border: 1px solid #808080;
                    border-radius: 5px;
                    background-color: #e0e0e0;
                }
                QToolButton:hover {
                    background-color: #c0c0c0;
                }
                QScrollBar:horizontal {
                    border: none;
                    background-color: transparent;
                    height: 15px;
                    border-radius: 7px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #aaaaaa;
                    min-height: 15px;
                    min-width: 40px;
                    border-radius: 7px;
                }
                QScrollBar::handle:hover {
                    background-color: #888888;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    border: none;
                    background: none;
                }
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                    background: none;
                }

                QScrollBar:vertical {
                    border: none;
                    background-color: transparent;
                    width: 15px;
                    border-radius: 7px;
                    /*border-top-right-radius: 10px;
                    border-bottom-right-radius: 10px;*/
                }
                QScrollBar::handle:vertical {
                    background-color: #aaaaaa;
                    min-height: 20px;
                    border-radius: 7px;
                }
                QScrollBar::handle:hover {
                    background-color: #888888;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }

                QScrollBar::corner {
                    background: #f0f0f0;
                    border: none;
                }
                QLineEdit#search_widget_line_edit {
                    border: 1px solid #808080;
                    border-radius: 5px;
                    padding: 5px;
                    background-color: #e0e0e0;
                    selection-background-color: #c0c0c0;
                    selection-color: black;
                }
                QLineEdit#search_widget_line_edit:hover {
                    background-color: #c0c0c0; /* Darker background on hover */
                    border: 1px solid #888888;  /* Slightly darker border on hover */
                }
                QLineEdit#search_widget_line_edit:focus {
                    border: 1px solid #606060; /* Darker border on focus */
                    background-color: #d0d0d0; /* Softer gray background on focus */
                }
            """, None, "light")
    dark = Theme("""
            QWidget {
                color: rgb(255, 255, 255);
                background-color: #333333;
            }
            QWidget:disabled {
                color: rgb(127, 127, 127);
                background-color: #444444;
            }
            QWidget#transparentImage {
                background: transparent;
            }
            QWidget#sideMenu {
                background: #383838; /*Lighter color for the side menu background (#393939)*/
            }
            QCheckBox{
                /*background-color: #444444;*/
                border-radius: 5px;           
            }
            QRadioButton{
                /*background-color: #444444;*/
                border-radius: 5px;           
            }
            QLabel {
                border-radius: 5px;
                padding: 5px;
                background-color: #4f4f4f; /*Before #555555, made it 6 darker*/
            }
            ImageLabel {
                padding: 0;
                background-color: transparent;
            }
            QPushButton {
                border: 1px solid #aaaaaa;
                border-radius: 5px;
                padding: 5px;
                background-color: #444444;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QToolButton {
                border: 1px solid #aaaaaa;
                border-radius: 5px;
                background-color: #444444;
            }
            QToolButton:hover {
                background-color: #555555;
            }
            /*QCheckBox::indicator:hover {
                background-color: rgba(85, 85, 85, 50);
            }*/
            QScrollBar:horizontal {
                border: none;
                background: transparent;  /* Ensure the background is transparent */
                height: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background-color: #666666;
                min-height: 15px;
                min-width: 40px;
                border-radius: 7px;
            }
            QScrollBar::handle:hover {
                background-color: #555555;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }

            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 15px;
                border-radius: 7px;
                /*border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;*/
            }
            QScrollBar::handle:vertical {
                background: #666666;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                border: none;
                background: none;
            }

            QScrollBar::corner {
                background: #f0f0f0;
                border: none;
            }
        """, "Fusion", "dark")
    light_dark = Theme("""
            QWidget {
                color: rgb(255, 255, 255);
                background-color: #333333;
            }
            QWidget:disabled {
                color: rgb(127, 127, 127);
                background-color: #444444;
            }
            QComboBox {
                border: 1px solid #808080;
                border-radius: 5px;
                padding: 5px;
                background-color: #444444;
                selection-background-color: #555555;
                selection-color: white;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url(data/arrow-down.png);
            }
            QComboBox QAbstractItemView {
                border: 1px solid #808080;
                background-color: #444444;
                border-radius: 5px;
                margin-top: -5px;
            }
            QCheckBox{
                border-radius: 5px;           
            }
            QLabel {
                border-radius: 5px;
                padding: 5px;
                background-color: #555555;
            }
            ImageLabel {
                padding: 0;
                background-color: transparent;
            }
            QWidget#transparentImage {
                background: transparent;
            }
            QPushButton {
                border: 1px solid #aaaaaa;
                border-radius: 5px;
                padding: 5px;
                background-color: #444444;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QToolButton {
                border: 1px solid #aaaaaa;
                border-radius: 5px;
                background-color: #444444;
            }
            QToolButton:hover {
                background-color: #555555;
            }
            QScrollBar:horizontal {
                border: none;
                background-color: transparent;
                height: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background-color: #666666;
                min-height: 15px;
                min-width: 40px;
                border-radius: 7px;
            }
            QScrollBar::handle:hover {
                background-color: #555555;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }

            QScrollBar:vertical {
                border: none;
                background-color: transparent;
                width: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:hover {
                background-color: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar::corner {
                background: #333333;
                border: none;
            }
            QLineEdit#search_widget_line_edit {
                border: 1px solid #808080;
                border-radius: 5px;
                padding: 5px;
                background-color: #444444;          /* Darker background color */
                color: rgb(255, 255, 255);          /* White text */
                selection-background-color: #555555; /* Dark selection background */
                selection-color: white;             /* White selection text color */
            }
            QLineEdit#search_widget_line_edit:hover {
                background-color: #555555;          /* Slightly darker background on hover */
                border: 1px solid #aaaaaa;          /* Lighter border on hover */
            }
            QLineEdit#search_widget_line_edit:focus {
                border: 1px solid #aaaaaa;          /* Light border on focus */
                background-color: #333333;          /* Even darker background on focus */
            }
        """, None, "dark")
    dynamic = DynamicTheme("""
        QWidget {{
            color: {text_color};
            background-color: {base_color};           
        }}
        QWidget:disabled {{
            color: {disabled_text_color};
            background-color: {disabled_bg_color};
        }}
        QWidget#transparentImage {{
            background: transparent;
        }}
        QWidget#sideMenu {{
            background: {base_color}; /* Previously #e8e6e6#ededed */
        }}
        QCheckBox{{
            background-color: {alternate_base_color};
            border-radius: 5px;           
        }}
        QRadioButton{{
            /*background-color: {base_color};*/
            border-radius: 5px;           
        }}
        QLabel {{
            border-radius: 5px;
            padding: 5px;
            background-color: {alternate_base_color}; /* Before #d6d6d6 */
        }}
        ImageLabel {{
            padding: 0;
            background-color: transparent;
        }}
        QPushButton {{
            border: 1px solid {normal_border};
            border-radius: 5px;
            padding: 5px;
            background-color: {base_color};
        }}
        QPushButton:hover {{
            background-color: {alternate_base_color};
        }}
        QToolButton {{
            border: 1px solid {normal_border};
            border-radius: 5px;
            background-color: {base_color};
        }}
        QToolButton:hover {{
            background-color: {alternate_base_color};
        }}
        /*QCheckBox::indicator:hover {{
            background-color: rgba(192, 192, 192, 50);
        }}*/
        QScrollBar:horizontal {{
            border: none;
            background-color: transparent;
            height: 15px;
            border-radius: 7px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {mid_color};
            min-height: 15px;
            min-width: 40px;
            border-radius: 7px;
        }}
        QScrollBar::handle:hover {{
            background-color: {dark_color};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    
        QScrollBar:vertical {{
            border: none;
            background-color: transparent;
            width: 15px;
            border-radius: 7px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {mid_color};
            min-height: 20px;
            border-radius: 7px;
        }}
        QScrollBar::handle:hover {{
            background-color: {dark_color};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
    
        QScrollBar::corner {{
            background: {window_color};
            border: none;
        }}
    """, "Fusion", "os")
    light_dynamic = DynamicTheme("""
            QWidget {{
                color: {text_color};
                background-color: {window_color};           
            }}
            QWidget:disabled {{
                color: {disabled_text_color};
                background-color: {disabled_bg_color};
            }}
            QComboBox {{
                border: 1px solid {mid_color};
                border-radius: 5px;
                padding: 5px;
                background-color: {base_color};
                selection-background-color: {highlight_color};
                selection-color: {highlighted_text_color};
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url(data/arrow-down.png);
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {mid_color};
                background-color: {base_color};
                border-radius: 5px;
                margin-top: -5px;
            }}
            QCheckBox {{
                border-radius: 5px;           
            }}
            QLabel {{
                border-radius: 5px;
                padding: 5px;
                background-color: {alternate_base_color};
            }}
            ImageLabel {{
                padding: 0;
                background-color: transparent;
            }}
            QWidget#transparentImage {{
                background: transparent;
            }}
            QPushButton {{
                border: 1px solid {mid_color};
                border-radius: 5px;
                padding: 5px;
                background-color: {base_color};
            }}
            QPushButton:hover {{
                background-color: {highlight_color};
            }}
            QToolButton {{
                border: 1px solid {mid_color};
                border-radius: 5px;
                background-color: {base_color};
            }}
            QToolButton:hover {{
                background-color: {highlight_color};
            }}
            QScrollBar:horizontal {{
                border: none;
                background-color: transparent;
                height: 15px;
                border-radius: 7px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {mid_color};
                min-height: 15px;
                min-width: 40px;
                border-radius: 7px;
            }}
            QScrollBar::handle:hover {{
                background-color: {dark_color};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
            
            QScrollBar:vertical {{
                border: none;
                background-color: transparent;
                width: 15px;
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {mid_color};
                min-height: 20px;
                border-radius: 7px;
            }}
            QScrollBar::handle:hover {{
                background-color: {dark_color};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            
            QScrollBar::corner {{
                background: {window_color};
                border: none;
            }}
            QLineEdit#search_widget_line_edit {{
                border: 1px solid {mid_color};
                border-radius: 5px;
                padding: 5px;
                background-color: {base_color};
                selection-background-color: {highlight_color};
                selection-color: {highlighted_text_color};
            }}
            QLineEdit#search_widget_line_edit:hover {{
                background-color: {alternate_base_color};
                border: 1px solid {light_color};  
            }}
            QLineEdit#search_widget_line_edit:focus {{
                border: 1px solid {dark_color};
                background-color: {alternate_base_color};
            }}
        """, None, "os")
    custom_my_theme = Theme(None, None, "os")
    customlight_cherry_blossom = Theme(generate_theme_stylesheet(**themes["Cherry Blossom"]), None, "light")
    customlight_blue_ocean = Theme(generate_theme_stylesheet(**themes["Blue Ocean"]), None, "dark")
    customlight_red_rage = Theme(generate_theme_stylesheet(**themes["Red Rage"]), None, "dark")
    customlight_soft_gray = Theme(generate_theme_stylesheet(**themes["Soft Gray"]), None, "light")
