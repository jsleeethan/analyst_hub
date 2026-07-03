"""
자동 하이라이트 모듈
- 투자자 관점에서 중요한 부분을 카테고리별로 식별
- 룰 기반 (정규식/키워드) + LLM 기반 (옵션) 지원
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from .config import (
    AUTO_HIGHLIGHT_CATEGORIES,
    AUTO_HIGHLIGHT_CATEGORY_COLORS,
    AUTO_HIGHLIGHT_ALPHA,
)

logger = logging.getLogger(__name__)


@dataclass
class HighlightSpan:
    """자동 하이라이트 대상 텍스트 스팬"""
    category: str          # 'target' | 'financial' | 'growth' | 'risk'
    snippet: str           # PDF에서 search_for로 다시 찾을 텍스트
    color: str
    alpha: int = AUTO_HIGHLIGHT_ALPHA


class AutoHighlighter:
    """투자자 관점 자동 하이라이트 분석기"""

    def __init__(self):
        # 패턴 컴파일 (성능)
        self._compiled: Dict[str, List[re.Pattern]] = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in AUTO_HIGHLIGHT_CATEGORIES.items()
        }

    def analyze_with_rules(self, page_blocks_or_text) -> List[HighlightSpan]:
        """
        단락(block) 단위 분석. 단락 내 어떤 라인이라도 패턴에 매칭되면
        그 단락의 모든 라인을 같은 카테고리 색상으로 하이라이트.

        이를 통해 한 문장이 여러 줄로 줄바꿈된 경우에도 연속된 줄이 모두 색칠됨.

        Args:
            page_blocks_or_text:
                - List[str]: PDFHandler.get_page_blocks() 결과 (권장)
                - str: 페이지 전체 텍스트 (fallback — \n\n 단위로 단락 분할)

        Returns:
            HighlightSpan 리스트 (카테고리별 색상 적용됨)
        """
        # 입력 정규화
        if isinstance(page_blocks_or_text, str):
            if not page_blocks_or_text:
                return []
            blocks = [b for b in re.split(r'\n\s*\n', page_blocks_or_text) if b.strip()]
        else:
            blocks = [b for b in (page_blocks_or_text or []) if b and b.strip()]

        if not blocks:
            return []

        spans: List[HighlightSpan] = []
        seen_lines: set = set()

        for block_text in blocks:
            lines = [l.strip() for l in block_text.split('\n') if l.strip()]
            if not lines:
                continue

            # 단락 단위로 카테고리 결정 (우선순위 기반)
            category = self._classify_block(lines)
            if not category:
                continue

            # 단락 내 모든 라인을 동일 카테고리 색상으로 하이라이트
            for line in lines:
                if line in seen_lines:
                    continue
                # 너무 짧거나 너무 긴 라인은 제외 (search_for 적중률 + 노이즈)
                if len(line) < 4 or len(line) > 200:
                    continue
                seen_lines.add(line)
                spans.append(HighlightSpan(
                    category=category,
                    snippet=line,
                    color=AUTO_HIGHLIGHT_CATEGORY_COLORS[category],
                    alpha=AUTO_HIGHLIGHT_ALPHA,
                ))

        logger.info(f"룰 기반 분석 완료: {len(blocks)}개 단락 → {len(spans)}개 스팬 발견")
        if logger.isEnabledFor(logging.DEBUG):
            for s in spans:
                logger.debug(f"  [{s.category}] {s.snippet[:60]}")
        return spans

    def _classify_block(self, lines: List[str]) -> Optional[str]:
        """
        단락의 라인들을 종합해서 카테고리 결정.
        우선순위 순으로 검사 — 한 단락에 여러 카테고리가 섞여 있어도
        가장 중요한 카테고리 하나로 통일하여 색상 일관성 유지.
        """
        priority_order = ['target', 'risk', 'financial', 'growth']
        for category in priority_order:
            for line in lines:
                for pattern in self._compiled[category]:
                    if pattern.search(line):
                        return category
        return None

    def _classify_line(self, line: str) -> Optional[str]:
        """단일 라인 분류 (LLM 결과 검증 등에 사용)"""
        return self._classify_block([line])

    def analyze_with_llm(self, page_text: str, llm_client,
                          report_meta: Optional[dict] = None) -> List[HighlightSpan]:
        """
        Claude API를 사용한 의미 기반 분석.

        Args:
            page_text: 페이지 텍스트
            llm_client: LLMClient 인스턴스 (None이거나 unavailable이면 빈 리스트)
            report_meta: {'stock', 'firm', 'opinion', 'target'} 등 메타정보

        Returns:
            HighlightSpan 리스트. 실패 시 빈 리스트(룰 기반으로 graceful fallback).
        """
        if not page_text or llm_client is None or not llm_client.available:
            return []

        try:
            results = llm_client.extract_highlights(page_text, report_meta or {})
        except Exception as e:
            logger.error(f"LLM 분석 실패: {e}")
            return []

        spans: List[HighlightSpan] = []
        for item in results:
            category = item.get('category')
            snippet = item.get('snippet', '').strip()
            if category not in AUTO_HIGHLIGHT_CATEGORY_COLORS or not snippet:
                continue
            if len(snippet) < 4 or len(snippet) > 200:
                continue
            spans.append(HighlightSpan(
                category=category,
                snippet=snippet,
                color=AUTO_HIGHLIGHT_CATEGORY_COLORS[category],
                alpha=AUTO_HIGHLIGHT_ALPHA,
            ))

        logger.info(f"LLM 분석 완료: {len(spans)}개 스팬 발견")
        return spans
