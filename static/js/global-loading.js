/**
 * Global Loading System - Prevents all interactions during page loads
 * This script manages loading states across the entire application
 */

class GlobalLoadingManager {
  constructor() {
    this.overlay = null;
    this.isLoading = false;
    this.loadingTimeout = null;
    this.init();
  }

  init() {
    // Create loading overlay if it doesn't exist
    this.createOverlay();
    
    // Set up event listeners
    this.setupEventListeners();
    
    // Handle initial page load
    this.handleInitialLoad();
  }

  createOverlay() {
    // Check if overlay already exists
    if (document.getElementById('globalLoadingOverlay')) {
      this.overlay = document.getElementById('globalLoadingOverlay');
      return;
    }

    // Create overlay element
    this.overlay = document.createElement('div');
    this.overlay.id = 'globalLoadingOverlay';
    this.overlay.className = 'global-loading-overlay';
    this.overlay.innerHTML = `
      <div class="global-loading-spinner"></div>
      <div class="global-loading-text">Loading...</div>
      <div class="global-loading-subtext">Please wait while we load the page</div>
    `;
    
    // Add to body
    document.body.appendChild(this.overlay);
  }

  show(message = 'Loading...', subtext = 'Please wait while we load the page') {
    if (this.isLoading) return;
    
    this.isLoading = true;
    
    // Update text if provided
    const textEl = this.overlay.querySelector('.global-loading-text');
    const subtextEl = this.overlay.querySelector('.global-loading-subtext');
    
    if (textEl) textEl.textContent = message;
    if (subtextEl) subtextEl.textContent = subtext;
    
    // Show overlay
    this.overlay.classList.remove('fade-out');
    this.overlay.classList.add('active');
    document.body.classList.add('loading-active');
    
    // Prevent scrolling
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    
    console.log('Global loading started:', message);
  }

  hide() {
    if (!this.isLoading) return;
    
    this.isLoading = false;
    
    // Fade out and hide
    this.overlay.classList.add('fade-out');
    
    setTimeout(() => {
      this.overlay.classList.remove('active', 'fade-out');
      document.body.classList.remove('loading-active');
      
      // Restore scrolling
      document.documentElement.style.overflow = '';
      document.body.style.overflow = '';
    }, 300);
    
    console.log('Global loading ended');
  }

  setupEventListeners() {
    // Handle page navigation
    this.setupNavigationListeners();
    
    // Handle form submissions
    this.setupFormListeners();
    
    // Handle AJAX requests
    this.setupAjaxListeners();
    
    // Handle page visibility changes
    this.setupVisibilityListeners();
  }

  setupNavigationListeners() {
    // Show loading on link clicks (except for specific exclusions)
    document.addEventListener('click', (e) => {
      // If another handler prevented default (e.g., user cancelled a confirm), do nothing
      if (e.defaultPrevented) return;
      const link = e.target.closest('a');
      if (!link) return;
      
      // Skip if it's an excluded link
      if (this.shouldSkipLink(link)) return;
      
      // Skip if it's a same-page anchor
      if (link.getAttribute('href')?.startsWith('#')) return;
      
      // Skip if it opens in new tab
      if (link.target === '_blank') return;
      
      // Skip if it's a download link
      if (link.hasAttribute('download')) return;
      
      // Show loading
      this.show('Navigating...', 'Loading the next page');
      
      // Add loading class to link
      link.classList.add('link-loading');
    });

    // Handle browser back/forward buttons
    window.addEventListener('popstate', () => {
      this.show('Loading...', 'Navigating to previous page');
    });

    // Handle page unload
    window.addEventListener('beforeunload', () => {
      this.show('Leaving page...', 'Please wait');
    });
  }

