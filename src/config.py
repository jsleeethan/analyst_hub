"""
설정값 모듈
- 색상 팔레트, URL 상수, PDF 렌더링 설정 등
"""

# 색상 팔레트 (다크 테마)
COLORS = {
    'bg_dark': '#0d1117',
    'bg_card': '#161b22',
    'bg_elevated': '#21262d',
    'border': '#30363d',
    'text_primary': '#f0f6fc',
    'text_secondary': '#8b949e',
    'text_muted': '#6e7681',
    'accent': '#58a6ff',
    'accent_hover': '#79c0ff',
    'success': '#3fb950',
    'warning': '#d29922',
    'danger': '#f85149',
    'highlight': '#388bfd',
    'highlighter': '#FFFF00',
}

# URL 상수
NAVER_BASE_URL = "https://finance.naver.com"
RESEARCH_URL = "https://finance.naver.com/research/"

# HTTP 헤더
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://finance.naver.com/'
}

# PDF 렌더링 설정
PDF_RENDER_SCALE = 1.5  # 150% 스케일
ZOOM_MIN = 0.5
ZOOM_MAX = 2.0
ZOOM_STEP = 0.25

# 어노테이션 설정
HIGHLIGHT_COLORS = ['#FFFF00', '#00FF00', '#FF69B4', '#00FFFF', '#FFA500']
LINE_COLORS = ['#FF0000', '#0000FF', '#00AA00', '#FF6600', '#000000']
DEFAULT_HIGHLIGHT_COLOR = '#FFFF00'
DEFAULT_LINE_COLOR = '#FF0000'

# 투명도 옵션 (PIL alpha 값, 0-255)
TRANSPARENCY_OPTIONS = [
    ('30%', 77),    # 30% 불투명
    ('50%', 128),   # 50% 불투명
    ('70%', 179),   # 70% 불투명
]
DEFAULT_ALPHA = 77  # 기본값: 30% 불투명

# 라인 굵기 옵션
LINE_WIDTH_OPTIONS = [2, 3, 5, 8]
DEFAULT_LINE_WIDTH = 3

# 창 설정
WINDOW_TITLE = "네이버 증권 종목 리포트 뷰어"
WINDOW_GEOMETRY = "1650x1000"
WINDOW_MIN_SIZE = (1400, 800)

# 스크래핑 설정
MAX_PAGES_TO_FETCH = 5
REQUEST_TIMEOUT = 10
PDF_DOWNLOAD_TIMEOUT = 30

# BeautifulSoup 파서 선택
try:
    import lxml
    PARSER = 'lxml'
except ImportError:
    PARSER = 'html.parser'
