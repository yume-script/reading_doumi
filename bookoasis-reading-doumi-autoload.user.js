// ==UserScript==
// @name         BookOasis 독서도우미 마스코트 자동 오픈
// @namespace    ym-reading-doumi-autoload
// @version      1.1
// @description  페이지 로드 시 '플러그인' 탭 -> '독서도우미' 탭을 자동 클릭해 마스코트를 마운트한 뒤 원래 있던 화면(Home)으로 복귀합니다.
// @match        http://your-bookoasis-ip:5930/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ------------------------------------------------------------------
  // 설정값 - 필요하면 이 부분만 수정하세요.
  // ------------------------------------------------------------------
  const PLUGIN_ID = 'reading_doumi';       // 플러그인 id (reading_doumi.py의 id와 동일해야 함)
  const PLUGIN_LABEL_FALLBACK = '독서도우미'; // 텍스트 매칭 폴백용 표시 이름
  const MAX_WAIT_MS = 15000;               // 각 단계별 최대 대기 시간
  const POLL_MS = 300;                     // 폴링 주기
  const RETURN_TO_HOME = true;             // 마운트 후 Home 탭으로 자동 복귀할지 여부
  const DEBUG = true;                      // 콘솔 로그 출력 여부

  const log = (...args) => { if (DEBUG) console.log('[ym-autoload]', ...args); };
  const warn = (...args) => console.warn('[ym-autoload]', ...args);

  function waitFor(label, checkFn, timeoutMs) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const timer = setInterval(() => {
        let el = null;
        try {
          el = checkFn();
        } catch (e) {
          /* DOM이 아직 준비 안 됐을 수 있음 - 다음 폴링에서 재시도 */
        }
        if (el) {
          clearInterval(timer);
          resolve(el);
        } else if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          reject(new Error(`timeout waiting for: ${label}`));
        }
      }, POLL_MS);
    });
  }

  function findDoumiTabButton() {
    // 1순위: data-plugin-tab 속성이 플러그인 id와 일치하는 버튼
    const byAttr = document.querySelector(
      `#plugins-view-tabs [data-plugin-tab="${PLUGIN_ID}"]`
    );
    if (byAttr) return byAttr;

    // 2순위: 탭 버튼 텍스트에 '독서도우미'가 포함된 버튼 (코어가 id 대신 표시명을
    // data-plugin-tab에 넣거나 속성명이 바뀐 경우를 대비한 폴백)
    const buttons = document.querySelectorAll('#plugins-view-tabs button, #plugins-view-tabs .settings-tab-btn');
    for (const b of buttons) {
      if (b.textContent && b.textContent.includes(PLUGIN_LABEL_FALLBACK)) {
        return b;
      }
    }
    return null;
  }

  async function autoOpenMascot() {
    // 이미 마스코트가 떠 있으면 아무것도 하지 않는다 (SPA 내 재실행/중복 실행 방지)
    if (document.getElementById('ym_reading-mate-mascot')) {
      log('마스코트가 이미 떠 있어 건너뜁니다.');
      return;
    }

    try {
      // 1) 사이드바 '플러그인' 메뉴 클릭
      const pluginsMenu = await waitFor(
        '#category-plugins (사이드바 플러그인 메뉴)',
        () => document.getElementById('category-plugins'),
        MAX_WAIT_MS
      );
      pluginsMenu.click();
      log('사이드바 "플러그인" 클릭 완료');

      // 2) 동적으로 생기는 '독서도우미' 탭 버튼이 나타날 때까지 대기 후 클릭
      const doumiTabBtn = await waitFor(
        `#plugins-view-tabs 안의 '${PLUGIN_LABEL_FALLBACK}' 탭 버튼`,
        findDoumiTabButton,
        MAX_WAIT_MS
      );
      doumiTabBtn.click();
      log('"독서도우미" 탭 클릭 완료');

      // 3) script.js가 실행되어 마스코트가 body에 붙을 때까지 대기
      await waitFor(
        '#ym_reading-mate-mascot (마스코트 DOM)',
        () => document.getElementById('ym_reading-mate-mascot'),
        MAX_WAIT_MS
      );
      log('마스코트 마운트 확인됨');

      // 4) 원래 있던 Home 화면으로 조용히 복귀
      //    마스코트는 이미 document.body에 붙어 있어 탭을 옮겨도 사라지지 않는다.
      if (RETURN_TO_HOME) {
        const homeMenu = document.getElementById('category-home');
        if (homeMenu) {
          homeMenu.click();
          log('Home 화면으로 복귀 완료');
        }
      }

      log('독서도우미 마스코트 자동 마운트 완료 ✅');
    } catch (e) {
      warn('자동 마운트 실패 - BookOasis 코어 UI(사이드바/탭 마크업)가 바뀌었을 수 있습니다:', e.message);
      warn('이 경우 스크립트 상단의 셀렉터(#category-plugins, #plugins-view-tabs 등)를 실제 화면 구조에 맞게 다시 확인해주세요.');
    }
  }

  autoOpenMascot();
})();
