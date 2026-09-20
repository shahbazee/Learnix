/**
 * Learnix Global Client Engine & Loading Component
 * Stitch Compass Star Indicator Asset
 * Smooth Fade-in/Fade-out • Centered Responsive • Button Locking
 */

(function () {
  'use strict';

  let safetyTimeoutId = null;

  const LearnixLoader = {
    overlay: null,
    statusText: null,

    init() {
      this.overlay = document.getElementById('learnixGlobalLoader');
      this.statusText = document.getElementById('learnixLoaderStatusText');

      if (!this.overlay) return;

      this.attachNavigationInterceptors();
      this.attachFormInterceptors();
      this.attachBfCacheHandler();
    },

    lastShownTime: 0,
    hideTimerId: null,

    /**
     * Shows the global full-screen harmonic equalizer loader with smooth fade-in
     * @param {string} message - Optional status message
     */
    show(message = 'Processing...') {
      if (!this.overlay) {
        this.init();
      }
      if (!this.overlay) return;

      clearTimeout(this.hideTimerId);
      this.lastShownTime = Date.now();

      if (this.statusText && message) {
        this.statusText.textContent = message;
      }

      this.overlay.classList.add('active');
      this.overlay.setAttribute('aria-hidden', 'false');

      // Pause Lenis smooth scrolling while loader is visible
      if (window.lenis && typeof window.lenis.stop === 'function') {
        window.lenis.stop();
      }

      // Safety fallback: auto-hide after 12s in case navigation is cancelled or file download starts
      clearTimeout(safetyTimeoutId);
      safetyTimeoutId = setTimeout(() => {
        this.hide(true);
      }, 12000);
    },

    /**
     * Hides the global loader with smooth fade-out and natural state transition
     * @param {boolean} immediate - If true, ignores minimum animation threshold
     */
    hide(immediate = false) {
      if (!this.overlay) return;

      clearTimeout(safetyTimeoutId);
      clearTimeout(this.hideTimerId);

      const elapsed = Date.now() - (this.lastShownTime || 0);
      // Small smoothing threshold (180ms) prevents jarring flickering on near-instant actions
      const delay = !immediate && elapsed < 180 ? 180 - elapsed : 0;

      this.hideTimerId = setTimeout(() => {
        if (!this.overlay) return;
        this.overlay.classList.remove('active');
        this.overlay.setAttribute('aria-hidden', 'true');

        // Reset any buttons locked in loading state
        document.querySelectorAll('.is-loading').forEach((btn) => {
          this.resetButton(btn);
        });

        // Resume Lenis smooth scroll
        if (window.lenis && typeof window.lenis.start === 'function') {
          window.lenis.start();
        }
      }, delay);
    },

    /**
     * Applies micro harmonic equalizer indicator to a specific button
     * Disables button and prevents duplicate click actions
     * @param {HTMLElement} btn
     * @param {string} message
     */
    setButtonLoading(btn, message = 'Processing...') {
      if (!btn || btn.classList.contains('is-loading')) return;

      btn.classList.add('is-loading');
      btn.disabled = true;
      btn.setAttribute('aria-busy', 'true');

      // Cache original HTML
      if (!btn.dataset.originalHtml) {
        btn.dataset.originalHtml = btn.innerHTML;
      }

      // Render micro icon inside button
      const iconUrl = (this.overlay && this.overlay.dataset.iconUrl) || '/static/images/loader-icon.png';
      btn.innerHTML = `
        <span class="inline-flex items-center gap-2">
          <img src="${iconUrl}" class="learnix-btn-micro-icon" alt="" aria-hidden="true" />
          <span>${message}</span>
        </span>
      `;
    },

    /**
     * Restores button to its original state
     * @param {HTMLElement} btn
     */
    resetButton(btn) {
      if (!btn || !btn.dataset.originalHtml) return;
      btn.innerHTML = btn.dataset.originalHtml;
      delete btn.dataset.originalHtml;
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
      btn.classList.remove('is-loading');
    },

    /**
     * Intercepts valid navigational link clicks
     */
    attachNavigationInterceptors() {
      document.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;

        const href = link.getAttribute('href');
        if (!href) return;

        // Skip non-navigational links
        if (
          href === '#' ||
          href.startsWith('#') ||
          href.startsWith('javascript:') ||
          href.startsWith('mailto:') ||
          href.startsWith('tel:') ||
          link.getAttribute('target') === '_blank' ||
          link.hasAttribute('download') ||
          link.dataset.noLoader !== undefined
        ) {
          return;
        }

        // Skip when modifier keys are pressed (open in background/new tab)
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
          return;
        }

        // Check if link points to same-page anchor
        try {
          const targetUrl = new URL(link.href, window.location.origin);
          if (
            targetUrl.origin === window.location.origin &&
            targetUrl.pathname === window.location.pathname &&
            targetUrl.search === window.location.search &&
            targetUrl.hash
          ) {
            return;
          }
        } catch (_) {}

        const label = link.dataset.loadingText || 'Loading Masterclass...';
        this.show(label);
      });
    },

    /**
     * Intercepts form submissions and shows loader + locks submit button
     */
    attachFormInterceptors() {
      document.addEventListener('submit', (e) => {
        const form = e.target;
        if (!form || form.dataset.noLoader !== undefined || form.getAttribute('target') === '_blank') {
          return;
        }

        // Check HTML5 validation before showing loader
        if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
          return;
        }

        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        const label = form.dataset.loadingText || (submitBtn ? submitBtn.dataset.loadingText : null) || 'Processing...';

        if (submitBtn) {
          this.setButtonLoading(submitBtn, label);
        }

        this.show(label);
      });
    },

    /**
     * Ensures loader is dismissed on back/forward browser cache navigation
     */
    attachBfCacheHandler() {
      window.addEventListener('pageshow', () => {
        this.hide(true);
      });

      // Escape key emergency dismissal
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.overlay && this.overlay.classList.contains('active')) {
          this.hide();
        }
      });
    },

    /**
     * Executes an async operation with automatic loader lifecycle
     * @param {Promise|Function} promiseOrAsyncFn
     * @param {string} message
     */
    async withLoading(promiseOrAsyncFn, message = 'Processing...') {
      this.show(message);
      try {
        const result = typeof promiseOrAsyncFn === 'function' ? await promiseOrAsyncFn() : await promiseOrAsyncFn;
        return result;
      } finally {
        this.hide();
      }
    }
  };

  // Expose to window for global access
  window.LearnixLoader = LearnixLoader;

  // Initialize upon DOM readiness
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => LearnixLoader.init());
  } else {
    LearnixLoader.init();
  }
})();
