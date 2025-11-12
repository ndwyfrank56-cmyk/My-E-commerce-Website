(function(){
  function ensureOverlay(){
    var overlay = document.getElementById('global-loading-overlay');
    if(!overlay){
      overlay = document.createElement('div');
      overlay.id = 'global-loading-overlay';
      var spinner = document.createElement('div');
      spinner.className = 'loading-spinner';
      overlay.appendChild(spinner);
      document.body.appendChild(overlay);
    }
    return overlay;
  }

  function showOverlay(){
    var overlay = ensureOverlay();
    overlay.classList.add('active');
    // Fallback: auto-hide if no navigation occurs within 8s
    clearTimeout(window.__loadingOverlayTimeout);
    window.__loadingOverlayTimeout = setTimeout(function(){
      hideOverlay();
    }, 8000);
  }
  function hideOverlay(){
    var overlay = document.getElementById('global-loading-overlay');
    if(overlay){ overlay.classList.remove('active'); }
    clearTimeout(window.__loadingOverlayTimeout);
  }

  function setButtonLoading(btn){
    if(!btn) return;
    if(btn.classList.contains('is-loading')) return;
    btn.classList.add('is-loading');
    // Add a small spinner next to text
    var dot = document.createElement('span');
    dot.className = 'loading-dot';
    btn.appendChild(dot);
    btn.disabled = true;
  }

  function attachHandlers(){
    // Only show overlay for true navigations and form submits
    document.addEventListener('click', function(e){
      if(e.defaultPrevented) return;
      if(e.button && e.button !== 0) return; // not left click
      if(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

      var el = e.target;
      while(el && !(el.tagName === 'A' || el.type === 'submit' || el.tagName === 'BUTTON')){
        el = el.parentElement;
      }
      if(!el) return;

      // Opt-out
      if(el.dataset && el.dataset.noLoading !== undefined) return;

      // Case 1: Anchor navigation
      if(el.tagName === 'A'){
        var href = el.getAttribute('href') || '';
        var t = el.getAttribute('target');
        if(!href || href.startsWith('#') || href.startsWith('javascript:') || (t && t === '_blank')){
          return; // not a page navigation
        }
        setButtonLoading(el);
        showOverlay();
        return;
      }

      // Case 2: Clicks on regular buttons are ignored here (including type=submit).
      // We only handle form submits in the 'submit' listener below to avoid false positives.

      // Case 3: Explicitly opted-in action button (e.g., buttons that do window.location in onclick)
      if(el.dataset && el.dataset.loading !== undefined){
        setButtonLoading(el);
        showOverlay();
        return;
      }

      // Otherwise, ignore normal buttons (like sidebar toggles) to avoid endless overlay
    }, true);

    // On any form submit, show overlay
    document.addEventListener('submit', function(e){
      var form = e.target;
      if(form && !(form.dataset && form.dataset.noLoading !== undefined)){
        var submitter = (e.submitter) ? e.submitter : form.querySelector('[type="submit"]');
        setButtonLoading(submitter);
        showOverlay();
      }
    }, true);

    // Hide overlay when page fully loaded
    window.addEventListener('pageshow', function(){ hideOverlay(); });
    window.addEventListener('load', function(){ hideOverlay(); });

    // Mobile search overlay functionality
    function initMobileSearch() {
      // Create mobile search overlay if it doesn't exist
      if (!document.querySelector('.mobile-search-overlay')) {
        var overlay = document.createElement('div');
        overlay.className = 'mobile-search-overlay';
        overlay.innerHTML = `
          <div class="mobile-search-container">
            <div class="mobile-search-input-wrapper">
              <i class="fas fa-search mobile-search-icon"></i>
              <input type="text" class="mobile-search-input" placeholder="Search products...">
              <button class="mobile-search-close" type="button">
                <i class="fas fa-times"></i>
              </button>
            </div>
            <div class="mobile-search-results" style="display: none;"></div>
          </div>
        `;
        document.body.appendChild(overlay);
        
        // Handle mobile search input
        var mobileInput = overlay.querySelector('.mobile-search-input');
        var mobileResults = overlay.querySelector('.mobile-search-results');
        var closeBtn = overlay.querySelector('.mobile-search-close');
        
        // Search functionality
        mobileInput.addEventListener('input', function() {
          var query = this.value.trim();
          if (query.length > 0) {
            performMobileSearch(query, mobileResults);
          } else {
            mobileResults.style.display = 'none';
          }
        });
        
        // Close overlay
        closeBtn.addEventListener('click', function() {
          overlay.classList.remove('active');
          mobileInput.value = '';
          mobileResults.style.display = 'none';
        });
        
        // Close on escape key
        document.addEventListener('keydown', function(e) {
          if (e.key === 'Escape' && overlay.classList.contains('active')) {
            overlay.classList.remove('active');
            mobileInput.value = '';
            mobileResults.style.display = 'none';
          }
        });
      }
      
      // Handle search icon click on mobile
      var searchIcons = document.querySelectorAll('.nav-center .search-icon, .search-btn');
      searchIcons.forEach(function(icon) {
        icon.addEventListener('click', function(e) {
          if (window.innerWidth <= 768) {
            e.preventDefault();
            e.stopPropagation();
            var overlay = document.querySelector('.mobile-search-overlay');
            if (overlay) {
              overlay.classList.add('active');
              setTimeout(function() {
                overlay.querySelector('.mobile-search-input').focus();
              }, 300);
            }
          }
        });
      });
    }
    
    // Mobile search function
    function performMobileSearch(query, resultsContainer) {
      // Use existing search functionality if available
      if (typeof searchProducts === 'function') {
        searchProducts(query).then(function(results) {
          displayMobileSearchResults(results, resultsContainer);
        });
      } else {
        // Fallback: redirect to search page
        setTimeout(function() {
          window.location.href = '/search?q=' + encodeURIComponent(query);
        }, 500);
      }
    }
    
    // Display mobile search results
    function displayMobileSearchResults(results, container) {
      if (!results || results.length === 0) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #9aa3b2;">No products found</div>';
        container.style.display = 'block';
        return;
      }
      
      var html = results.slice(0, 8).map(function(product) {
        return `
          <div class="mobile-search-suggestion" onclick="window.location.href='/product/${product.id}'">
            <img src="${product.image || '/static/images/placeholder.jpg'}" alt="${product.name}">
            <div class="mobile-search-suggestion-content">
              <div class="mobile-search-suggestion-name">${product.name}</div>
              <div class="mobile-search-suggestion-price">RWF ${product.price.toLocaleString()}</div>
              <div class="mobile-search-suggestion-category">${product.category || ''}</div>
            </div>
          </div>
        `;
      }).join('');
      
      container.innerHTML = html;
      container.style.display = 'block';
    }
    
    // Initialize mobile search
    initMobileSearch();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', attachHandlers);
  } else {
    attachHandlers();
  }
})();
