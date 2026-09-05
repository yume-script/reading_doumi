# -*- coding: utf-8 -*-
"""
reading_doumi.py -- 화면 우측 하단에 캐릭터를 띄워두고, 클릭하면 채팅창이 열려
LLM과 대화하듯 내 서재의 책을 추천받거나, 책 목록/저자/서평(줄거리)을 물어볼 수
있는 "오버레이 마스코트" 샘플 플러그인.

- BookOasis 코어에는 "부팅 시 페이지 전역에 무언가를 주입하는" 훅이 없다. 그래서
  이 마스코트는 사이드바의 category_tab(전용 탭)을 사용자가 최초 1회 열 때
  script.js가 실행되면서 마운트되고, spotify_mood 샘플의 플로팅 플레이어와 동일한
  방식으로 자기 자신을 #library-plugin-custom-view 밖(document.body)에 옮겨 붙여서
  다른 탭으로 이동해도 계속 화면에 남아있게 만든다. 이 한계(세션 중 탭을 한 번도
  열지 않으면 마스코트도 뜨지 않음)는 docs 가이드에 명시했다.
- LLM 호출은 반드시 서버(이 파일)에서만 한다. API 키를 프론트엔드로 절대 내려주지
  않는다 (get_dashboard_data()가 유일한 백엔드 진입점이라 자연히 그렇게 됨).
- config_schema로 어떤 OpenAI 호환 채팅 API든(OpenAI, 로컬 Ollama/LM Studio,
  자체 게이트웨이 등) BASE_URL만 바꿔서 붙일 수 있게 했다.

- 모듈 전역 상수는 다른 플러그인 모듈과 이름이 겹치지 않도록 YM_ 접두사를 붙였다.

- 책 목록/저자/서평 검색: 사용자 메시지에서 검색어를 뽑아 books 테이블에서
  제목/저자/서평(줄거리)/장르 컬럼을 직접 LIKE 검색해서 최우선 근거로 LLM에게
  준다. 서평/평점/장르/시리즈 컬럼명은 메타데이터 프로바이더마다 다를 수 있어
  PRAGMA로 실제 스키마를 조회해서 있는 컬럼만 골라 쓴다 (_inspect_book_columns).
- 페르소나 프롬프트: config_schema의 SYSTEM_PROMPT 항목으로 설정 화면에서 직접
  저장할 수 있다. 비워두고 저장하거나 아예 저장하지 않으면
  YM_DEFAULT_SYSTEM_PROMPT(코드에 내장된 기본 프롬프트)를 그대로 쓴다.

- 독서 상태(/읽는중,/완독,/읽을예정,/상태), 평점/장르 필터, 채팅 히스토리 영구
  저장, 랜덤 추천(/랜덤), 서재 통계(/통계,/시리즈)를 지원한다 - 전부 "/명령어"나
  자연어 트리거로 LLM 호출 없이 코드에서 바로 처리한다.

- (신규) 다른 BookOasis 플러그인과의 연동:
    1) unified_book 연동: 서재 검색 결과가 없을 때(또는 /외부검색 명령) 같은
       BookOasis 인스턴스의 unified_book 플러그인(BaseMetadataProvider 계약의
       search(db_type, query))을 직접 호출해서 "서재엔 없지만 외부(교보문고/
       리디북스/알라딘 등 unified_book이 통합 검색하는 소스)에서 찾았어요"
       식으로 답할 수 있게 근거를 얹어준다.
    2) cover_quiz 연동: 심심하다/퀴즈/게임 같은 표현이나 /퀴즈 명령에 "책표지
       퀴즈" 탭을 자연스럽게 추천한다 (cover_quiz는 독립된 category_tab UI라
       채팅에서 직접 실행시키는 API는 없어서, 안내 문구로 유도하는 수준).

  * 주의(중요): 위 연동은 "다른 플러그인 인스턴스를 직접 import해서 호출"하는
    방식으로 구현했다. BookOasis 코어에 플러그인 레지스트리 같은 공식 API
    (예: self.get_plugin('unified_book'))가 있다면 그걸 쓰는 게 훨씬 안전하니,
    있다면 _get_sibling_plugin()의 내부 구현만 그걸로 바꾸면 된다. 또한
    unified_book의 실제 모듈 경로·클래스명·메서드 시그니처를 직접 확인하지
    못한 채 BookOasis의 명명 규칙(plugins/metadata/<id>/<id>.py, 클래스명
    <PascalCase><Id>MetadataProvider)과 ridi_book에서 확인된
    BaseMetadataProvider 계약을 근거로 "가장 그럴듯한 경로"를 추정해 넣었다.

- (신규) LIVE2D_MODEL_URL 설정에 Cubism 4 모델(.model3.json, 직접 호스팅한 URL)을
  넣으면, 우측 하단 마스코트가 정적 이미지/이모지 대신 살아 움직이는 Live2D
  캐릭터로 렌더링된다 (script.js가 pixi.js + pixi-live2d-display를 CDN에서
  지연 로딩). live2d.com 샘플은 라이선스 동의 후 다운로드해서 별도 서버에
  올려야 하며(핫링크 불가), 여기엔 그 호스팅 URL만 넣으면 된다. 비워두면
  기존 CHARACTER_IMAGE_URL/이모지 방식 그대로 동작한다.

- (신규) 책과는 무관하지만 마스코트 잡담용으로 /날씨 <지역>과 /주식 <종목명
  또는 코드>를 추가했다. 둘 다 DB 접근 없이 외부 사이트만 조회하는
  "/명령어" 방식이고, 별도 API 키가 필요 없다(둘 다 네이버의 공개 페이지/
  비공식 JSON을 그대로 이용). /날씨는 기상청 공식 API 대신 네이버 검색결과
  날씨 위젯을 BeautifulSoup으로 스크래핑하는 방식이라, 네이버가 페이지
  마크업을 바꾸면 깨질 수 있다는 점을 감안해야 한다(주식 쪽 비공식 JSON
  API보다 상대적으로 더 잘 깨지는 편).

- (신규) "손쉬운 것" 묶음: /환율 <통화>(open.er-api.com, 키 불필요),
  /로또(동행복권 공식 API가 최근 봇 차단으로 막혀서, GitHub Pages에
  호스팅되는 smok95/lotto 커뮤니티 미러 JSON을 대신 사용), /코인 <이름
  또는 티커>(CoinGecko 공개 API, 키 불필요 - 한글 코인명은 자체 별칭
  표로 매핑하고 표에 없으면 CoinGecko 검색으로 재시도), /명언(서재
  서평/줄거리 컬럼에서 랜덤 발췌), /운세(LLM에게 즉석에서 지어내게 함 -
  유일하게 LLM 호출이 필요해서 _handle_command가 아니라
  get_dashboard_data에서 직접 처리)를 추가했다.
- (신규) category_tab의 sessions를 "general"에서 "all"로 바꿔 4개 세션
  (general/adult/audiobook/video) 전체 사이드바에 노출되게 했다. 단, 서재
  관련 기능(_sample_library/_search_library 등)은 여전히 "books" 테이블
  스키마를 전제로 하므로, 다른 세션의 실제 테이블명/구조가 다르면 그
  기능만 조용히 빈 결과로 실패한다(예외를 이미 넓게 잡아뒀음) - 반면
  날씨/주식/환율/로또처럼 DB에 의존하지 않는 명령들은 세션과 무관하게
  항상 동작한다.
- (신규) 캐릭터 감정 표현: 답변 문구에 "축하/완독" 등이 있으면 emotion을
  "celebrate", "못 찾았어요/오류/미안" 등이 있으면 "sorry"로 분류해서
  응답에 함께 실어 보낸다(_detect_emotion). 실제로 아바타를 잠깐 다른
  이모지로 바꿨다가 원래 모습으로 되돌리는 애니메이션은 script.js의
  ym_flashEmotion()이 담당한다. 별도 설정 없이 항상 동작한다.
"""
import json
import logging
import re

