(function () {
  // 이 파일은 core가 `new Function('pluginId', 'container', bundle.js)`로 감싸서
  // 실행한다 - 즉 'pluginId'와 'container'는 이미 파라미터로 주어진 전역 스코프
  // 변수이며, 아래 IIFE는 그 값을 그대로 클로저로 캡처해서 쓴다.
  //
  // 이 IIFE 안의 지역 변수/함수 자체는 플러그인마다 독립된 함수 스코프라 원래도
  // 다른 플러그인과 충돌하지 않지만, 마스코트가 document.body/head에 직접
  // 엘리먼트/스타일을 붙이는 부분(진짜로 전역 DOM 이름공간을 쓰는 부분)은
  // 다른 플러그인과 겹칠 수 있으므로 모든 식별자에 ym_ 접두사를 붙여 통일했다.
  const YM_LOG_PREFIX = '[Reading-Doumi-Plugin]';
  // 위젯 데이터 엔드포인트는 플러그인 id를 그대로 쓴다 - id가 reading_doumi로
  // 바뀌었으니 여기도 함께 맞춰야 한다 (안 맞추면 404가 난다).
  const YM_DATA_URL = '/api/media/dashboard/widgets/reading_doumi/data';

  // 채팅 히스토리는 이 클로저(모듈 스코프 변수)에만 존재한다 - 탭을 옮겨도
  // 살아있지만, 페이지를 새로고침하면 사라진다. 서버에 영구 저장하지 않는 이유는
  // 이 샘플이 "마운트 지속" 패턴 자체를 보여주는 데 집중하기 위함이다. 대화를
  // 새로고침 후에도 이어가고 싶다면 sessionStorage에 history 배열을 그대로
  // 저장/복원하면 된다.
  let ymHistory = [];
  let ymCharacterName = null;
  let ymTtsEnabled = false;

  // Live2D는 필요할 때만(LIVE2D_MODEL_URL이 실제로 설정됐을 때만) CDN에서
  // 지연 로딩한다 - pixi.js + pixi-live2d-display가 꽤 무겁기 때문.
  // Cubism 4(.model3.json) 모델 기준. live2d.com 샘플 중 예전 Cubism 2.1
  // 형식(.model.json) 모델을 쓰려면 이 목록을 cubism2용 번들+런타임으로
  // 바꿔야 한다 (README: https://github.com/guansss/pixi-live2d-display).
  const YM_LIVE2D_LIBS = [
    'https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js',
    'https://cdn.jsdelivr.net/npm/pixi.js@6.5.9/dist/browser/pixi.min.js',
    'https://cdn.jsdelivr.net/npm/pixi-live2d-display@0.4.0/dist/cubism4.min.js',
  ];
  let ymLive2DLoadPromise = null;
  let ymLive2DApp = null;

  // ------------------------------------------------------------------
  // 1) 마스코트 전용 CSS를 document.head에 직접 주입한다.
  //    이유: style.css는 카테고리 탭 컨테이너 안에서만 살아있고, 다른 탭으로
  //    이동하면 코어가 그 컨테이너를 통째로 갈아치우면서 함께 사라진다.
  //    마스코트는 document.body에 붙어 탭을 넘어 계속 떠 있어야 하므로,
  //    스타일도 독립적으로 살려둔다 (spotify_mood 샘플의 플로팅 플레이어와 동일한 트릭).
  // ------------------------------------------------------------------
  function ym_ensureMascotStyle() {
    if (document.getElementById('ym_reading-mate-mascot-style')) return;
    const style = document.createElement('style');
    style.id = 'ym_reading-mate-mascot-style';
    style.textContent = `
      #ym_reading-mate-mascot {
        position: fixed;
        right: 1.25rem;
        bottom: 1.25rem;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        font-family: inherit;
      }
      #ym_reading-mate-mascot .ym_rm-avatar-btn {
        width: 64px;
        height: 64px;
        border-radius: 50%;
        border: 2px solid var(--app-accent, #7c5cff);
        background: var(--app-bg-card, #1e1e2e);
        cursor: pointer;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        box-shadow: 0 6px 18px rgba(0,0,0,0.35);
        padding: 0;
      }
      #ym_reading-mate-mascot .ym_rm-avatar-btn img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      @keyframes ym_rm_emotion_pop {
        0% { transform: scale(0.6); opacity: 0; }
        60% { transform: scale(1.15); opacity: 1; }
        100% { transform: scale(1); opacity: 1; }
      }
      #ym_reading-mate-mascot .ym_rm-emotion-flash {
        display: inline-block;
        animation: ym_rm_emotion_pop 0.25s ease-out;
      }
      #ym_reading-mate-mascot .ym_rm-live2d-canvas {
        display: none;
        width: 140px;
        height: 200px;
        cursor: pointer;
        background: transparent;
        filter: drop-shadow(0 6px 14px rgba(0,0,0,0.35));
      }
      #ym_reading-mate-mascot .ym_rm-chat-panel {
        width: 320px;
        max-width: calc(100vw - 2rem);
        max-height: 420px;
        margin-bottom: 0.6rem;
        display: none;
        flex-direction: column;
        background: var(--app-bg-card, #1e1e2e);
        border: 1px solid var(--app-border, #333);
        border-radius: 12px;
        box-shadow: 0 10px 28px rgba(0,0,0,0.4);
        overflow: hidden;
      }
      #ym_reading-mate-mascot .ym_rm-chat-panel.ym_open { display: flex; }
      #ym_reading-mate-mascot .ym_rm-chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.55rem 0.75rem;
        background: var(--app-bg-sidebar, #181825);
        color: var(--app-text-primary, #eee);
        font-size: 0.85rem;
        font-weight: 600;
      }
      #ym_reading-mate-mascot .ym_rm-chat-header-actions {
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }
      #ym_reading-mate-mascot .ym_rm-chat-tts {
        background: none;
        border: none;
        color: inherit;
        opacity: 0.7;
        cursor: pointer;
        font-size: 0.85rem;
        line-height: 1;
        padding: 0;
      }
      #ym_reading-mate-mascot .ym_rm-chat-tts:hover { opacity: 1; }
      #ym_reading-mate-mascot .ym_rm-chat-tts.ym_rm-chat-tts--on {
        opacity: 1;
        color: var(--app-accent, #7c5cff);
      }
      #ym_reading-mate-mascot .ym_rm-chat-close {
        background: none;
        border: none;
        color: inherit;
        cursor: pointer;
        font-size: 1rem;
        line-height: 1;
      }
      #ym_reading-mate-mascot .ym_rm-chat-body {
        flex: 1;
        overflow-y: auto;
        padding: 0.6rem 0.7rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        font-size: 0.85rem;
        /* 얇은 스크롤바 - Firefox */
        scrollbar-width: thin;
        scrollbar-color: var(--app-border, #444) transparent;
      }
      #ym_reading-mate-mascot .ym_rm-chat-body::-webkit-scrollbar {
        width: 6px;
      }
      #ym_reading-mate-mascot .ym_rm-chat-body::-webkit-scrollbar-track {
        background: transparent;
      }
      #ym_reading-mate-mascot .ym_rm-chat-body::-webkit-scrollbar-thumb {
        background: var(--app-border, #444);
        border-radius: 4px;
      }
      #ym_reading-mate-mascot .ym_rm-bubble {
        max-width: 85%;
        padding: 0.5rem 0.7rem;
        border-radius: 10px;
        line-height: 1.4;
      }
      #ym_reading-mate-mascot .ym_rm-bubble-text {
        white-space: pre-wrap;
      }
      #ym_reading-mate-mascot .ym_rm-bubble-time {
        margin-top: 0.2rem;
        font-size: 0.68rem;
        opacity: 0.6;
      }
      #ym_reading-mate-mascot .ym_rm-bubble.ym_rm-bubble--assistant {
        align-self: flex-start;
        background: var(--app-bg-sidebar, #181825);
        color: var(--app-text-primary, #eee);
      }
      #ym_reading-mate-mascot .ym_rm-bubble.ym_rm-bubble--user {
        align-self: flex-end;
        background: var(--app-accent, #7c5cff);
        color: #fff;
      }
      #ym_reading-mate-mascot .ym_rm-bubble.ym_rm-bubble--user .ym_rm-bubble-time {
        text-align: right;
      }
      #ym_reading-mate-mascot .ym_rm-bubble.ym_rm-bubble--pending { opacity: 0.6; }
      #ym_reading-mate-mascot .ym_rm-chat-form {
        display: flex;
        gap: 0.4rem;
        padding: 0.6rem;
        border-top: 1px solid var(--app-border, #333);
      }
      #ym_reading-mate-mascot .ym_rm-chat-form input {
        flex: 1;
        min-width: 0;
        padding: 0.45rem 0.6rem;
        border-radius: 8px;
        border: 1px solid var(--app-border, #333);
        background: var(--app-bg-main, #11111b);
        color: var(--app-text-primary, #eee);
      }
      #ym_reading-mate-mascot .ym_rm-chat-form button {
        border: none;
        border-radius: 8px;
        background: var(--app-accent, #7c5cff);
        color: #fff;
        padding: 0 0.8rem;
        cursor: pointer;
      }
    `;
    document.head.appendChild(style);
  }

  // ------------------------------------------------------------------
  // 2) 마스코트 DOM을 document.body에 (컨테이너 밖에) 만든다 - 이미 있으면 재사용.
  // ------------------------------------------------------------------
  function ym_ensureMascot() {
    ym_ensureMascotStyle();

    let host = document.getElementById('ym_reading-mate-mascot');
    if (host) return host;

    host = document.createElement('div');
    host.id = 'ym_reading-mate-mascot';
    host.innerHTML = `
      <div class="ym_rm-chat-panel" id="ym_rm-chat-panel">
        <div class="ym_rm-chat-header">
          <span id="ym_rm-chat-title">독서메이트</span>
          <div class="ym_rm-chat-header-actions">
            <button type="button" class="ym_rm-chat-tts" id="ym_rm-chat-tts" title="답변 음성으로 읽어주기 켜기/끄기">
              <i class="fa-solid fa-volume-xmark"></i>
            </button>
            <button type="button" class="ym_rm-chat-close" id="ym_rm-chat-close" title="닫기">&times;</button>
          </div>
        </div>
        <div class="ym_rm-chat-body" id="ym_rm-chat-body"></div>
        <form class="ym_rm-chat-form" id="ym_rm-chat-form">
          <input id="ym_rm-chat-input" type="text" placeholder="어떤 책이 읽고 싶은지 물어보세요..." autocomplete="off">
          <button type="submit"><i class="fa-solid fa-paper-plane"></i></button>
        </form>
      </div>
      <button type="button" class="ym_rm-avatar-btn" id="ym_rm-avatar-btn" title="독서메이트에게 물어보기">
        <span id="ym_rm-avatar-fallback">📚</span>
      </button>
      <canvas class="ym_rm-live2d-canvas" id="ym_rm-live2d-canvas" title="독서메이트에게 물어보기"></canvas>
    `;
    document.body.appendChild(host);

    const avatarBtn = host.querySelector('#ym_rm-avatar-btn');
    const live2dCanvas = host.querySelector('#ym_rm-live2d-canvas');
    const panel = host.querySelector('#ym_rm-chat-panel');
    const closeBtn = host.querySelector('#ym_rm-chat-close');
    const ttsBtn = host.querySelector('#ym_rm-chat-tts');
    const form = host.querySelector('#ym_rm-chat-form');
    const input = host.querySelector('#ym_rm-chat-input');

    ttsBtn.addEventListener('click', () => {
      ymTtsEnabled = !ymTtsEnabled;
      ttsBtn.classList.toggle('ym_rm-chat-tts--on', ymTtsEnabled);
      ttsBtn.innerHTML = ymTtsEnabled
        ? '<i class="fa-solid fa-volume-high"></i>'
        : '<i class="fa-solid fa-volume-xmark"></i>';
      if (!ymTtsEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    });

    const ym_toggleChat = () => {
      panel.classList.toggle('ym_open');
      if (panel.classList.contains('ym_open') && ymHistory.length === 0) {
        ym_fetchReply(''); // 첫 오픈 시 인사말 요청
      }
    };

    avatarBtn.addEventListener('click', ym_toggleChat);
    // Live2D 캔버스는 pointertap(모델 자체 클릭 이벤트)이 잡지 못하는 여백을
    // 클릭했을 때를 대비해 캔버스 자체에도 같은 토글을 걸어둔다. 모델의
    // pointertap 쪽은 ym_setupLive2D()에서 별도로 건다.
    live2dCanvas.addEventListener('click', ym_toggleChat);
    closeBtn.addEventListener('click', () => panel.classList.remove('ym_open'));

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = (input.value || '').trim();
      if (!text) return;
      input.value = '';
      ym_sendMessage(text);
    });

    return host;
  }

  function ym_speak(text) {
    if (!ymTtsEnabled || !text || !('speechSynthesis' in window)) return;
    try {
      // 이전 발화가 남아있으면 겹치지 않게 취소하고 새로 읽는다.
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = 'ko-KR';
      window.speechSynthesis.speak(utter);
    } catch (e) {
      console.error(YM_LOG_PREFIX, 'TTS 실패:', e);
    }
  }

  // speak: false를 넘기면(예: 이전 대화 복원 시) 답변이어도 소리 내어 읽지
  // 않는다 - 과거 대화를 한꺼번에 낭독하는 걸 막기 위함.
  function ym_appendBubble(role, text, pending, speak) {
    const body = document.getElementById('ym_rm-chat-body');
    if (!body) return null;
    const bubble = document.createElement('div');
    bubble.className = 'ym_rm-bubble ym_rm-bubble--' + role + (pending ? ' ym_rm-bubble--pending' : '');

    const textEl = document.createElement('div');
    textEl.className = 'ym_rm-bubble-text';
    textEl.textContent = text;
    bubble.appendChild(textEl);

    if (!pending) {
      const timeEl = document.createElement('div');
      timeEl.className = 'ym_rm-bubble-time';
      timeEl.textContent = new Date().toLocaleTimeString('ko-KR', { hour: 'numeric', minute: '2-digit' });
      bubble.appendChild(timeEl);
    }

    body.appendChild(bubble);
    body.scrollTop = body.scrollHeight;

    if (role === 'assistant' && !pending && speak !== false) {
      ym_speak(text);
    }
    return bubble;
  }

  function ym_setAvatarImage(url) {
    const fallback = document.getElementById('ym_rm-avatar-fallback');
    if (!url || !fallback || fallback.dataset.applied) return;
    fallback.dataset.applied = '1';
    const img = document.createElement('img');
    img.src = url;
    img.alt = ymCharacterName || '독서메이트';
    fallback.replaceWith(img);
  }

  // ------------------------------------------------------------------
  // 캐릭터 감정 표현 - Live2D 없이도 표정 변화를 흉내낸다. 서버가 답변
  // 내용을 보고 'celebrate'/'sorry'/'normal' 중 하나를 emotion으로 실어
  // 보내주면, 'normal'이 아닐 때만 아바타를 잠깐 다른 이모지로 바꿨다가
  // 원래 모습(커스텀 이미지든 기본 이모지든)으로 되돌린다.
  // ------------------------------------------------------------------
  const YM_EMOTION_EMOJI = { celebrate: '🎉', sorry: '😥' };
  const YM_EMOTION_FLASH_MS = 2500;
  let ymEmotionRevertTimer = null;

  function ym_flashEmotion(emotion) {
    const emoji = YM_EMOTION_EMOJI[emotion];
    if (!emoji) return; // 'normal'이거나 알 수 없는 값이면 그대로 둔다

    const avatarBtn = document.getElementById('ym_rm-avatar-btn');
    const live2dCanvas = document.getElementById('ym_rm-live2d-canvas');
    // Live2D가 이미 활성화된 상태(캔버스가 보임)라면 정적 이모지 흉내는 건너뛴다.
    if (live2dCanvas && live2dCanvas.style.display === 'block') return;
    if (!avatarBtn) return;

    if (ymEmotionRevertTimer) {
      window.clearTimeout(ymEmotionRevertTimer);
      ymEmotionRevertTimer = null;
    }

    // 이미 되돌릴 원본을 기억해둔 상태가 아니라면(=지금이 첫 깜빡임이라면)
    // 지금 모습(커스텀 이미지 또는 기본 이모지)을 원본으로 저장해둔다.
    if (!avatarBtn.dataset.ymOriginalHtml) {
      avatarBtn.dataset.ymOriginalHtml = avatarBtn.innerHTML;
    }

    avatarBtn.innerHTML = '<span class="ym_rm-emotion-flash">' + emoji + '</span>';

    ymEmotionRevertTimer = window.setTimeout(() => {
      if (avatarBtn.dataset.ymOriginalHtml) {
        avatarBtn.innerHTML = avatarBtn.dataset.ymOriginalHtml;
        delete avatarBtn.dataset.ymOriginalHtml;
      }
      ymEmotionRevertTimer = null;
    }, YM_EMOTION_FLASH_MS);
  }

  // ------------------------------------------------------------------
  // Live2D 모델 로딩 - LIVE2D_MODEL_URL이 설정된 경우에만 호출된다.
  // pixi.js + pixi-live2d-display를 CDN에서 순서대로 로드한 뒤, 캔버스에
  // Cubism 4 모델을 띄우고 기본 아바타 버튼을 숨긴다. 무엇이든 실패하면
  // 콘솔에만 로그를 남기고 기존 이미지/이모지 아바타를 그대로 둔다.
  // ------------------------------------------------------------------
  function ym_loadScriptOnce(src) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-ym-live2d-src="' + src + '"]');
      if (existing) {
        if (existing.dataset.loaded === '1') { resolve(); return; }
        existing.addEventListener('load', () => resolve());
        existing.addEventListener('error', () => reject(new Error('script load 실패: ' + src)));
        return;
      }
      const s = document.createElement('script');
      s.src = src;
      s.dataset.ymLive2dSrc = src;
      s.onload = () => { s.dataset.loaded = '1'; resolve(); };
      s.onerror = () => reject(new Error('script load 실패: ' + src));
      document.head.appendChild(s);
    });
  }

  function ym_ensureLive2DLibs() {
    if (!ymLive2DLoadPromise) {
      ymLive2DLoadPromise = YM_LIVE2D_LIBS.reduce(
        (p, src) => p.then(() => ym_loadScriptOnce(src)),
        Promise.resolve()
      );
    }
    return ymLive2DLoadPromise;
  }

  function ym_setupLive2D(modelUrl) {
    const canvas = document.getElementById('ym_rm-live2d-canvas');
    const avatarBtn = document.getElementById('ym_rm-avatar-btn');
    if (!canvas || !modelUrl || canvas.dataset.applied) return;
    canvas.dataset.applied = '1';

    ym_ensureLive2DLibs()
      .then(() => {
        // pixi-live2d-display는 window.PIXI.Ticker를 자동으로 찾아 쓴다.
        ymLive2DApp = new window.PIXI.Application({
          view: canvas,
          width: 140,
          height: 200,
          backgroundAlpha: 0,
        });
        return window.PIXI.live2d.Live2DModel.from(modelUrl);
      })
      .then((model) => {
        ymLive2DApp.stage.addChild(model);

        const scale = Math.min(140 / model.width, 200 / model.height) * 0.9;
        model.scale.set(scale);
        model.x = (140 - model.width * scale) / 2;
        model.y = 200 - model.height * scale;

        model.interactive = true;
        model.cursor = 'pointer';
        model.on('pointertap', () => {
          const panel = document.getElementById('ym_rm-chat-panel');
          if (panel) {
            panel.classList.toggle('ym_open');
            if (panel.classList.contains('ym_open') && ymHistory.length === 0) {
              ym_fetchReply('');
            }
          }
          // 모델에 모션이 있으면 탭할 때마다 살짝 반응하게 - 모델마다 모션
          // 그룹 이름이 달라서 실패해도 무시한다.
          try { model.motion('TapBody'); } catch (e) { /* 이 모델엔 없는 모션 - 무시 */ }
        });

        canvas.style.display = 'block';
        if (avatarBtn) avatarBtn.style.display = 'none';
      })
      .catch((err) => {
        console.error(YM_LOG_PREFIX, 'Live2D 로딩 실패, 기본 이미지로 대체:', err);
        canvas.style.display = 'none';
        if (avatarBtn) avatarBtn.style.display = 'flex';
      });
  }

  function ym_fetchReply(userText) {
    const params = new URLSearchParams({
      message: userText || '',
      history: JSON.stringify(ymHistory),
    });

    let pendingBubble = null;
    if (userText) {
      pendingBubble = ym_appendBubble('assistant', '생각 중...', true);
    }

    fetch(YM_DATA_URL + '?' + params.toString())
      .then((res) => res.json())
      .then((data) => {
        if (pendingBubble) pendingBubble.remove();

        if (!data.success) {
          ym_appendBubble('assistant', data.error || '오류가 발생했어요.');
          return;
        }

        if (data.character_name) {
          ymCharacterName = data.character_name;
          const title = document.getElementById('ym_rm-chat-title');
          if (title) title.textContent = ymCharacterName;
        }
        if (data.character_image_url) {
          ym_setAvatarImage(data.character_image_url);
        }
        if (data.character_live2d_url) {
          ym_setupLive2D(data.character_live2d_url);
        }

        // 서버에 영구 저장된 이전 대화 기록이 있으면(마스코트를 처음 여는
        // 시점에 message='' 로 호출했을 때) 그걸 그대로 복원해서 보여준다 -
        // 새로고침해도 이전 대화가 이어지는 것처럼 보인다.
        if (Array.isArray(data.history) && data.history.length) {
          data.history.forEach((turn) => {
            ym_appendBubble(turn.role === 'user' ? 'user' : 'assistant', turn.content || '', false, false);
          });
          ymHistory = data.history.slice();
          return;
        }

        ym_appendBubble('assistant', data.reply || '...');
        if (data.emotion) {
          ym_flashEmotion(data.emotion);
        }
        if (userText) {
          ymHistory.push({ role: 'user', content: userText });
        }
        ymHistory.push({ role: 'assistant', content: data.reply || '' });
      })
      .catch((err) => {
        if (pendingBubble) pendingBubble.remove();
        console.error(YM_LOG_PREFIX, '요청 실패:', err);
        ym_appendBubble('assistant', '서버에 연결할 수 없어요.');
      });
  }

  function ym_sendMessage(text) {
    ym_appendBubble('user', text);
    ym_fetchReply(text);
  }

  // ------------------------------------------------------------------
  // 3) 카테고리 탭(설정/안내 페이지) 쪽 상태 표시 - container 안쪽만 건드린다.
  // ------------------------------------------------------------------
  function ym_renderTabStatus() {
    const status = container.querySelector('#ym_rm-status');
    if (!status) return;
    const host = document.getElementById('ym_reading-mate-mascot');
    status.textContent = host
      ? '마스코트가 우측 하단에 떠 있어요. 아무 곳이나 이동해도 사라지지 않아요.'
      : '마스코트를 준비하는 중...';
  }

  ym_ensureMascot();
  ym_renderTabStatus();
})();
