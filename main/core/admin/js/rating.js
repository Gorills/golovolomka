(function () {
  'use strict';

  var body = document.body;
  var menuButton = document.querySelector('.ra-menu-button');
  var backdrop = document.querySelector('.ra-drawer-backdrop');
  var sidebar = document.getElementById('ra-sidebar-drawer');

  function setMenu(open, restoreFocus) {
    body.classList.toggle('ra-menu-open', open);
    if (menuButton) menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (backdrop) backdrop.hidden = !open;
    if (open && sidebar) {
      var firstLink = sidebar.querySelector('a');
      if (firstLink) firstLink.focus();
    } else if (restoreFocus && menuButton) {
      menuButton.focus();
    }
  }

  if (menuButton) menuButton.addEventListener('click', function () { setMenu(!body.classList.contains('ra-menu-open')); });
  if (backdrop) backdrop.addEventListener('click', function () { setMenu(false, true); });
  document.addEventListener('keydown', function (event) { if (event.key === 'Escape') setMenu(false, true); });

  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!window.confirm(form.getAttribute('data-confirm'))) event.preventDefault();
    });
  });

  document.querySelectorAll('form[data-prevent-double-submit]').forEach(function (form) {
    form.addEventListener('submit', function () {
      form.querySelectorAll('button[type="submit"]').forEach(function (button) {
        button.disabled = true;
        button.setAttribute('aria-disabled', 'true');
      });
    });
  });

  document.querySelectorAll('[data-stepper]').forEach(function (stepper) {
    var input = stepper.querySelector('input[type="number"]');
    if (!input) return;
    stepper.querySelectorAll('[data-step]').forEach(function (button) {
      button.addEventListener('click', function () {
        var current = Number(input.value || 0);
        var next = current + Number(button.getAttribute('data-step'));
        var min = input.min === '' ? -Infinity : Number(input.min);
        input.value = String(Math.max(min, next));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
    });
  });
})();