import requests
from bs4 import BeautifulSoup

from plugins.metadata.base import BaseMetadataProvider

logger = logging.getLogger(__name__)

YM_REQUEST_TIMEOUT = 20
YM_MAX_MESSAGE_CHARS = 500
YM_MAX_HISTORY_TURNS = 8
YM_LIBRARY_SAMPLE_LIMIT = 30

YM_SEARCH_RESULT_LIMIT = 15
YM_MAX_SEARCH_KEYWORDS = 5
YM_REVIEW_SNIPPET_CHARS = 200
YM_REVIEW_COLUMN_CANDIDATES = ["description", "summary", "review", "synopsis", "overview", "plot"]
YM_RATING_COLUMN_CANDIDATES = ["rating", "my_rating", "score", "stars"]
YM_GENRE_COLUMN_CANDIDATES = ["genre", "category", "tags", "tag"]
YM_SERIES_COLUMN_CANDIDATES = ["series", "series_name", "series_title"]
YM_SEARCH_STOPWORDS = {
    "책", "저자", "작가", "있어", "있나요", "있어요", "있음",
    "알려줘", "알려주세요", "추천", "추천해줘", "추천해주세요",
    "뭐가", "뭐야", "뭐있어", "좀", "좀요", "해줘", "해주세요",
    "줄거리", "리뷰", "서평", "관련", "대해", "대한", "정보",
}
YM_RANDOM_TRIGGER_WORDS = {"아무거나", "암거나", "아무책", "암책", "랜덤", "무작위"}

YM_STATUS_LABELS = {
    "reading": "읽는 중",
    "completed": "완독",
    "to_read": "읽을 예정",
}
YM_STATUS_SET_COMMANDS = {
    "읽는중": "reading",
    "완독": "completed",
    "읽을예정": "to_read",
}

YM_MAX_CHAT_HISTORY_STORE = 40

# ------------------------------------------------------------------
# 날씨 조회 (/날씨) - 기상청 공식 API 대신 네이버 검색 결과의 날씨 위젯을
# 스크래핑한다 (주식과 마찬가지로 API 키 불필요). 공식 API가 아니라
# 네이버가 페이지 구조를 바꾸면 깨질 수 있다 - 실제로 몇 년 주기로 마크업이
# 바뀐 이력이 있다(2021, 2024 등). 아래 CSS 선택자는 2024~2025년 무렵
# 자주 확인되던 구조(temperature_text, temperature_info, today_chart_list)
# 기준이며, 깨지면 이 선택자들을 실제 페이지 구조에 맞게 갱신해야 한다.
# ------------------------------------------------------------------
YM_NAVER_WEATHER_URL = "https://search.naver.com/search.naver"
YM_NAVER_WEATHER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}

# ------------------------------------------------------------------
# 주식 시세 조회 (/주식) - 네이버 금융의 비공식 공개 JSON API (인증 불필요).
# 종목명 -> 코드 변환은 오토컴플리트 API, 시세는 realtime API를 쓴다.
# ------------------------------------------------------------------
YM_STOCK_SEARCH_URL = "https://m.stock.naver.com/front-api/search/autoComplete"
YM_STOCK_REALTIME_URL = "https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
YM_STOCK_DIRECTION_LABELS = {"2": "상승", "5": "하락"}

# ------------------------------------------------------------------
# 환율 조회 (/환율) - open.er-api.com(무료, 키 불필요) 사용. 네이버 금융에도
# 환율 API가 있을 것으로 보이나 정확한 엔드포인트/응답 형식을 확인하지
# 못해서, 검증 가능하고 안정적인 공개 API를 대신 골랐다.
# ------------------------------------------------------------------
YM_EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/{base}"
YM_CURRENCY_ALIASES = {
    "달러": "USD", "미국달러": "USD", "미화": "USD",
    "엔": "JPY", "엔화": "JPY", "일본엔": "JPY",
    "유로": "EUR", "유로화": "EUR",
    "위안": "CNY", "위안화": "CNY", "중국위안": "CNY",
    "파운드": "GBP", "영국파운드": "GBP",
}

# ------------------------------------------------------------------
# 로또 당첨번호 조회 (/로또) - 동행복권 공식 사이트의 공개 조회 API 사용
# (별도 키 불필요, 오래전부터 널리 쓰이는 안정적인 엔드포인트).
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# 로또 당첨번호 조회 (/로또) - 동행복권 공식 API(common.do?method=
# getLottoNumber)는 최근 봇 차단 정책이 강화돼 서버 IP에 따라 홈페이지로
# 302 리다이렉트만 돌아오는 걸 확인했다(동일 세션/Referer/User-Agent를
# 다 붙여봐도 동일). 대신 회차마다 자동 갱신되는 커뮤니티 미러
# (smok95/lotto, GitHub Pages 정적 JSON)를 사용한다 - 공식은 아니지만
# GitHub Pages라 안정적이고 봇 차단 이슈가 없다.
# ------------------------------------------------------------------
YM_LOTTO_LATEST_URL = "https://smok95.github.io/lotto/results/latest.json"

# ------------------------------------------------------------------
# 코인(가상자산) 시세 조회 (/코인) - CoinGecko 공개 API(무료, 키 불필요,
# 직접 호출해서 정상 동작 확인함) 사용. CoinGecko 검색은 한글 코인명을
# 인식하지 못해서, 자주 쓰는 한글 이름/약칭은 별칭 표로 먼저 매핑하고
# 표에 없으면 CoinGecko 자체 검색(영문명/티커)으로 한 번 더 시도한다.
# ------------------------------------------------------------------
YM_COIN_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
YM_COIN_SEARCH_URL = "https://api.coingecko.com/api/v3/search"
YM_COIN_ALIASES = {
    "비트코인": "bitcoin", "btc": "bitcoin",
    "이더리움": "ethereum", "이더": "ethereum", "eth": "ethereum",
    "리플": "ripple", "xrp": "ripple",
    "도지코인": "dogecoin", "도지": "dogecoin", "doge": "dogecoin",
    "솔라나": "solana", "sol": "solana",
    "카르다노": "cardano", "에이다": "cardano", "ada": "cardano",
    "라이트코인": "litecoin", "ltc": "litecoin",
    "폴카닷": "polkadot", "dot": "polkadot",
    "트론": "tron", "trx": "tron",
    "바이낸스코인": "binancecoin", "bnb": "binancecoin",
    "체인링크": "chainlink", "link": "chainlink",
    "폴리곤": "matic-network", "매틱": "matic-network", "matic": "matic-network",
    "시바이누": "shiba-inu", "시바": "shiba-inu", "shib": "shiba-inu",
    "아발란체": "avalanche-2", "avax": "avalanche-2",
}

