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

# 자동 하이라이트 카테고리별 색상
AUTO_HIGHLIGHT_CATEGORY_COLORS = {
    'target':    '#FFFF66',  # 노란색 - 목표주가/투자의견
    'financial': '#90EE90',  # 연한 초록 - 실적/재무 수치
    'growth':    '#87CEEB',  # 하늘색 - 성장 동력/긍정 요인
    'risk':      '#FFB6C1',  # 분홍 - 리스크/부정 요인
}

# 자동 하이라이트 카테고리별 라벨 (UI/로그용)
AUTO_HIGHLIGHT_CATEGORY_LABELS = {
    'target':    '목표주가/투자의견',
    'financial': '실적/재무',
    'growth':    '성장 동력',
    'risk':      '리스크',
}

# 자동 하이라이트 투명도 (수동: 77, 자동은 약간 진하게)
AUTO_HIGHLIGHT_ALPHA = 100

# 자동 하이라이트 카테고리별 정규식 패턴 (한국 증권 리포트 어휘)
AUTO_HIGHLIGHT_CATEGORIES = {
    'target': [
        r'목표주가\s*[:：]?\s*[\d,]+\s*원',
        r'적정주가\s*[:：]?\s*[\d,]+\s*원',
        r'투자의견\s*[:：]?\s*(매수|Buy|BUY|보유|Hold|HOLD|매도|Sell|SELL|중립|Neutral)',
        r'(상향|하향)\s*조정',
        r'목표주가\s*(상향|하향)',
        r'TP\s*[:：]?\s*[\d,]+',
    ],
    'financial': [
        r'(매출액?|영업이익|당기순이익|순이익|EPS|PER|ROE|PBR|EBITDA|영업이익률)\s*[:：은는이가]*\s*[\d,\.]+\s*(원|억원?|조원?|%|배)',
        r'(YoY|QoQ|전년\s*대비|전분기\s*대비)\s*[+\-]?\s*\d+\.?\d*\s*%',
        r'[\+\-]?\s*\d+\.?\d*\s*%\s*(증가|감소|성장|하락|상승)',
    ],
    'growth': [
        r'(신사업|신제품|신규\s*고객|수혜|성장\s*동력|모멘텀|점유율\s*(상승|확대)|시장\s*확대|판매\s*호조|수요\s*증가)',
        r'(역대\s*최대|사상\s*최고|컨센서스\s*상회|기대\s*이상)',
    ],
    'risk': [
        r'(리스크|위험\s*요인|우려|하방|부정적|둔화|역성장|규제\s*(리스크|강화))',
        r'(컨센서스\s*하회|기대\s*이하|불확실성|악화|부진)',
    ],
}

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

# PDF 다운로드 허용 도메인 목록
ALLOWED_PDF_DOMAINS = [
    'ssl.pstatic.net',
    'stock.pstatic.net',
    'finance.naver.com',
    'imgstock.naver.com',
]
