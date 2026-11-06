// 독서도우미 홈 위젯 - core가 new Function('pluginId', 'shadowRoot', 'items', 이 파일)로 실행한다.
// 카드 자체는 바로가기일 뿐이고, 진짜 일은 마스코트(script.js)를 화면 전체에 띄우는 것이다:
// 독서도우미 탭과 같은 script.js를 /ui 번들에서 받아 container 없이 실행하면, 마스코트가
// document.body에 붙어서 홈에서 다른 메뉴로 옮겨가도 계속 떠 있다. 이미 떠 있으면(탭을
// 열었거나 홈을 다시 그린 경우) 다시 실행하지 않는다.
(function () {
  const card = shadowRoot.querySelector('.ym_rdw');
  if (!card) return;
  const nameEl = card.querySelector('[data-ym-name]');
  const statusEl = card.querySelector('[data-ym-status]');
  const openBtn = card.querySelector('[data-ym-open]');

  const info = (Array.isArray(items) ? items : []).find((i) => i && i.widget_type === 'reading_doumi');
  if (info && info.character_name) nameEl.textContent = String(info.character_name);

  const MASCOT_ID = 'ym_reading-mate-mascot';

  // ------------------------------------------------------------------
  // 평소에는 코어가 그리는 제목줄(아이콘·제목·제공·×)만 보이게 카드 본문을 접어
  // 둔다. 제목줄을 누르면 펼치고/접고, 상태는 이 브라우저에 기억한다.
  // 제목줄과 본문(.plugin-widget-body)은 Shadow DOM 밖(코어 마크업)이라
  // shadowRoot.host에서 거슬러 올라가 찾는다. 코어 마크업이 바뀌어 못 찾으면
  // 접지 않고 그대로 보여준다.
  // ------------------------------------------------------------------
  const YM_OPEN_KEY = 'ym_reading_doumi_widget_open';
  const slot = shadowRoot.host && shadowRoot.host.closest('.home-widget-slot');
  const header = slot && slot.querySelector('.plugin-card-header');
  const body = slot && slot.querySelector('.plugin-widget-body');
  if (slot && header && body && !slot.dataset.ymCollapsible) {
    slot.dataset.ymCollapsible = '1';
    let open = false;
    try { open = localStorage.getItem(YM_OPEN_KEY) === '1'; } catch (e) { /* 저장소 막힘 - 접힌 채로 */ }
    const apply = () => {
      body.style.display = open ? '' : 'none';
      header.style.cursor = 'pointer';
      header.setAttribute('aria-expanded', open ? 'true' : 'false');
      header.title = open ? '눌러서 접기' : '눌러서 펼치기';
    };
    header.addEventListener('click', (e) => {
      // 제거(×) 버튼은 코어 동작 그대로 둔다.
      if (e.target.closest('.home-widget-remove-btn')) return;
      open = !open;
      try { localStorage.setItem(YM_OPEN_KEY, open ? '1' : '0'); } catch (err) { /* 무시 */ }
      apply();
    });
    apply();
  }

  function ym_mountMascot() {
    if (document.getElementById(MASCOT_ID)) return Promise.resolve();
    // 홈 위젯이 거의 동시에 두 번 그려져도 번들은 한 번만 받는다.
    if (window.__ymReadingDoumiMounting) return window.__ymReadingDoumiMounting;
    window.__ymReadingDoumiMounting = fetch('/api/media/plugins/' + encodeURIComponent(pluginId) + '/ui', {
      credentials: 'same-origin',
    })
      .then((res) => res.json())
      .then((data) => {
        const js = data && data.success && data.bundle && data.bundle.js;
        if (!js) throw new Error((data && data.error) || 'script.js를 받지 못했어요');
        if (document.getElementById(MASCOT_ID)) return;
        new Function('pluginId', 'container', js)(pluginId, null);
      })
      .finally(() => { window.__ymReadingDoumiMounting = null; });
    return window.__ymReadingDoumiMounting;
  }

  function ym_openChat() {
    if (typeof window.ymReadingDoumiOpen === 'function') {
      window.ymReadingDoumiOpen();
      return;
    }
    // 예전 버전 script.js가 이미 떠 있는 경우 - 아바타를 대신 눌러준다.
    const avatar = document.getElementById('ym_rm-avatar-btn');
    if (avatar) avatar.click();
  }

  statusEl.textContent = '마스코트 준비 중...';
  ym_mountMascot()
    .then(() => { statusEl.textContent = ''; })
    .catch((err) => {
      console.error('[Reading-Doumi-Widget] 마스코트를 띄우지 못했어요:', err);
      statusEl.textContent = '마스코트를 띄우지 못했어요.';
    });

  openBtn.addEventListener('click', () => {
    ym_mountMascot().then(ym_openChat).catch(() => {
      statusEl.textContent = '마스코트를 띄우지 못했어요.';
    });
  });
})();