# ------------------------------------------------------------------
# 캐릭터 감정 표현 - 답변 문구에 특정 단어가 있으면 아바타를 잠깐 다른
# 이모지로 바꿨다가 원래 모습(커스텀 이미지 또는 기본 이모지)으로 되돌린다.
# 실제 전환 애니메이션은 script.js가 담당하고, 여기서는 reply 텍스트만 보고
# "celebrate/sorry/normal" 중 하나로 분류해서 응답에 얹어준다.
# ------------------------------------------------------------------
YM_EMOTION_CELEBRATE_WORDS = ["축하", "완독", "🎉"]
YM_EMOTION_SORRY_WORDS = [
    "못 찾", "찾지 못", "가져오지 못", "실패", "오류가 발생",
    "미안", "죄송", "연결할 수 없어요", "안 됐어요",
]

# ------------------------------------------------------------------
# 다른 BookOasis 플러그인과의 연동 설정 (전부 "추정" - 위 모듈 docstring 참고)
# ------------------------------------------------------------------
YM_SIBLING_PLUGIN_MODULES = {
    "unified_book": ("plugins.metadata.unified_book.unified_book", "UnifiedBookMetadataProvider"),
}
YM_EXTERNAL_SEARCH_RESULT_LIMIT = 5
YM_QUIZ_TRIGGER_WORDS = {"퀴즈", "심심해", "심심하다", "게임하자", "놀자", "표지퀴즈"}
YM_QUIZ_SUGGESTION_TEXT = (
    "심심하면 '책표지 퀴즈'는 어때요? 왼쪽 사이드바의 '책표지 퀴즈' 탭에서 바로 즐길 수 있어요!"
)

YM_DEFAULT_SYSTEM_PROMPT = (
    "너는 '{character_name}'라는 이름의 친근한 독서 도우미 캐릭터야.\n"
    "사용자의 홈 서버 서재에 있는 책 중에서만 골라 짧고 다정하게 추천하거나,\n"
    "책 목록 · 저자 · 줄거리/서평을 물어보면 아래 데이터를 근거로 답해.\n"
    "모르는 책이나 정보를 지어내지 말고, 아래 데이터에 없으면\n"
    "'서재에서 비슷한 걸 못 찾았어요'라고 솔직히 말해.\n"
    "답변은 채팅 말풍선에 들어가므로 3~4문장 이내로 짧게 유지해.\n"
    "특별한 언급이 없으면 한국어로 답해."
)


