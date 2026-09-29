"""Read existing abstracts from OpenAlex; no LLM client or generated text."""
import logging
import re
import requests as _requests

logger = logging.getLogger(__name__)
MIN_ABSTRACT_LENGTH = 50
NO_ABSTRACT_PLACEHOLDERS = [
    "초록(Abstract) 정보가 제공되지 않았습니다.", "초록 정보가 없습니다.",
    "No abstract available",
]

def _fetch_abstract_openalex(doi):
    """DOI를 이용해 OpenAlex API에서 Abstract를 가져옵니다."""
    if not doi:
        return None
    try:
        # DOI에서 URL 부분만 추출 (이미 full URL인 경우 대응)
        if doi.startswith("http"):
            openalex_url = f"https://api.openalex.org/works/{doi}"
        else:
            openalex_url = f"https://api.openalex.org/works/https://doi.org/{doi}"

        resp = _requests.get(openalex_url, timeout=10,
                             headers={"User-Agent": "AcademicResearchBot/1.0"})
        if resp.status_code != 200:
            return None

        data = resp.json()

        # OpenAlex는 inverted_abstract_index 형태로 Abstract를 제공
        inv_index = data.get("abstract_inverted_index")
        if inv_index:
            # inverted index → 원문 재구성
            word_positions = []
            for word, positions in inv_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort(key=lambda x: x[0])
            abstract = " ".join(w for _, w in word_positions)
            if abstract and len(abstract) > MIN_ABSTRACT_LENGTH:
                logger.info(f"🔄 OpenAlex fallback 성공: {len(abstract)}자 Abstract 확보")
                return abstract

    except Exception as e:
        logger.warning(f"OpenAlex fallback 실패: {e}")
    return None


def enrich_abstract(abstract, doi):
    """
    Abstract가 없거나 너무 짧으면 OpenAlex에서 보완합니다.

    Args:
        abstract: Crossref에서 가져온 원본 Abstract 문자열
        doi: 논문의 DOI (URL 형태도 가능)

    Returns:
        보완된 Abstract 문자열
    """
    # 기본 placeholder인지 확인
    is_placeholder = any(ph in (abstract or "") for ph in NO_ABSTRACT_PLACEHOLDERS)
    is_too_short = len(abstract or "") < MIN_ABSTRACT_LENGTH

    if is_placeholder or is_too_short:
        logger.info(f"⚠️ Abstract 부족 ({len(abstract or '')}자) — OpenAlex fallback 시도...")
        openalex_abstract = _fetch_abstract_openalex(doi)
        if openalex_abstract:
            # HTML 태그 제거
            return re.sub(r'<[^>]+>', '', openalex_abstract).strip()
        else:
            logger.warning("OpenAlex에서도 Abstract를 찾지 못했습니다.")
    return abstract or "초록(Abstract) 정보가 제공되지 않았습니다."


