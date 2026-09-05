# 독서메이트 (reading_doumi)

BookOasis의 오버레이 마스코트 플러그인. 우측 하단에 떠 있는 캐릭터를 클릭하면
채팅창이 열리고, LLM과 대화하며 서재의 책을 추천받거나 목록/저자/줄거리를
물어볼 수 있다. 책과 무관한 날씨/주식/환율/로또/코인 같은 잡담용 명령도
지원한다.

- 플러그인 id: `reading_doumi` (이전 id: `reading_mate`)
- 클래스: `YM_ReadingMateMetadataProvider`
- 카테고리 탭: `general`/`adult`/`audiobook`/`video` 4개 세션 전체에 노출

## 설치

1. `plugins/metadata/reading_doumi/` 아래에 이 폴더의 파일들을 그대로 넣는다
   (`reading_doumi.py`, `__init__.py`, `VERSION`, `index.html`, `style.css`,
   `script.js`, `README.md`, `requirements.txt`).
2. `pip install -r requirements.txt` (또는 컨테이너에 `beautifulsoup4`가
   이미 설치돼 있는지 확인).
3. BookOasis 재시작 후 좌측 사이드바에서 "독서메이트" 탭을 한 번 연다
   (탭을 열어야 마스코트가 화면에 뜬다 - 새로고침하면 다시 한 번 열어야 함).
4. 환경설정 > 플러그인 > 독서메이트에서 `LLM_API_KEY` 등을 설정한다.

## 환경설정 항목

| 키 | 필수 | 설명 |
| --- | --- | --- |
| `LLM_API_KEY` | O | OpenAI 호환 `/chat/completions` API 키 |
| `LLM_BASE_URL` | O | API Base URL (기본: `https://api.openai.com/v1`, 로컬 Ollama/LM Studio 등도 가능) |
| `LLM_MODEL` | O | 모델 이름 (기본: `gpt-4o-mini`) |
| `CHARACTER_NAME` | - | 캐릭터 이름 (기본: `책비서`) |
| `CHARACTER_IMAGE_URL` | - | 캐릭터 이미지 URL (비워두면 기본 이모지 📚) |
| `LIVE2D_MODEL_URL` | - | Live2D 모델(.model3.json) 직접 호스팅 URL. 설정하면 `CHARACTER_IMAGE_URL`보다 우선 적용됨. live2d.com 샘플은 라이선스 동의 후 다운로드해서 직접 호스팅해야 함(핫링크 불가) |
| `SYSTEM_PROMPT` | - | AI 페르소나 프롬프트. `{character_name}` 자리는 자동 치환. 비워두면 코드 내장 기본값 사용 |

## 채팅 명령어

전부 `/`로 시작하며, LLM 호출 없이 코드에서 바로 처리한다(빠르고 비용이 안 듦).

### 서재 관련
- `/완독 <책 제목>`, `/읽는중 <책 제목>`, `/읽을예정 <책 제목>` - 독서 상태 저장
- `/상태` - 지금 "읽는 중"인 책 목록, `/상태 <책 제목>` - 특정 책 상태 조회
- `/랜덤` - 서재에서 무작위로 한 권 추천 (자연어 "아무거나/무작위"도 인식)
- `/통계` - 총 소장 권수 + 저자 Top 5
- `/시리즈 <이름>` - 시리즈 컬럼이 있을 때 해당 시리즈 권수 집계
- `/명언` - 서평/줄거리 컬럼에서 랜덤 발췌
- `/외부검색 <책 제목>` - unified_book 플러그인 연동, 서재 밖(교보문고/리디북스 등) 검색
- `/퀴즈` - cover_quiz(책표지 퀴즈) 탭 안내

일반 대화(명령어가 아닌 메시지)는 서재 검색 결과 + 평점/장르 필터 + "읽는 중" 목록을
근거로 LLM이 답한다. 평점 필터는 "평점 4점 이상"처럼 자연어로 인식된다.

### 책과 무관한 부가 명령
- `/날씨 <지역>` - 네이버 검색 날씨 위젯 스크래핑 (API 키 불필요, 다소 취약할 수 있음)
- `/주식 <종목명 또는 코드>` - 네이버 금융 비공식 공개 API (API 키 불필요)
- `/환율 <통화>` - open.er-api.com (API 키 불필요)
- `/로또` - smok95/lotto 커뮤니티 미러(GitHub Pages) - 동행복권 공식 API는
  최근 봇 차단으로 사용 불가
- `/코인 <이름 또는 티커>` - CoinGecko 공개 API (API 키 불필요)
- `/운세` - LLM이 즉석에서 지어냄

## 특이사항 / 알려진 제약

- **DB 스키마 의존**: 서재 관련 기능은 `books` 테이블을 전제로 한다. 컬럼(서평/평점/
  장르/시리즈)은 `PRAGMA table_info(books)`로 자동 탐지하지만, 세션에 따라
  테이블 자체가 다르면(예: 오디오북/비디오) 해당 기능만 조용히 빈 결과로
  실패한다. 반대로 날씨/주식/환율/로또/코인처럼 DB에 의존하지 않는 명령은
  세션과 무관하게 항상 동작한다.
- **비공식 API 의존**: 날씨(네이버 스크래핑)와 주식(네이버 비공식 JSON)은
  공식 문서화된 API가 아니라서, 상대 사이트가 구조를 바꾸면 예고 없이 깨질
  수 있다. 로또도 동행복권 공식 API가 막혀서 커뮤니티 미러로 대체한
  상태다.
- **캐릭터 감정 표현**: 답변 문구에 "축하/완독" 등이 있으면 잠깐 🎉로,
  "못 찾음/오류/미안" 등이 있으면 잠깐 😥로 아바타가 바뀌었다가 원래
  모습으로 돌아온다. 별도 설정 없이 항상 동작하며, Live2D가 활성화된
  경우에는 건너뛴다.
- **채팅 기록 영구 저장**: 최근 40개 메시지까지 플러그인 설정 저장소에
  저장돼서, 새로고침 후 마스코트를 다시 열어도 이전 대화가 복원된다.
- **다른 플러그인 연동**: `unified_book`, `cover_quiz`를 같은 모듈 경로
  규칙(`plugins/metadata/<id>/<id>.py`, 클래스명 `<PascalCase><Id>MetadataProvider`)으로
  동적 import해서 호출한다. 공식 플러그인 레지스트리 API가 있다면
  `_get_sibling_plugin()`을 그걸로 바꾸는 게 더 안전하다.