  setupFormListeners() {
    document.addEventListener('submit', (e) => {
      const form = e.target;
      if (!form || form.tagName !== 'FORM') return;
      
      // Only skip if form has explicit no-loading class
      if (form.classList.contains('no-loading')) return;
      
      // Show loading for ALL forms - no restrictions!
      this.show('Processing...', 'Submitting your request');
      
      // Add loading class to form
      form.classList.add('form-loading');
      
      // Add loading state to submit button
      const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submitBtn) {
        this.addButtonLoading(submitBtn);
      }
    });
  }

  setupAjaxListeners() {
    // Intercept fetch requests
    const originalFetch = window.fetch;
    window.fetch = (...args) => {
      // Check if we should show loading for this request
      const url = args[0];
      const options = args[1] || {};
      
      // Skip loading for certain requests
      if (this.shouldSkipAjaxLoading(url, options)) {
        return originalFetch.apply(this, args);
      }
      
      this.show('Loading...', 'Fetching data');
      
      return originalFetch.apply(this, args)
        .finally(() => {
          // Small delay to prevent flashing
          setTimeout(() => this.hide(), 100);
        });
    };

    // Intercept XMLHttpRequest
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(...args) {
      this.addEventListener('loadstart', () => {
        if (!globalLoading.shouldSkipAjaxLoading(args[1])) {
          globalLoading.show('Loading...', 'Processing request');
        }
      });
      
      this.addEventListener('loadend', () => {
        setTimeout(() => globalLoading.hide(), 100);
      });
      
      return originalXHROpen.apply(this, args);
    };
  }

  setupVisibilityListeners() {
    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        // Page is hidden, might be navigating away
        this.show('Loading...', 'Please wait');
      } else {
        // Page is visible again
        setTimeout(() => this.hide(), 500);
      }
    });
  }

  handleInitialLoad() {
    // Show loading immediately if page is still loading
    if (document.readyState === 'loading') {
      this.show('Loading page...', 'Setting up the interface');
    }
    
    // Hide loading when page is fully loaded
    const hideOnLoad = () => {
      setTimeout(() => this.hide(), 300);
    };
    
    if (document.readyState === 'complete') {
      hideOnLoad();
    } else {
      window.addEventListener('load', hideOnLoad);
    }
  }

  shouldSkipLink(link) {
    // Only skip if link has explicit no-loading class
    if (link.classList.contains('no-loading')) return true;
    
    // Skip if it's a JavaScript void link
    if (link.getAttribute('href') === 'javascript:void(0)' || link.getAttribute('href') === '#') return true;
    
    // Skip if it's an email or tel link
    const href = link.getAttribute('href') || '';
    if (href.startsWith('mailto:') || href.startsWith('tel:')) return true;
    
    // Show loading for everything else - no restrictions!
    return false;
  }

  shouldSkipAjaxLoading(url, options = {}) {
    // Only skip if request has explicit no-loading header
    if (options.headers && options.headers['X-No-Loading']) return true;
    
    // Skip loading for search API requests (they're fast and shouldn't show overlay)
    if (url.includes('/api/search')) return true;
    
    // Show loading for ALL other AJAX requests
    return false;
  }

  addButtonLoading(button) {
    if (button.classList.contains('btn-loading')) return;
    
    button.classList.add('btn-loading');
    button.disabled = true;
    
    // Store original content
    const originalContent = button.innerHTML;
    button.setAttribute('data-original-content', originalContent);
    
    // Add spinner
    const spinner = document.createElement('span');
    spinner.className = 'btn-spinner';
    
    const textSpan = document.createElement('span');
    textSpan.className = 'btn-text';
    textSpan.innerHTML = originalContent;
    
    button.innerHTML = '';
    button.appendChild(textSpan);
    button.appendChild(spinner);
  }

  removeButtonLoading(button) {
    if (!button.classList.contains('btn-loading')) return;
    
    button.classList.remove('btn-loading');
    button.disabled = false;
    
    // Restore original content
    const originalContent = button.getAttribute('data-original-content');
    if (originalContent) {
      button.innerHTML = originalContent;
      button.removeAttribute('data-original-content');
    }
  }

  // Public methods for manual control
  showManual(message, subtext) {
    this.show(message, subtext);
  }

  hideManual() {
    this.hide();
  }

  isCurrentlyLoading() {
    return this.isLoading;
  }
}

// Initialize global loading manager
let globalLoading;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    globalLoading = new GlobalLoadingManager();
  });
} else {
  globalLoading = new GlobalLoadingManager();
}

// Export for global access
window.GlobalLoading = globalLoading;
