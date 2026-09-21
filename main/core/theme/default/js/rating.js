(function () {
  'use strict';

  var filterForm = document.querySelector('.rating-filters');
  if (filterForm) {
    var submits = filterForm.querySelectorAll('button[type="submit"]');
    filterForm.addEventListener('submit', function () {
      submits.forEach(function (button) {
        button.disabled = true;
        button.setAttribute('aria-disabled', 'true');
        button.textContent = 'Загрузка…';
      });
    });
  }

  var giftLinks = document.querySelectorAll('[data-gift-format]');
  var giftPanels = document.querySelectorAll('[data-gift-panel]');
  if (!giftLinks.length || !giftPanels.length) return;

  giftLinks.forEach(function (link) {
    link.addEventListener('click', function (event) {
      var selectedFormat = link.getAttribute('data-gift-format');
      var selectedPanel = document.getElementById(link.getAttribute('aria-controls'));
      if (!selectedFormat || !selectedPanel) return;

      event.preventDefault();
      giftLinks.forEach(function (item) {
        var isSelected = item === link;
        item.classList.toggle('is-active', isSelected);
        if (isSelected) {
          item.setAttribute('aria-current', 'true');
        } else {
          item.removeAttribute('aria-current');
        }
      });
      giftPanels.forEach(function (panel) {
        panel.hidden = panel.getAttribute('data-gift-panel') !== selectedFormat;
      });
    });
  });
})();
