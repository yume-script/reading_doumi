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
