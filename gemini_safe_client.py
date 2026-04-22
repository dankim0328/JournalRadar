"""
gemini_safe_client.py — Gemini API 안전 래퍼 모듈

5가지 안전장치를 통합하여 하나의 인터페이스로 제공합니다:
1. Exponential Backoff (429/503 에러 시 재시도 간격 기하급수 증가, 최대 3회)
2. 입력 페이로드 최적화 (텍스트 8,000자 제한 + 변수 초기화)
3. API 호출 속도 제한 (각 호출 사이 최소 3초 강제 sleep)
4. 로컬 캐싱 (JSON 파일에 결과 저장, 중복 API 호출 방지)
5. OpenAlex Fallback (Crossref Abstract 누락/부족 시 OpenAlex에서 보완)
"""

import os
import re
import json
import time
import hashlib
import logging

import requests as _requests
import google.generativeai as genai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)

# ─── 로깅 설정 ───
logger = logging.getLogger("gemini_safe_client")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ─── 상수 ───
MAX_TEXT_LENGTH = 8000          # Abstract 등 텍스트 최대 글자 수
MIN_CALL_INTERVAL_SEC = 3      # API 호출 사이 최소 대기 시간(초)
MIN_ABSTRACT_LENGTH = 50       # Abstract 최소 유효 길이 (이하이면 OpenAlex fallback)
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_cache.json")
FAILURE_MARKERS = ["AI 분석 실패", "AI Analysis Failed", "AI 백필 분석 실패"]
NO_ABSTRACT_PLACEHOLDERS = [
    "초록(Abstract) 정보가 제공되지 않았습니다.",
    "초록 정보가 없습니다.",
    "No abstract available",
]

# ─── 환각 방지 프롬프트 (모든 분석 프롬프트에 공통 삽입) ───
ANTI_HALLUCINATION_INSTRUCTION = """[환각 방지 - 필수 준수 사항]
제공된 Abstract 데이터가 없거나, 내용이 너무 부족해서 구체적인 연구 방법론(예: 구조적 모형, 계량경제학적 추정 방식 등)이나 결론을 파악할 수 없다면, 절대로 내용을 추측하거나 지어내지(Hallucinate) 마라. 대신 해당 항목에 [초록 정보 부족으로 분석 불가]라고만 출력해라."""

# ─── 안전 설정 (모든 호출에 공통 적용) ───
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]


# ─── 5. OpenAlex Fallback ───
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


# ─── 1. 입력 페이로드 최적화 ───
def truncate_text(text, max_length=MAX_TEXT_LENGTH):
    """텍스트를 최대 길이로 절단합니다. 초과 시 경고 로그를 출력합니다."""
    if not text:
        return text
    if len(text) <= max_length:
        return text
    logger.warning(f"텍스트 절단: {len(text)}자 → {max_length}자")
    return text[:max_length] + "..."


# ─── 2. 재시도 가능 여부 판별 ───
def _is_retryable_error(exception):
    """429 (ResourceExhausted) 또는 503 (ServiceUnavailable) 에러인지 확인합니다."""
    error_str = str(exception).lower()
    # google.api_core.exceptions 또는 일반 HTTP 에러 메시지 탐지
    retryable_keywords = [
        "429", "resource exhausted", "resourceexhausted",
        "503", "service unavailable", "serviceunavailable",
        "too many requests", "quota",
    ]
    return any(keyword in error_str for keyword in retryable_keywords)


# ─── 3. 로컬 캐시 ───
class GeminiCache:
    """JSON 파일 기반 로컬 캐시. 논문 제목의 MD5 해시를 키로 사용합니다."""

    def __init__(self, cache_file=CACHE_FILE):
        self.cache_file = cache_file
        self._cache = {}
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"캐시 로드 완료: {len(self._cache)}건")
            except (json.JSONDecodeError, IOError):
                logger.warning("캐시 파일 손상 — 빈 캐시로 시작합니다.")
                self._cache = {}

    def _save(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"캐시 저장 실패: {e}")

    @staticmethod
    def make_key(title):
        """논문 제목에서 캐시 키(MD5 해시)를 생성합니다."""
        normalized = title.strip().lower()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def get(self, title):
        """캐시에서 결과를 조회합니다. 없으면 None을 반환합니다."""
        key = self.make_key(title)
        result = self._cache.get(key)
        if result:
            # 실패 결과가 캐시에 있다면 무시
            if any(marker in result for marker in FAILURE_MARKERS):
                return None
            logger.info(f"🟢 캐시 히트: {title[:50]}...")
        return result

    def put(self, title, result):
        """결과를 캐시에 저장합니다. 실패 결과는 저장하지 않습니다."""
        if any(marker in result for marker in FAILURE_MARKERS):
            return
        key = self.make_key(title)
        self._cache[key] = result
        self._save()


# ─── 4. 안전 클라이언트 ───
class GeminiSafeClient:
    """Gemini API 안전 래퍼. 4가지 안전장치가 모두 적용됩니다."""

    def __init__(self, model_name="gemini-2.5-flash", api_key=None):
        api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=model_name)
        self.cache = GeminiCache()
        self._last_call_time = 0

    def _rate_limit_wait(self):
        """마지막 API 호출 이후 최소 대기 시간을 보장합니다."""
        elapsed = time.time() - self._last_call_time
        if elapsed < MIN_CALL_INTERVAL_SEC:
            wait_time = MIN_CALL_INTERVAL_SEC - elapsed
            logger.info(f"⏳ Rate limit 대기: {wait_time:.1f}초")
            time.sleep(wait_time)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception(_is_retryable_error),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call_api(self, prompt):
        """실제 API 호출. tenacity 데코레이터로 exponential backoff가 적용됩니다."""
        self._rate_limit_wait()
        self._last_call_time = time.time()
        
        # 비용 및 답변 폭주 통제를 위한 파라미터 적용
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=1000,
            temperature=0.2
        )
        
        response = self.model.generate_content(
            prompt, 
            safety_settings=SAFETY_SETTINGS,
            generation_config=generation_config
        )
        return response.text

    def analyze(self, prompt, cache_key_title=None):
        """
        Gemini API를 안전하게 호출합니다.

        Args:
            prompt: Gemini에 전송할 전체 프롬프트 문자열
            cache_key_title: 캐시 키로 사용할 논문 제목 (None이면 캐시 미사용)

        Returns:
            API 응답 텍스트 또는 실패 문자열
        """
        # 캐시 확인
        if cache_key_title:
            cached = self.cache.get(cache_key_title)
            if cached:
                return cached

        # API 호출 (backoff + rate limiting 적용)
        try:
            result = self._call_api(prompt)
            if not result:
                result = "===KOREAN===\nAI 분석 실패.\n===ENGLISH===\nAI Analysis Failed."
        except Exception as e:
            logger.error(f"❌ API 호출 최종 실패 (3회 재시도 후): {e}")
            result = "===KOREAN===\nAI 분석 실패.\n===ENGLISH===\nAI Analysis Failed."

        # 캐시 저장 (성공 시에만)
        if cache_key_title:
            self.cache.put(cache_key_title, result)

        return result
