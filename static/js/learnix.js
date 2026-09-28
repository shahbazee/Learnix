/**
 * Learnix Modern Client Engine & Processing Feedback System
 * 
 * Features:
 * - Ultra-slim gradient top progress bar (NProgress style, non-blocking)
 * - Subtle floating status pill (delayed threshold: only appears if action takes >350ms)
 * - Layout-stable button locking with inline SVG spinner (prevents duplicate clicks)
 * - Instant page delivery with zero artificial delays
 * - BFCache & error recovery (pageshow, popstate, error handlers)
 */

(function () {
  'use strict';

  const LearnixLoader = {
    progressBar: null,
    overlay: null,
    statusText: null,

    // Timers & State
    progressInterval: null,
    delayedPillTimer: null,
    safetyTimeoutId: null,
    currentProgress: 0,
    isActive: false,

    init() {
      this.progressBar = document.getElementById('learnixProgressBar');
      this.overlay = document.getElementById('learnixGlobalLoader');
      this.statusText = document.getElementById('learnixLoaderStatusText');

      this.attachNavigationInterceptors();
      this.attachFormInterceptors();
      this.attachLifecycleHandlers();
    },

    /* ==========================================================================
       1. Top Progress Bar Engine (Smooth, Non-Blocking)
       ========================================================================== */
    startProgress() {
      if (!this.progressBar) {
        this.progressBar = document.getElementById('learnixProgressBar');
      }
      if (!this.progressBar) return;

      clearInterval(this.progressInterval);
      this.currentProgress = 15 + Math.random() * 10; // Instantly jump to 15-25%

      this.progressBar.classList.remove('is-finished');
      this.progressBar.classList.add('is-active');
      this.progressBar.style.width = `${this.currentProgress}%`;

      // Trickle progress slowly up to ~85%
      this.progressInterval = setInterval(() => {
        if (this.currentProgress < 50) {
          this.currentProgress += Math.random() * 8 + 4;
        } else if (this.currentProgress < 75) {
          this.currentProgress += Math.random() * 4 + 2;
        } else if (this.currentProgress < 88) {
          this.currentProgress += Math.random() * 1.5 + 0.5;
        }
        if (this.progressBar) {
          this.progressBar.style.width = `${Math.min(this.currentProgress, 90)}%`;
        }
      }, 160);
    },

    finishProgress() {
      clearInterval(this.progressInterval);
      if (!this.progressBar) return;

      this.progressBar.style.width = '100%';
      this.progressBar.classList.add('is-finished');

      setTimeout(() => {
        if (this.progressBar) {
          this.progressBar.classList.remove('is-active', 'is-finished');
          this.progressBar.style.width = '0%';
        }
      }, 250);
    },

    /* ==========================================================================
       2. Floating Processing Pill (Thresholded for Long Requests)
       ========================================================================== */
    showPill(message = 'Processing...') {
      if (!this.overlay) {
        this.overlay = document.getElementById('learnixGlobalLoader');
        this.statusText = document.getElementById('learnixLoaderStatusText');
      }
      if (!this.overlay) return;

      if (this.statusText && message) {
        this.statusText.textContent = message;
      }
      this.overlay.classList.add('active');
      this.overlay.setAttribute('aria-hidden', 'false');
    },

    hidePill() {
      if (!this.overlay) return;
      this.overlay.classList.remove('active');
      this.overlay.setAttribute('aria-hidden', 'true');
    },

    /* ==========================================================================
       3. Global Show / Hide Coordinator
       ========================================================================== */
    show(message = 'Processing...', options = {}) {
      this.isActive = true;
      clearTimeout(this.delayedPillTimer);
      clearTimeout(this.safetyTimeoutId);

      // Start the top progress bar immediately
      this.startProgress();

      // For instant navigations (<350ms), we do NOT show any screen pill.
      // Only show the floating pill if the action takes longer than 350ms,
      // or if explicitly requested via options.immediate = true
      if (options.immediate) {
        this.showPill(message);
      } else {
        const threshold = options.threshold || 380;
        this.delayedPillTimer = setTimeout(() => {
          if (this.isActive) {
            this.showPill(message);
          }
        }, threshold);
      }

      // Safety fallback: auto-hide after 7s in case connection drops or download starts
      this.safetyTimeoutId = setTimeout(() => {
        this.hide(true);
      }, 7000);
    },

    hide(immediate = false) {
      this.isActive = false;
      clearTimeout(this.delayedPillTimer);
      clearTimeout(this.safetyTimeoutId);

      this.hidePill();
      this.finishProgress();

      // Restore any buttons currently in a loading state
      document.querySelectorAll('.is-loading').forEach((btn) => {
        this.resetButton(btn);
      });
    },

    /* ==========================================================================
       4. Button Loading State (Prevents Double-Clicks & Layout Shifts)
       ========================================================================== */
    inferLoadingText(btn) {
      if (btn.dataset.loadingText) {
        return btn.dataset.loadingText;
      }
      const text = (btn.textContent || '').trim().toLowerCase();
      if (text.includes('sign in') || text.includes('log in')) return 'Signing in...';
      if (text.includes('sign up') || text.includes('register') || text.includes('create account')) return 'Creating account...';
      if (text.includes('verify')) return 'Verifying...';
      if (text.includes('buy now') || text.includes('pay') || text.includes('checkout')) return 'Redirecting to payment...';
      if (text.includes('enroll')) return 'Enrolling...';
      if (text.includes('save') || text.includes('update')) return 'Saving...';
      if (text.includes('send') || text.includes('resend')) return 'Sending...';
      if (text.includes('search')) return 'Searching...';
      if (text.includes('delete') || text.includes('remove')) return 'Deleting...';
      return 'Processing...';
    },

    setButtonLoading(btn, customMessage = null) {
      if (!btn || btn.classList.contains('is-loading')) return;

      // Lock exact computed width to prevent layout jump
      const currentWidth = btn.getBoundingClientRect().width;
      if (currentWidth > 0) {
        btn.style.minWidth = `${currentWidth}px`;
      }

      // Cache original HTML
      if (!btn.dataset.originalHtml) {
        btn.dataset.originalHtml = btn.innerHTML;
      }

      const message = customMessage || this.inferLoadingText(btn);

      btn.classList.add('is-loading');
      btn.disabled = true;
      btn.setAttribute('aria-busy', 'true');

      // Inject clean SVG spinner with matching text
      btn.innerHTML = `
        <span class="inline-flex items-center justify-center gap-2">
          <svg class="learnix-btn-spinner" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
            <path class="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>${message}</span>
        </span>
      `;
    },

    resetButton(btn) {
      if (!btn || !btn.dataset.originalHtml) return;
      btn.innerHTML = btn.dataset.originalHtml;
      delete btn.dataset.originalHtml;
      btn.style.minWidth = '';
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
      btn.classList.remove('is-loading');
    },

    /* ==========================================================================
       5. Event Interceptors & Lifecycle Handlers
       ========================================================================== */
    attachNavigationInterceptors() {
      document.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;

        const href = link.getAttribute('href');
        if (!href) return;

        // Skip anchors, javascript, mailto, tel, new tabs, downloads, or opted-out links
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

        // Skip modified clicks (new tab, new window, background)
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
        this.show(label, { threshold: 380 });
      });
    },

    attachFormInterceptors() {
      document.addEventListener('submit', (e) => {
        const form = e.target;
        if (!form || form.dataset.noLoader !== undefined || form.getAttribute('target') === '_blank') {
          return;
        }

        // Check HTML5 validation before triggering loading state
        if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
          return;
        }

        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        const customText = form.dataset.loadingText || (submitBtn ? submitBtn.dataset.loadingText : null);

        if (submitBtn) {
          this.setButtonLoading(submitBtn, customText);
        }

        const pillLabel = customText || (submitBtn ? this.inferLoadingText(submitBtn) : 'Processing...');
        // Delayed pill appears after 450ms if the server response takes longer
        this.show(pillLabel, { threshold: 450 });
      });
    },

    attachLifecycleHandlers() {
      // Dismiss on back/forward browser cache navigation or full reload
      window.addEventListener('pageshow', () => {
        this.hide(true);
      });

      window.addEventListener('popstate', () => {
        this.hide(true);
      });

      // Emergency reset on escape key
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isActive) {
          this.hide(true);
        }
      });

      // Cleanup loading state if unhandled errors occur during client execution
      window.addEventListener('error', () => {
        this.hide(true);
      });

      window.addEventListener('unhandledrejection', () => {
        this.hide(true);
      });
    },

    /* ==========================================================================
       6. Async Helper Method
       ========================================================================== */
    async withLoading(promiseOrAsyncFn, message = 'Processing...') {
      this.show(message, { immediate: true });
      try {
        const result = typeof promiseOrAsyncFn === 'function' ? await promiseOrAsyncFn() : await promiseOrAsyncFn;
        return result;
      } finally {
        this.hide(true);
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