class YM_ReadingMateMetadataProvider(BaseMetadataProvider):
    """우측 하단 오버레이 캐릭터 + LLM 채팅 기반 도서 추천/검색 플러그인."""

    id = "reading_doumi"
    name = "독서메이트 (오버레이 마스코트)"
    is_searchable = False

    config_schema = [
        {
            "key": "LLM_API_KEY",
            "label": "LLM API Key",
            "type": "password",
            "required": True,
        },
        {
            "key": "LLM_BASE_URL",
            "label": "LLM API Base URL (OpenAI 호환 /chat/completions 엔드포인트를 쓰는 서비스면 무엇이든 가능 - OpenAI, 로컬 Ollama/LM Studio, 자체 게이트웨이 등)",
            "type": "text",
            "default": "https://api.openai.com/v1",
            "required": True,
        },
        {
            "key": "LLM_MODEL",
            "label": "모델 이름",
            "type": "text",
            "default": "gpt-4o-mini",
            "required": True,
        },
        {
            "key": "CHARACTER_NAME",
            "label": "캐릭터 이름",
            "type": "text",
            "default": "책비서",
        },
        {
            "key": "CHARACTER_IMAGE_URL",
            "label": "캐릭터 이미지 URL (비워두면 기본 이모지로 대체, LIVE2D_MODEL_URL을 설정하면 이 값은 무시됨)",
            "type": "text",
            "required": False,
        },
        {
            "key": "LIVE2D_MODEL_URL",
            "label": (
                "Live2D 모델 URL (.model3.json, 선택) - live2d.com 샘플 페이지에서 내려받은 모델을 "
                "직접 호스팅한 뒤 그 model3.json 주소를 넣으세요. live2d.com 파일을 그대로 핫링크할 "
                "수는 없고(라이선스 동의 후 다운로드해야 함, 일반 이용자/연매출 1천만엔 미만 소규모 "
                "사업자 한정 무료), 반드시 별도 웹서버에 업로드해서 그 URL을 써야 해요. 비워두면 위 "
                "이미지/이모지로 대체돼요."
            ),
            "type": "text",
            "required": False,
        },
        {
            "key": "SYSTEM_PROMPT",
            "label": (
                "AI 페르소나 프롬프트 - {character_name}은 위 캐릭터 이름으로 자동 치환돼요. "
                "비워두고 저장하면(또는 아예 저장하지 않으면) 기본 프롬프트를 그대로 사용해요."
            ),
            "type": "textarea",
            "default": YM_DEFAULT_SYSTEM_PROMPT,
            "required": False,
        },
    ]

    category_tab = {
        "title": "독서메이트",
        "icon": "fa-solid fa-comment-dots",
        "order": 95,
        # 'all'이면 general/adult/audiobook/video 4개 세션(카테고리 탭) 전체에
        # 노출된다. 예전엔 "general"만 지정해서 일반 도서 사이드바에만 떴었다.
        "sessions": "all",
    }

    update_manifest = {
        "enabled": True,
        "provider": "github-raw",
        "raw_base_url": "https://raw.githubusercontent.com/leeyj/BookOasis_stable/main/sample_plugins/metadata/reading_doumi",
        "files": [
            "reading_doumi.py", "__init__.py", "VERSION",
            "index.html", "style.css", "script.js",
            "README.md", "requirements.txt",
        ],
        "version_file": "VERSION",
        "version_key": "plugin version",
        "show_sample_update_button": True,
    }

    # ------------------------------------------------------------------
    # 필수 계약
    # ------------------------------------------------------------------
    def search(self, db_type, query):
        return []

    def apply(self, db_type, book_id, item_data):
        return False, "독서메이트 플러그인은 도서 메타데이터 적용을 지원하지 않습니다."

    # ------------------------------------------------------------------
    # 요청 파라미터 파싱
    # ------------------------------------------------------------------
    def _get_request_args(self):
        try:
            from flask import request

            message = (request.args.get("message") or "").strip()[:YM_MAX_MESSAGE_CHARS]

            history = []
            raw_history = request.args.get("history")
            if raw_history:
                try:
                    parsed = json.loads(raw_history)
                    if isinstance(parsed, list):
                        for turn in parsed[-YM_MAX_HISTORY_TURNS:]:
                            role = turn.get("role")
                            content = str(turn.get("content") or "")[:YM_MAX_MESSAGE_CHARS]
                            if role in ("user", "assistant") and content:
                                history.append({"role": role, "content": content})
                except Exception:
                    history = []

            return {"message": message, "history": history}
        except Exception:
            return {"message": "", "history": []}

    def _save_config(self, db_type, cfg):
        try:
            self.set_plugin_config(db_type, cfg)
        except Exception as e:
            logger.warning("[reading_doumi] 설정 저장 실패: %s", e)

    # ------------------------------------------------------------------
    # 다른 BookOasis 플러그인 인스턴스 가져오기 (추정 구현 - 모듈 docstring 참고)
    # ------------------------------------------------------------------
    def _get_sibling_plugin(self, plugin_id):
        mapping = YM_SIBLING_PLUGIN_MODULES.get(plugin_id)
        if not mapping:
            return None
        module_path, class_name = mapping
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            return cls()
        except Exception as e:
            logger.info(
                "[reading_doumi] '%s' 플러그인 연동 불가(%s) - 이 기능은 조용히 건너뜁니다.",
                plugin_id, e,
            )
            return None

    def _search_unified_book(self, db_type, query):
        """unified_book 플러그인(BaseMetadataProvider 계약)에게 외부 도서 검색을
        위임한다. 서재 DB가 아니라 unified_book이 붙여둔 외부 소스(교보문고,
        리디북스, 알라딘, 국립중앙도서관 등)를 검색하는 것으로 이해하면 된다."""
        provider = self._get_sibling_plugin("unified_book")
        if not provider:
            return []
        try:
            results = provider.search(db_type, query) or []
        except Exception as e:
            logger.info("[reading_doumi] unified_book 검색 실패: %s", e)
            return []

        formatted = []
        for r in results[:YM_EXTERNAL_SEARCH_RESULT_LIMIT]:
            formatted.append({
                "title": r.get("title") or "",
                "author": r.get("author") or "",
                "publisher": r.get("publisher") or "",
                "link": r.get("link") or "",
            })
        return [f for f in formatted if f["title"]]

    def _format_external_line(self, book):
        author = f" - {book['author']}" if book.get("author") else ""
        publisher = f" ({book['publisher']})" if book.get("publisher") else ""
        line = f"- {book['title']}{author}{publisher}"
        if book.get("link"):
            line += f" | {book['link']}"
        return line

    # ------------------------------------------------------------------
    # books 테이블 스키마 조사
    # ------------------------------------------------------------------
    def _inspect_book_columns(self, db_type):
        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all("PRAGMA table_info(books)")
            names = {(r.get("name") or "").lower() for r in (rows or [])}
        except Exception as e:
            logger.warning("[reading_doumi] books 테이블 스키마 조회 실패: %s", e)
            names = set()

        def pick(candidates):
            return next((c for c in candidates if c in names), None)

        return {
            "review": pick(YM_REVIEW_COLUMN_CANDIDATES),
            "rating": pick(YM_RATING_COLUMN_CANDIDATES),
            "genre": pick(YM_GENRE_COLUMN_CANDIDATES),
            "series": pick(YM_SERIES_COLUMN_CANDIDATES),
        }

    def _select_columns_sql(self, cols):
        parts = ["id", "title", "author"]
        for key in ("review", "rating", "genre", "series"):
            col = cols.get(key)
            if col:
                parts.append(f"{col} AS {key}")
        return ", ".join(parts)

    def _format_book_row(self, row, cols):
        return {
            "id": row.get("id"),
            "title": row.get("title") or "",
            "author": row.get("author") or "",
            "review": (row.get("review") or "").strip() if cols.get("review") else "",
            "rating": row.get("rating") if cols.get("rating") else None,
            "genre": (row.get("genre") or "").strip() if cols.get("genre") else "",
        }

    def _format_book_line(self, book):
        author = f" - {book['author']}" if book.get("author") else ""
        line = f"- {book['title']}{author}"

        extras = []
        if book.get("genre"):
            extras.append(book["genre"])
        if book.get("rating") not in (None, ""):
            extras.append(f"평점 {book['rating']}")
        if book.get("status_label"):
            extras.append(book["status_label"])
        if extras:
            line += " (" + ", ".join(str(e) for e in extras) + ")"

        review = (book.get("review") or "").strip()
        if review:
            snippet = review[:YM_REVIEW_SNIPPET_CHARS]
            if len(review) > YM_REVIEW_SNIPPET_CHARS:
                snippet += "…"
            line += f" | 줄거리/서평: {snippet}"
        return line

    def _sample_library(self, db_type, cols):
        select_sql = self._select_columns_sql(cols)
        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all(
                f"""
                SELECT {select_sql} FROM books
                WHERE COALESCE(is_deleted, 0) = 0
                ORDER BY id DESC
                LIMIT ?
                """,
                (YM_LIBRARY_SAMPLE_LIMIT,),
            )
            return [self._format_book_row(r, cols) for r in (rows or []) if r.get("title")]
        except Exception as e:
            logger.warning("[reading_doumi] 서재 샘플 조회 실패: %s", e)
            return []

    def _extract_keywords(self, message):
        words = []
        for raw in message.split():
            w = raw.strip(" ?!.,~☆★…\"'")
            if len(w) < 2:
                continue
            if w in YM_SEARCH_STOPWORDS:
                continue
            words.append(w)
        return words[:YM_MAX_SEARCH_KEYWORDS]

    def _parse_rating_filter(self, message):
        m = re.search(r"(\d+(?:\.\d+)?)\s*점?\s*(이상|넘는|초과)", message)
        if m:
            op = ">=" if m.group(2) == "이상" else ">"
            return (op, float(m.group(1)))
        m = re.search(r"(\d+(?:\.\d+)?)\s*점?\s*(이하|미만)", message)
        if m:
            op = "<=" if m.group(2) == "이하" else "<"
            return (op, float(m.group(1)))
        return None

    def _search_library(self, db_type, message, cols):
        keywords = self._extract_keywords(message)
        rating_filter = self._parse_rating_filter(message)
        if not keywords and not rating_filter:
            return []

        select_sql = self._select_columns_sql(cols)
        conditions = []
        params = []

        if keywords:
            keyword_clauses = []
            for kw in keywords:
                like = f"%{kw}%"
                clause_cols = ["title", "author"]
                if cols.get("review"):
                    clause_cols.append(cols["review"])
                if cols.get("genre"):
                    clause_cols.append(cols["genre"])
                sub = " OR ".join(f"{c} LIKE ?" for c in clause_cols)
                keyword_clauses.append(f"({sub})")
                params.extend([like] * len(clause_cols))
            conditions.append("(" + " OR ".join(keyword_clauses) + ")")

        if rating_filter and cols.get("rating"):
            op, value = rating_filter
            conditions.append(f"{cols['rating']} {op} ?")
            params.append(value)

        if not conditions:
            return []
        where_clause = " AND ".join(conditions)

        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all(
                f"""
                SELECT {select_sql} FROM books
                WHERE COALESCE(is_deleted, 0) = 0 AND ({where_clause})
                ORDER BY id DESC
                LIMIT ?
                """,
                (*params, YM_SEARCH_RESULT_LIMIT),
            )
            return [self._format_book_row(r, cols) for r in (rows or []) if r.get("title")]
        except Exception as e:
            logger.warning("[reading_doumi] 서재 검색 실패: %s", e)
            return []

    def _find_books_by_title(self, db_type, title_query, cols, limit=5):
        select_sql = self._select_columns_sql(cols)
        like = f"%{title_query.strip()}%"
        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all(
                f"""
                SELECT {select_sql} FROM books
                WHERE COALESCE(is_deleted, 0) = 0 AND title LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (like, limit),
            )
            return [self._format_book_row(r, cols) for r in (rows or []) if r.get("title")]
        except Exception as e:
            logger.warning("[reading_doumi] 책 제목 검색 실패: %s", e)
            return []

    def _pick_random_book(self, db_type, cols):
        select_sql = self._select_columns_sql(cols)
        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all(
                f"""
                SELECT {select_sql} FROM books
                WHERE COALESCE(is_deleted, 0) = 0
                ORDER BY RANDOM()
                LIMIT 1
                """
            )
            books = [self._format_book_row(r, cols) for r in (rows or []) if r.get("title")]
            return books[0] if books else None
        except Exception as e:
            logger.warning("[reading_doumi] 랜덤 추천 조회 실패: %s", e)
            return None

    def _get_library_stats(self, db_type):
        try:
            gateway = self.get_db_gateway(db_type)
            total_rows = gateway.fetch_all(
                "SELECT COUNT(*) AS cnt FROM books WHERE COALESCE(is_deleted, 0) = 0"
            )
            total = (total_rows[0].get("cnt") if total_rows else 0) or 0

            top_authors = gateway.fetch_all(
                """
                SELECT author, COUNT(*) AS cnt FROM books
                WHERE COALESCE(is_deleted, 0) = 0 AND COALESCE(author, '') != ''
                GROUP BY author
                ORDER BY cnt DESC
                LIMIT 5
                """
            )
            return {
                "total": total,
                "top_authors": [
                    {"author": r.get("author") or "", "count": r.get("cnt") or 0}
                    for r in (top_authors or [])
                ],
            }
        except Exception as e:
            logger.warning("[reading_doumi] 서재 통계 조회 실패: %s", e)
            return {"total": 0, "top_authors": []}

    def _get_series_count(self, db_type, series_query, cols):
        series_col = cols.get("series")
        if not series_col:
            return None
        like = f"%{series_query.strip()}%"
        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all(
                f"""
                SELECT COUNT(*) AS cnt FROM books
                WHERE COALESCE(is_deleted, 0) = 0 AND {series_col} LIKE ?
                """,
                (like,),
            )
            return (rows[0].get("cnt") if rows else 0) or 0
        except Exception as e:
            logger.warning("[reading_doumi] 시리즈 통계 조회 실패: %s", e)
            return None

    # ------------------------------------------------------------------
    # 날씨 조회 (/날씨) - 책과 무관한 잡담용 부가 기능. DB 접근 없음.
    # ------------------------------------------------------------------
    def _get_weather(self, region):
        region = (region or "").strip() or "서울"
        query = f"{region} 날씨"
        try:
            resp = requests.get(
                YM_NAVER_WEATHER_URL,
                params={"query": query},
                headers=YM_NAVER_WEATHER_HEADERS,
                timeout=YM_REQUEST_TIMEOUT,
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            box = (
                soup.select_one("div.weather_info > div.status_wrap")
                or soup.select_one("div.weather_info")
            )
            if not box:
                return None, "날씨 정보를 못 찾았어요. 네이버 페이지 구조가 바뀌었을 수 있어요."

            temp = None
            temp_el = box.select_one("div.temperature_text")
            if temp_el:
                strong = temp_el.select_one("strong")
                temp = (strong.get_text(strip=True) if strong else temp_el.get_text(strip=True))

            summary = ""
            summary_el = box.select_one("div.temperature_info") or box.select_one("p.summary")
            if summary_el:
                summary = " ".join(summary_el.get_text(" ", strip=True).split())

            chart_texts = []
            for li in box.select("ul.today_chart_list > li"):
                target = li.select_one("a") or li
                text = target.get_text(" ", strip=True)
                if text:
                    chart_texts.append(text)

            if not temp and not summary:
                return None, "날씨 정보를 못 찾았어요. 네이버 페이지 구조가 바뀌었을 수 있어요."

            parts = [f"{region} 현재 날씨"]
            if temp:
                parts.append(temp if ("℃" in temp or "도" in temp) else f"{temp}℃")
            if summary:
                parts.append(summary)
            result = ", ".join(parts)
            if chart_texts:
                result += " (" + " / ".join(chart_texts[:4]) + ")"
            return result, None
        except Exception as e:
            logger.warning("[reading_doumi] 네이버 날씨 파싱 실패: %s", e)
            return None, "날씨 정보를 가져오지 못했어요."

    # ------------------------------------------------------------------
    # 주식 시세 조회 (/주식) - 책과 무관한 잡담용 부가 기능. DB 접근 없음.
    # ------------------------------------------------------------------
    def _resolve_stock_code(self, query):
        query = query.strip()
        if query.isdigit() and len(query) == 6:
            return query, query
        try:
            resp = requests.get(
                YM_STOCK_SEARCH_URL,
                params={"query": query, "target": "stock,index,marketindicator,coin,ipo"},
                timeout=YM_REQUEST_TIMEOUT,
            )
            items = (resp.json().get("result") or {}).get("items") or []
            for item in items:
                if item.get("code"):
                    return item["code"], item.get("name") or query
        except Exception as e:
            logger.warning("[reading_doumi] 종목 검색 실패: %s", e)
        return None, None

    def _get_stock_quote(self, query):
        code, name = self._resolve_stock_code(query)
        if not code:
            return None, f"'{query}' 종목을 찾지 못했어요."

        try:
            resp = requests.get(
                YM_STOCK_REALTIME_URL.format(code=code), timeout=YM_REQUEST_TIMEOUT
            )
            datas = resp.json().get("datas") or []
            if not datas:
                return None, f"'{query}' 시세를 가져오지 못했어요."
            d = datas[0]
        except Exception as e:
            logger.warning("[reading_doumi] 시세 조회 실패: %s", e)
            return None, "시세 조회 중 오류가 발생했어요."

        price = d.get("closePrice")
        change = d.get("compareToPreviousClosePrice")
        pct = d.get("fluctuationsRatio")
        direction_code = str((d.get("compareToPreviousPrice") or {}).get("code") or "")
        direction = YM_STOCK_DIRECTION_LABELS.get(direction_code, "보합")
        status = "장중" if d.get("marketStatus") == "OPEN" else "장마감"

        display_name = name or query
        line = f"{display_name}({code}) {status} 현재가 {price}원"
        if change is not None:
            sign = "+" if direction == "상승" else ("-" if direction == "하락" else "")
            line += f" ({sign}{change}, {direction}, {pct}%)"
        return line, None

    # ------------------------------------------------------------------
    # 환율 조회 (/환율) - DB 접근 없음.
    # ------------------------------------------------------------------
    def _get_exchange_rate(self, query):
        raw = (query or "").strip()
        code = YM_CURRENCY_ALIASES.get(raw, raw.upper())
        try:
            resp = requests.get(
                YM_EXCHANGE_RATE_URL.format(base=code), timeout=YM_REQUEST_TIMEOUT
            )
            data = resp.json()
            if data.get("result") != "success":
                return None, f"'{query}' 통화 코드를 찾지 못했어요. (예: USD, JPY, EUR, CNY)"
            krw = (data.get("rates") or {}).get("KRW")
            if krw is None:
                return None, "원화 환율 정보를 가져오지 못했어요."
            return f"1 {code} = {krw:,.2f}원", None
        except Exception as e:
            logger.warning("[reading_doumi] 환율 조회 실패: %s", e)
            return None, "환율 정보를 가져오지 못했어요."

    # ------------------------------------------------------------------
    # 로또 당첨번호 조회 (/로또) - DB 접근 없음.
    # ------------------------------------------------------------------
    def _get_lotto_result(self):
        try:
            resp = requests.get(YM_LOTTO_LATEST_URL, timeout=YM_REQUEST_TIMEOUT)
            data = resp.json()
        except Exception as e:
            logger.warning("[reading_doumi] 로또 조회 실패: %s", e)
            return None

        numbers = data.get("numbers")
        if not numbers:
            return None
        return {
            "round": data.get("draw_no"),
            "date": (data.get("date") or "")[:10],
            "numbers": numbers,
            "bonus": data.get("bonus_no"),
        }

    # ------------------------------------------------------------------
    # 코인 시세 조회 (/코인) - DB 접근 없음.
    # ------------------------------------------------------------------
    def _resolve_coin_id(self, query):
        key = query.strip().lower()
        if key in YM_COIN_ALIASES:
            return YM_COIN_ALIASES[key]
        try:
            resp = requests.get(
                YM_COIN_SEARCH_URL, params={"query": query.strip()}, timeout=YM_REQUEST_TIMEOUT
            )
            coins = resp.json().get("coins") or []
            if coins:
                return coins[0].get("id")
        except Exception as e:
            logger.info("[reading_doumi] 코인 검색 실패: %s", e)
        return None

    def _get_coin_price(self, query):
        coin_id = self._resolve_coin_id(query)
        if not coin_id:
            return None, f"'{query}' 코인을 찾지 못했어요. (예: 비트코인, ETH, 리플)"

        try:
            resp = requests.get(
                YM_COIN_PRICE_URL,
                params={"ids": coin_id, "vs_currencies": "krw", "include_24hr_change": "true"},
                timeout=YM_REQUEST_TIMEOUT,
            )
            data = resp.json().get(coin_id)
            if not data:
                return None, f"'{query}' 시세를 가져오지 못했어요."
        except Exception as e:
            logger.warning("[reading_doumi] 코인 시세 조회 실패: %s", e)
            return None, "코인 시세 조회 중 오류가 발생했어요."

        price = data.get("krw")
        change = data.get("krw_24h_change")
        line = f"{query.strip()} 현재가 {price:,.0f}원"
        if change is not None:
            direction = "상승" if change >= 0 else "하락"
            line += f" (24시간 {direction} {abs(change):.2f}%)"
        return line, None

    # ------------------------------------------------------------------
    # 오늘의 한 줄 (/명언) - 서재 서평/줄거리 컬럼에서 랜덤으로 하나 뽑는다.
    # ------------------------------------------------------------------
    def _pick_random_quote(self, db_type, cols):
        review_col = cols.get("review")
        if not review_col:
            return None
        select_sql = self._select_columns_sql(cols)
        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all(
                f"""
                SELECT {select_sql} FROM books
                WHERE COALESCE(is_deleted, 0) = 0
                  AND {review_col} IS NOT NULL AND TRIM({review_col}) != ''
                ORDER BY RANDOM()
                LIMIT 1
                """
            )
            books = [self._format_book_row(r, cols) for r in (rows or []) if r.get("title")]
            return books[0] if books else None
        except Exception as e:
            logger.warning("[reading_doumi] 오늘의 한 줄 조회 실패: %s", e)
            return None

    # ------------------------------------------------------------------
    # 캐릭터 감정 표현 - 답변 문구를 보고 celebrate/sorry/normal로 분류한다.
    # ------------------------------------------------------------------
    def _detect_emotion(self, reply_text):
        text = reply_text or ""
        if any(w in text for w in YM_EMOTION_SORRY_WORDS):
            return "sorry"
        if any(w in text for w in YM_EMOTION_CELEBRATE_WORDS):
            return "celebrate"
        return "normal"

    def _reply_payload(self, character_name, character_image_url, character_live2d_url, reply):
        return {
            "success": True,
            "reply": reply,
            "character_name": character_name,
            "character_image_url": character_image_url,
            "character_live2d_url": character_live2d_url,
            "emotion": self._detect_emotion(reply),
        }

    def _get_status_map(self, cfg):
        raw = cfg.get("_BOOK_STATUS")
        return raw if isinstance(raw, dict) else {}

    def _save_status_map(self, db_type, cfg, status_map):
        cfg["_BOOK_STATUS"] = status_map
        self._save_config(db_type, cfg)

    def _titles_by_status(self, db_type, status_map, status):
        ids = [int(k) for k, v in status_map.items() if v == status and str(k).isdigit()]
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        try:
            gateway = self.get_db_gateway(db_type)
            rows = gateway.fetch_all(
                f"""
                SELECT title FROM books
                WHERE COALESCE(is_deleted, 0) = 0 AND id IN ({placeholders})
                ORDER BY id DESC
                """,
                tuple(ids),
            )
            return [r.get("title") for r in (rows or []) if r.get("title")]
        except Exception as e:
            logger.warning("[reading_doumi] 상태별 목록 조회 실패: %s", e)
            return []

    def _persist_turn(self, db_type, cfg, stored_history, user_text, reply_text):
        stored_history.append({"role": "user", "content": user_text})
        stored_history.append({"role": "assistant", "content": reply_text})
        trimmed = stored_history[-YM_MAX_CHAT_HISTORY_STORE:]
        cfg["_CHAT_HISTORY"] = trimmed
        self._save_config(db_type, cfg)

    # ------------------------------------------------------------------
    # "/명령어" 처리 - LLM 호출 없이 코드에서 바로 답을 만든다.
    # ------------------------------------------------------------------
    def _handle_command(self, db_type, cfg, message, cols):
        if not message.startswith("/"):
            return None, False

        parts = message[1:].strip().split(maxsplit=1)
        if not parts:
            return None, False
        cmd = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in YM_STATUS_SET_COMMANDS:
            status = YM_STATUS_SET_COMMANDS[cmd]
            label = YM_STATUS_LABELS[status]
            if not arg:
                return f"어떤 책을 '{label}'(으)로 표시할까요? 예) /{cmd} 어린왕자", True

            matches = self._find_books_by_title(db_type, arg, cols)
            if not matches:
                return f"'{arg}'(으)로 서재에서 못 찾았어요.", True
            if len(matches) > 1:
                listing = ", ".join(m["title"] for m in matches[:5])
                return f"'{arg}'로 여러 권이 검색됐어요: {listing}. 조금 더 구체적으로 말해줄래요?", True

            book = matches[0]
            status_map = self._get_status_map(cfg)
            status_map[str(book["id"])] = status
            self._save_status_map(db_type, cfg, status_map)

            if status == "completed":
                return f"'{book['title']}' 완독 축하해요! 🎉 다음 책도 골라줄까요?", True
            return f"'{book['title']}'을(를) '{label}'(으)로 표시했어요.", True

        if cmd == "상태":
            if not arg:
                status_map = self._get_status_map(cfg)
                reading_titles = self._titles_by_status(db_type, status_map, "reading")
                if not reading_titles:
                    return "지금 '읽는 중'으로 표시된 책이 없어요.", True
                return "지금 읽는 중인 책: " + ", ".join(reading_titles), True

            matches = self._find_books_by_title(db_type, arg, cols)
            if not matches:
                return f"'{arg}'(으)로 서재에서 못 찾았어요.", True
            status_map = self._get_status_map(cfg)
            lines = []
            for m in matches[:5]:
                label = YM_STATUS_LABELS.get(status_map.get(str(m["id"])), "상태 미지정")
                lines.append(f"{m['title']}: {label}")
            return "\n".join(lines), True

        if cmd in ("랜덤", "아무거나", "무작위"):
            book = self._pick_random_book(db_type, cols)
            if not book:
                return "서재에 책이 없어서 추천할 수 없어요.", True
            return "오늘의 랜덤 추천: " + self._format_book_line(book), True

        if cmd == "통계":
            stats = self._get_library_stats(db_type)
            lines = [f"서재에 총 {stats['total']}권이 있어요."]
            if stats["top_authors"]:
                top = ", ".join(f"{a['author']}({a['count']}권)" for a in stats["top_authors"])
                lines.append(f"가장 많이 소장한 저자 Top {len(stats['top_authors'])}: {top}")
            return "\n".join(lines), True

        if cmd == "시리즈":
            if not arg:
                return "어떤 시리즈가 궁금해요? 예) /시리즈 해리포터", True
            count = self._get_series_count(db_type, arg, cols)
            if count is None:
                return (
                    "서재에 시리즈 정보가 따로 없어서 집계는 어려워요. "
                    "대신 채팅으로 저자나 제목을 물어봐 주세요."
                ), True
            if count == 0:
                return f"'{arg}' 시리즈는 서재에서 못 찾았어요.", True
            return f"'{arg}' 시리즈는 서재에 {count}권 있어요.", True

        # --- 책과 무관한 잡담용 부가 명령 ---
        if cmd == "날씨":
            region = arg or "서울"
            result, err = self._get_weather(region)
            return (err or result), True

        if cmd == "주식":
            if not arg:
                return "종목명이나 종목코드를 같이 적어주세요. 예) /주식 삼성전자", True
            result, err = self._get_stock_quote(arg)
            return (err or result), True

        if cmd == "환율":
            if not arg:
                return "통화 이름이나 코드를 같이 적어주세요. 예) /환율 USD, /환율 엔화", True
            result, err = self._get_exchange_rate(arg)
            return (err or result), True

        if cmd == "로또":
            result = self._get_lotto_result()
            if not result:
                return "로또 당첨번호를 가져오지 못했어요.", True
            numbers = ", ".join(str(n) for n in result["numbers"])
            return (
                f"{result['round']}회({result['date']}) 당첨번호: {numbers} "
                f"+ 보너스 {result['bonus']}"
            ), True

        if cmd == "코인":
            if not arg:
                return "코인 이름이나 티커를 같이 적어주세요. 예) /코인 비트코인, /코인 ETH", True
            result, err = self._get_coin_price(arg)
            return (err or result), True

        if cmd in ("명언", "오늘의한줄"):
            book = self._pick_random_quote(db_type, cols)
            if not book:
                return "서재에 서평/줄거리 데이터가 없어서 아직 뽑아줄 게 없어요.", True
            review = (book.get("review") or "").strip()
            snippet = review[:YM_REVIEW_SNIPPET_CHARS]
            if len(review) > YM_REVIEW_SNIPPET_CHARS:
                snippet += "…"
            return f"오늘의 한 줄 — 《{book['title']}》: {snippet}", True

        # --- 다른 플러그인 연동 명령 ---
        if cmd == "외부검색":
            if not arg:
                return "찾고 싶은 책 제목을 같이 적어주세요. 예) /외부검색 어린왕자", True
            results = self._search_unified_book(db_type, arg)
            if not results:
                return f"'{arg}'을(를) 외부에서도 찾지 못했어요. (unified_book 플러그인 연동을 확인해주세요)", True
            lines = [f"서재엔 없지만 외부에서 이렇게 찾았어요:"]
            lines.extend(self._format_external_line(r) for r in results)
            return "\n".join(lines), True

        if cmd == "퀴즈":
            return YM_QUIZ_SUGGESTION_TEXT, True

        return None, False

    def _build_system_prompt(
        self, persona_prompt, library_sample, search_results, reading_now_titles, external_results
    ):
        lines = [persona_prompt]

        if reading_now_titles:
            lines.append("사용자가 지금 '읽는 중'으로 표시한 책: " + ", ".join(reading_now_titles))

        if search_results:
            lines.append("사용자 질문과 직접 관련된 책 (검색 결과 - 최우선 근거):")
            for book in search_results:
                lines.append(self._format_book_line(book))

        if library_sample:
            lines.append("서재에 최근 추가된 책 목록 (일부):")
            for book in library_sample:
                lines.append(self._format_book_line(book))
        elif not search_results:
            lines.append("현재 서재 정보를 불러오지 못했으니, 일반적인 독서 취향만 물어보며 대화를 이어가.")

        if external_results:
            lines.append(
                "서재에는 없지만 외부 도서 검색(unified_book)에서 찾은 책 - 참고용이며, "
                "이 책들을 언급할 때는 반드시 '서재에는 없지만 외부에서 찾았어요'라고 밝혀:"
            )
            for r in external_results:
                lines.append(self._format_external_line(r))

        return "\n".join(lines)

    def _resolve_persona_prompt(self, cfg, character_name):
        custom = str(cfg.get("SYSTEM_PROMPT") or "").strip()
        template = custom if custom else YM_DEFAULT_SYSTEM_PROMPT
        return template.replace("{character_name}", character_name)

    def _call_llm(self, base_url, api_key, model, messages):
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=YM_REQUEST_TIMEOUT,
        )
        if not resp.ok:
            detail = ""
            try:
                body = resp.json()
                detail = (body.get("error") or {}).get("message") or str(body)
            except Exception:
                detail = (resp.text or "")[:200]
            raise RuntimeError(f"status {resp.status_code}: {detail}")

        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("LLM 응답에 choices가 없습니다.")
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("LLM 응답이 비어 있습니다.")
        return content

    # ------------------------------------------------------------------
    # 채팅 한 턴 처리 - 마스코트 위젯의 유일한 백엔드 진입점
    # ------------------------------------------------------------------
    def get_dashboard_data(self, db_type, limit=10):
        cfg = self.get_plugin_config(db_type, default={}) or {}
        api_key = str(cfg.get("LLM_API_KEY") or "").strip()
        base_url = str(cfg.get("LLM_BASE_URL") or "https://api.openai.com/v1").strip().rstrip("/")
        model = str(cfg.get("LLM_MODEL") or "gpt-4o-mini").strip()
        character_name = str(cfg.get("CHARACTER_NAME") or "책비서").strip()
        character_image_url = str(cfg.get("CHARACTER_IMAGE_URL") or "").strip()
        character_live2d_url = str(cfg.get("LIVE2D_MODEL_URL") or "").strip()

        if not api_key:
            return {
                "success": False,
                "error": "LLM_API_KEY가 설정되지 않았습니다. 환경설정 > 플러그인에서 입력해주세요.",
            }

        def reply_payload(reply_text):
            return self._reply_payload(character_name, character_image_url, character_live2d_url, reply_text)

        args = self._get_request_args()
        stored_history = cfg.get("_CHAT_HISTORY")
        stored_history = stored_history if isinstance(stored_history, list) else []

        if not args["message"]:
            if stored_history:
                return {
                    "success": True,
                    "history": stored_history[-(YM_MAX_HISTORY_TURNS * 2):],
                    "character_name": character_name,
                    "character_image_url": character_image_url,
                    "character_live2d_url": character_live2d_url,
                }
            return reply_payload(
                f"안녕! 나는 {character_name}야. 책 추천은 물론, 서재에 있는 책 목록·저자·줄거리도 찾아줄 수 있어.\n"
                "'/완독 책 제목', '/읽는중 책 제목', '/랜덤', '/통계', '/외부검색 책 제목', '/퀴즈', "
                "'/날씨 지역', '/주식 종목명', '/환율 통화', '/로또', '/코인 이름', '/명언', '/운세' 같은 명령도 써봐!"
            )

        message = args["message"]
        cols = self._inspect_book_columns(db_type)

        # 1) "/명령어" - LLM 호출 없이 바로 처리
        command_reply, handled = self._handle_command(db_type, cfg, message, cols)
        if handled:
            self._persist_turn(db_type, cfg, stored_history, message, command_reply)
            return reply_payload(command_reply)

        # 1-1) "/운세"만 예외적으로 LLM이 필요해서 여기서 직접 처리한다
        # (_handle_command는 DB/외부 API만 쓰고 LLM 자격증명이 없어서 못 다룸).
        stripped = message.strip()
        if stripped == "/운세" or stripped.startswith("/운세 "):
            fortune_prompt = (
                f"너는 '{character_name}'라는 이름의 친근한 캐릭터야. "
                "사용자에게 오늘의 운세를 재미있고 가볍게, 미신처럼 진지하지 않게 2~3문장으로 "
                "지어내서 알려줘. 책이나 독서와 살짝 엮어도 좋아. 특별한 언급이 없으면 한국어로 답해."
            )
            try:
                reply = self._call_llm(
                    base_url, api_key, model,
                    [
                        {"role": "system", "content": fortune_prompt},
                        {"role": "user", "content": "오늘의 운세 봐줘"},
                    ],
                )
            except Exception as e:
                logger.warning("[reading_doumi] 운세 생성 실패: %s", e)
                reply = "오늘은 운세를 못 봐줬어요, 미안!"
            self._persist_turn(db_type, cfg, stored_history, message, reply)
            return reply_payload(reply)

        keywords_probe = self._extract_keywords(message)

        # 2) 책표지 퀴즈 자연어 유도 (cover_quiz 연동 - 안내 문구 수준)
        if any(w in message for w in YM_QUIZ_TRIGGER_WORDS):
            self._persist_turn(db_type, cfg, stored_history, message, YM_QUIZ_SUGGESTION_TEXT)
            return reply_payload(YM_QUIZ_SUGGESTION_TEXT)

        # 3) 자연어 "아무거나/랜덤" 요청
        if not keywords_probe and any(w in message for w in YM_RANDOM_TRIGGER_WORDS):
            book = self._pick_random_book(db_type, cols)
            reply = (
                "오늘의 랜덤 추천: " + self._format_book_line(book)
                if book
                else "서재에 책이 없어서 추천할 수 없어요."
            )
            self._persist_turn(db_type, cfg, stored_history, message, reply)
            return reply_payload(reply)

        # 4) 일반 대화 흐름 (LLM 호출)
        status_map = self._get_status_map(cfg)
        reading_now_titles = self._titles_by_status(db_type, status_map, "reading")

        library_sample = self._sample_library(db_type, cols)
        search_results = self._search_library(db_type, message, cols)

        # 서재에서 못 찾았지만 특정 책을 찾는 것으로 보이면(검색어는 있는데
        # 결과가 없음) unified_book으로 외부 검색까지 시도한다.
        external_results = []
        if keywords_probe and not search_results:
            external_results = self._search_unified_book(db_type, message)

        persona_prompt = self._resolve_persona_prompt(cfg, character_name)
        system_prompt = self._build_system_prompt(
            persona_prompt, library_sample, search_results, reading_now_titles, external_results
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(args["history"])
        messages.append({"role": "user", "content": message})

        try:
            reply = self._call_llm(base_url, api_key, model, messages)
        except Exception as e:
            logger.warning("[reading_doumi] LLM 호출 실패: %s", e)
            return {"success": False, "error": f"LLM 호출에 실패했어요: {e}"}

        self._persist_turn(db_type, cfg, stored_history, message, reply)

        return reply_payload(reply)
