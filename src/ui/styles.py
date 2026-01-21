"""
ttk 스타일 설정 모듈
- setup_styles(): 스타일 초기화
- STYLES: 스타일 상수
"""

from tkinter import ttk
from ..config import COLORS


# 스타일 이름 상수
STYLES = {
    'MAIN_FRAME': 'Main.TFrame',
    'CARD_FRAME': 'Card.TFrame',
    'ELEVATED_FRAME': 'Elevated.TFrame',
    'TITLE_LABEL': 'Title.TLabel',
    'SUBTITLE_LABEL': 'Subtitle.TLabel',
    'CARD_LABEL': 'Card.TLabel',
    'CARD_TITLE_LABEL': 'CardTitle.TLabel',
    'STATUS_LABEL': 'Status.TLabel',
    'ACCENT_BUTTON': 'Accent.TButton',
    'NAV_BUTTON': 'Nav.TButton',
    'ICON_BUTTON': 'Icon.TButton',
    'TOOL_BUTTON': 'Tool.TButton',
    'TOOL_ACTIVE_BUTTON': 'ToolActive.TButton',
    'REPORT_TREEVIEW': 'Report.Treeview',
    'SEARCH_ENTRY': 'Search.TEntry',
    'CUSTOM_SCROLLBAR': 'Custom.Vertical.TScrollbar',
}


def setup_styles(colors: dict = None) -> ttk.Style:
    """
    ttk 스타일 설정 - 모던 다크 테마

    Args:
        colors: 색상 딕셔너리 (None이면 기본 COLORS 사용)

    Returns:
        ttk.Style 객체
    """
    if colors is None:
        colors = COLORS

    style = ttk.Style()
    style.theme_use('clam')

    # 메인 프레임 스타일
    style.configure('Main.TFrame', background=colors['bg_dark'])
    style.configure('Card.TFrame', background=colors['bg_card'])
    style.configure('Elevated.TFrame', background=colors['bg_elevated'])

    # 레이블 스타일
    style.configure('Title.TLabel',
                    background=colors['bg_dark'],
                    foreground=colors['text_primary'],
                    font=('Segoe UI', 22, 'bold'))

    style.configure('Subtitle.TLabel',
                    background=colors['bg_dark'],
                    foreground=colors['text_secondary'],
                    font=('Segoe UI', 10))

    style.configure('Card.TLabel',
                    background=colors['bg_card'],
                    foreground=colors['text_primary'],
                    font=('Segoe UI', 10))

    style.configure('CardTitle.TLabel',
                    background=colors['bg_card'],
                    foreground=colors['accent'],
                    font=('Segoe UI', 12, 'bold'))

    style.configure('Status.TLabel',
                    background=colors['bg_dark'],
                    foreground=colors['success'],
                    font=('Segoe UI', 10, 'bold'))

    # 버튼 스타일
    style.configure('Accent.TButton',
                    background=colors['accent'],
                    foreground='white',
                    font=('Segoe UI', 10, 'bold'),
                    padding=(20, 12),
                    borderwidth=0)
    style.map('Accent.TButton',
              background=[('active', colors['accent_hover']),
                          ('pressed', colors['highlight'])])

    style.configure('Nav.TButton',
                    background=colors['bg_elevated'],
                    foreground=colors['text_primary'],
                    font=('Segoe UI', 9),
                    padding=(12, 8),
                    borderwidth=0)
    style.map('Nav.TButton',
              background=[('active', colors['border']),
                          ('pressed', colors['bg_card'])])

    style.configure('Icon.TButton',
                    background=colors['bg_elevated'],
                    foreground=colors['text_primary'],
                    font=('Segoe UI', 11),
                    padding=(8, 6),
                    borderwidth=0)
    style.map('Icon.TButton',
              background=[('active', colors['border'])])

    # 툴 버튼 스타일 (활성화/비활성화)
    style.configure('Tool.TButton',
                    background=colors['bg_elevated'],
                    foreground=colors['text_primary'],
                    font=('Segoe UI', 10),
                    padding=(10, 6),
                    borderwidth=0)
    style.map('Tool.TButton',
              background=[('active', colors['border']),
                          ('pressed', colors['bg_card'])])

    style.configure('ToolActive.TButton',
                    background=colors['warning'],
                    foreground='#000000',
                    font=('Segoe UI', 10, 'bold'),
                    padding=(10, 6),
                    borderwidth=0)
    style.map('ToolActive.TButton',
              background=[('active', '#e6ac00')])

    # Treeview 스타일
    style.configure('Report.Treeview',
                    background=colors['bg_card'],
                    foreground=colors['text_primary'],
                    fieldbackground=colors['bg_card'],
                    font=('Segoe UI', 9),
                    rowheight=32,
                    borderwidth=0)

    style.configure('Report.Treeview.Heading',
                    background=colors['bg_elevated'],
                    foreground=colors['text_secondary'],
                    font=('Segoe UI', 9, 'bold'),
                    borderwidth=0,
                    relief='flat')

    style.map('Report.Treeview',
              background=[('selected', colors['highlight'])],
              foreground=[('selected', colors['text_primary'])])

    style.map('Report.Treeview.Heading',
              background=[('active', colors['border'])])

    # Entry 스타일
    style.configure('Search.TEntry',
                    fieldbackground=colors['bg_elevated'],
                    foreground=colors['text_primary'],
                    insertcolor=colors['text_primary'],
                    borderwidth=0,
                    padding=(10, 8))

    # Scrollbar 스타일
    style.configure('Custom.Vertical.TScrollbar',
                    background=colors['bg_card'],
                    troughcolor=colors['bg_card'],
                    borderwidth=0,
                    arrowsize=0)
    style.map('Custom.Vertical.TScrollbar',
              background=[('active', colors['border'])])

    return style
