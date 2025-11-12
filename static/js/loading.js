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

    var containers = document.querySelectorAll('.search-container');
    containers.forEach(function(c){
      c.addEventListener('click', function(){
        var input = c.querySelector('input, .search-input');
        if(input){ input.focus(); }
      }, true);
    });
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', attachHandlers);
  } else {
    attachHandlers();
  }
})();
