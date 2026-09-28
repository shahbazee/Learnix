/**
 * Learnix Smooth & Fluid Scrolling Engine (Powered by Lenis)
 * 
 * Provides luxury-grade kinetic momentum for mouse-wheel, trackpad responsiveness,
 * floating navbar clearance on anchor navigation, and modal scroll containment.
 * 
 * Optimized Configuration:
 * - lerp: 0.12 (Immediate response, buttery-smooth linear interpolation, rapid natural settling)
 * - Zero artificial duration lag (eliminates 1.15s delayed movement & excessive inertia)
 * - wheelMultiplier: 1.0 (True 1:1 input responsiveness on mouse wheel)
 * - touchMultiplier: 1.0 (Balanced, natural trackpad and touch navigation without overshoot)
 */
(function() {
  'use strict';

  // Respect user accessibility preference
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  // Ensure Lenis constructor is available
  if (typeof Lenis === 'undefined') {
    console.warn('Lenis library not loaded; falling back to native scrolling.');
    return;
  }

  // Initialize Lenis with optimized kinetic physics
  // lerp: 0.12 provides instantaneous input response, subtle luxury smoothing,
  // and rapid natural deceleration without sluggishness or excessive inertia.
  const lenis = new Lenis({
    lerp: 0.12,
    orientation: 'vertical',
    gestureOrientation: 'vertical',
    smoothWheel: true,
    wheelMultiplier: 1.0,
    touchMultiplier: 1.0,
    syncTouch: false,
    infinite: false,
    autoResize: true,
  });

  // Animation frame runner using requestAnimationFrame
  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  // Expose global instance for application-wide control
  window.lenis = lenis;

  // Floating navbar offset (5.5rem = 88px clearance)
  const NAVBAR_OFFSET = -88;

  // Exponential ease-out function for smooth anchor navigations
  const smoothEaseOut = (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t));

  // Smooth Anchor Navigation with swift, graceful duration
  document.addEventListener('click', function(e) {
    const link = e.target.closest('a[href*="#"]');
    if (!link) return;

    const href = link.getAttribute('href');
    if (!href || href === '#' || href.startsWith('#!')) return;

    try {
      const url = new URL(link.href, window.location.href);
      if (url.pathname === window.location.pathname && url.hash) {
        const targetElement = document.querySelector(url.hash);
        if (targetElement) {
          e.preventDefault();
          lenis.scrollTo(targetElement, {
            offset: NAVBAR_OFFSET,
            duration: 0.75, // Swift, polished section glide without dragging
            easing: smoothEaseOut,
          });

          if (history.pushState) {
            history.pushState(null, '', url.hash);
          } else {
            window.location.hash = url.hash;
          }
        }
      }
    } catch (err) {
      // Ignore invalid URLs
    }
  });

  // Handle incoming hash on page load
  window.addEventListener('load', function() {
    if (window.location.hash) {
      setTimeout(function() {
        const targetElement = document.querySelector(window.location.hash);
        if (targetElement) {
          lenis.scrollTo(targetElement, {
            offset: NAVBAR_OFFSET,
            duration: 0.75,
            easing: smoothEaseOut,
            immediate: false,
          });
        }
      }, 100);
    }
  });

  // Programmatic helper
  window.learnixSmoothScrollTo = function(target, offset) {
    const off = typeof offset === 'number' ? offset : NAVBAR_OFFSET;
    lenis.scrollTo(target, {
      offset: off,
      duration: 0.75,
      easing: smoothEaseOut,
    });
  };

})();
