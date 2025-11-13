// Loading functionality for specific buttons only (Add to Cart, Buy Now)
(function(){
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

  function removeButtonLoading(btn){
    if(!btn) return;
    btn.classList.remove('is-loading');
    var dot = btn.querySelector('.loading-dot');
    if(dot) dot.remove();
    btn.disabled = false;
  }

  function attachHandlers(){
    // Only handle Add to Cart and Buy Now buttons
    document.addEventListener('click', function(e){
      if(e.defaultPrevented) return;
      if(e.button && e.button !== 0) return; // not left click
      if(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

      var el = e.target;
      while(el && el.tagName !== 'BUTTON'){
        el = el.parentElement;
      }
      if(!el) return;

      // Only apply loading to Add to Cart and Buy Now buttons
      if(el.classList.contains('add-to-cart-btn') || 
         el.classList.contains('buy-now-btn') ||
         el.id === 'addToCartBtn' ||
         el.onclick && el.onclick.toString().includes('addToCart') ||
         el.onclick && el.onclick.toString().includes('buyNow')){
        setButtonLoading(el);
        
        // Auto-remove loading after 3 seconds as fallback
        setTimeout(function(){
          removeButtonLoading(el);
        }, 3000);
      }
    }, true);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', attachHandlers);
  } else {
    attachHandlers();
  }

  // Expose functions globally for manual use
  window.setButtonLoading = setButtonLoading;
  window.removeButtonLoading = removeButtonLoading;
})();
