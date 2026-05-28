$(document).ready(function () {
  $('.slider__inner').owlCarousel({
    items: 1, // Показывает только один слайд
    loop: true, // Бесконечная прокрутка
    autoplay: true, // Включает автолистание
    autoplayTimeout: 6000, // Задержка между автолистанием (в миллисекундах)
    autoplayHoverPause: false, // Пауза при наведении мыши на слайдер
    nav: false, // Отключение кнопок навигации
    dots: false, // Включает точки под слайдером
  });
});


// При loop:true Owl Carousel клонирует слайды. Клоны получают те же id внутри SVG
// (градиенты, маски и т.д.) — Safari/iOS тогда «мигают» стили и ломают заливки.
// Важно: не вызывать это на каждом translated/changed — массовая правка DOM при свайпе
// перегружает WebKit и на iPhone даёт падение вкладки («повторно возникла проблема»).
function uniquifyScheduleSvgIds() {
  var counter = 0;
  $('.schedule__slider .schedule__item svg').each(function () {
    var svg = this;
    var $svg = $(svg);
    var pairs = [];
    $svg.find('[id]').each(function () {
      var el = this;
      var oldId = el.id;
      if (!oldId) return;
      var newId = 'sd_' + (++counter) + '_' + Math.random().toString(36).slice(2, 8);
      pairs.push({ el: el, oldId: oldId, newId: newId });
    });
    var map = {};
    pairs.forEach(function (p) {
      map[p.oldId] = p.newId;
      p.el.id = p.newId;
    });
    var urlAttrs = ['fill', 'stroke', 'mask', 'clip-path', 'filter'];
    $svg.find('*').each(function () {
      var el = this;
      var a;
      for (a = 0; a < urlAttrs.length; a++) {
        var attr = urlAttrs[a];
        var val = el.getAttribute(attr);
        if (!val || val.indexOf('url(#') === -1) continue;
        var replaced = val.replace(/url\(#([^)]+)\)/g, function (_, id) {
          return map[id] ? 'url(#' + map[id] + ')' : 'url(#' + id + ')';
        });
        if (replaced !== val) el.setAttribute(attr, replaced);
      }
      var href = el.getAttribute('href');
      if (href && href.charAt(0) === '#' && map[href.slice(1)]) {
        el.setAttribute('href', '#' + map[href.slice(1)]);
      }
      var xlink = el.getAttribute('xlink:href');
      if (xlink && xlink.charAt(0) === '#' && map[xlink.slice(1)]) {
        el.setAttribute('xlink:href', '#' + map[xlink.slice(1)]);
      }
    });
  });
}

$('.schedule__slider').on('initialized.owl.carousel refreshed.owl.carousel', function () {
  window.requestAnimationFrame(function () {
    uniquifyScheduleSvgIds();
  });
});

$('.schedule__slider').owlCarousel({
  items: 1,
  loop: true,
  margin: 20,
  autoplay: false,
  autoplayTimeout: 5000,
  autoplayHoverPause: true,
  nav: true,
  navText: [
    `<div class="custom-prev">

        <svg width="9" height="15" viewBox="0 0 9 15" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="0.646447" y1="7.64645" x2="7.64645" y2="0.646447" stroke="#202020"/>
        <line x1="1.35355" y1="7.64645" x2="8.35355" y2="14.6464" stroke="#202020"/>
        </svg>

    </div>`, // Левая кнопка
    `<div class="custom-next">

      <svg width="9" height="15" viewBox="0 0 9 15" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="8.35355" y1="7.35355" x2="1.35355" y2="14.3536" stroke="#202020"/>
      <line x1="7.64645" y1="7.35355" x2="0.646447" y2="0.353553" stroke="#202020"/>
      </svg>

    </div>` // Правая кнопка
  ],
  dots: false,
  responsiveClass: true,
  responsive: {
      0: {
          items: 1,
          stagePadding: 40 // Добавляет отступы для видимости
      },
      420: {
          items: 1,
          stagePadding: 50 // Добавляет отступы для видимости
      },
      768: {
          items: 2,
          stagePadding: 100
      },
      1024: {
          items: 3,
          stagePadding: 150,
          margin: 80,
      }
  }
});

window.requestAnimationFrame(function () {
  uniquifyScheduleSvgIds();
});



$('.format__slider').owlCarousel({
  items: 1,
  loop: true,
  margin: 20,
  autoplay: false,
  autoplayTimeout: 5000,
  autoplayHoverPause: true,
  nav: true,
  navText: [
    `<div class="custom-prev">
    
        <svg width="9" height="15" viewBox="0 0 9 15" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="0.646447" y1="7.64645" x2="7.64645" y2="0.646447" stroke="#202020"/>
        <line x1="1.35355" y1="7.64645" x2="8.35355" y2="14.6464" stroke="#202020"/>
        </svg>

    </div>`, // Левая кнопка
    `<div class="custom-next">
    
      <svg width="9" height="15" viewBox="0 0 9 15" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="8.35355" y1="7.35355" x2="1.35355" y2="14.3536" stroke="#202020"/>
      <line x1="7.64645" y1="7.35355" x2="0.646447" y2="0.353553" stroke="#202020"/>
      </svg>

    </div>` // Правая кнопка
  ],
  dots: true,
  responsiveClass: true,
  responsive: {
      0: {
          items: 1,
          stagePadding: 50 // Добавляет отступы для видимости
      },
      768: {
          items: 2,
          stagePadding: 100
      },
      1024: {
          items: 3,
          stagePadding: 0,
          margin: 80,
      }
  }
});


$('.corp-about__slider').owlCarousel({
  items: 3,
  loop: true,
  margin: 20,
  autoplay: true,
  autoplayTimeout: 5000,
  autoplayHoverPause: true,
  nav: false,
  
  dots: false,
  responsiveClass: true,
  
});

new VenoBox({
  selector: '.format__slider-item',
  numeration: true,
  infinigall: true,
  share: true,
  spinner: 'rotating-plane'
});

$(document).on('click','.about__rules-top',function(){

  $(".about__rules-body").toggleClass('about__rules-body--active');

  
})


$(document).on('click','.format__nav-item',function(){

  let dataId = $(this).attr('data-id')
  console.log(dataId)
  $('.format__body-item').removeClass('format__body-item--active')
  $('.format__body-item[data-id="'+dataId+'"]').addClass('format__body-item--active')

  
})


$(document).on('click','.faq__item',function(){

  // $('.faq__item').removeClass('faq__item--active')
  $(this).toggleClass('faq__item--active')

  
})  


$(document).on('click','.toggle-menu',function(e){
  e.preventDefault();
  $(".menu-btn").toggleClass('menu-btn_active');
  $(".nav").toggleClass('nav--active');
  
 
 
})


$(document).on('click','.nav__link',function(e){

  $(".menu-btn").removeClass('menu-btn_active');
  $(".nav").removeClass('nav--active');
  
 
})


// Скрол хедера
$(window).scroll(function() {
  var height = $(window).scrollTop();
  /*Если сделали скролл на 100px задаём новый класс для header*/
  if(height > 200){
      $('.header').addClass('header--hide');
      
      
  } else{
      /*Если меньше 100px удаляем класс для header*/
      $('.header').removeClass('header--hide');
      
  }
  if(height > 200){
      $('.header').addClass('header--fixed');
      
      
  } else{
      /*Если меньше 100px удаляем класс для header*/
      $('.header').removeClass('header--fixed');
     

     
  }
});


$(document).on('click','#messenger-btn',function(e){

  e.preventDefault();
  $(".messenger-links").toggleClass('messenger-links--active');
  
 
})


/**
 * Сетка кнопок 1–12 для поля command_number (скрытый input).
 */
function initCommandNumberPicker() {
  $('[data-command-picker]').each(function () {
    var $root = $(this);
    if ($root.data('commandPickerInit')) {
      return;
    }
    $root.data('commandPickerInit', true);

    var $input = $root.find('input[name="command_number"]');
    var $grid = $root.find('.command-number-picker__grid');
    if (!$input.length || !$grid.length) {
      return;
    }

    function clamp(n) {
      var v = parseInt(n, 10);
      if (isNaN(v)) {
        v = 2;
      }
      return Math.min(12, Math.max(1, v));
    }

    function setValue(n, focusBtn) {
      var v = clamp(n);
      $input.val(String(v));
      var $btns = $grid.find('.command-number-picker__btn');
      $btns.removeClass('command-number-picker__btn--selected').attr({ 'aria-checked': 'false', tabindex: -1 });
      var $cur = $btns.filter('[data-value="' + v + '"]');
      $cur.addClass('command-number-picker__btn--selected').attr({ 'aria-checked': 'true', tabindex: 0 });
      if (focusBtn && $cur.length) {
        $cur.trigger('focus');
      }
    }

    var n;
    for (n = 1; n <= 12; n += 1) {
      $('<button>', {
        type: 'button',
        class: 'command-number-picker__btn',
        text: String(n),
        'data-value': n,
        role: 'radio',
        'aria-checked': 'false',
        tabindex: -1,
      }).appendTo($grid);
    }

    $grid.on('click', '.command-number-picker__btn', function () {
      var val = $(this).data('value');
      setValue(val, false);
    });

    $grid.on('keydown', '.command-number-picker__btn', function (e) {
      var cur = clamp($(this).data('value'));
      var next = cur;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        next = cur < 12 ? cur + 1 : 1;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        next = cur > 1 ? cur - 1 : 12;
      } else if (e.key === 'Home') {
        next = 1;
      } else if (e.key === 'End') {
        next = 12;
      } else {
        return;
      }
      e.preventDefault();
      setValue(next, true);
    });

    setValue($input.val(), false);
  });
}


var _gameFormSubmitFallbackTimer = null;

function resetGameOrderFormSubmitLock($f) {
  if (_gameFormSubmitFallbackTimer) {
    clearTimeout(_gameFormSubmitFallbackTimer);
    _gameFormSubmitFallbackTimer = null;
  }
  if ($f && $f.length) {
    $f.data('submitting', false);
    $f.find('button[type="submit"]').prop('disabled', false);
  }
}

function lockBodyScrollForPopup() {
  if ($('html').hasClass('body-scroll-lock')) {
    return;
  }
  var scrollY = window.scrollY || window.pageYOffset || 0;
  $('html').addClass('body-scroll-lock');
  $('body').addClass('body').data('popup-scroll-y', scrollY);
  document.body.style.top = '-' + scrollY + 'px';
}

function unlockBodyScrollForPopup() {
  var scrollY = $('body').data('popup-scroll-y');
  if (scrollY === undefined) {
    scrollY = 0;
  }
  $('html').removeClass('body-scroll-lock');
  $('body').removeClass('body').removeData('popup-scroll-y');
  document.body.style.top = '';
  window.scrollTo(0, scrollY);
}

function hideHeaderForPopup() {
  $('.header').addClass('header--popup-hidden');
}

function showHeaderAfterPopup() {
  $('.header').removeClass('header--popup-hidden');
}

function closeAllPopups() {
  $('.popup').removeClass('popup--active');
  unlockBodyScrollForPopup();
  showHeaderAfterPopup();
  resetGameOrderFormSubmitLock($('form.game-form'));
}

function openGameRegisterPopup(gameId) {
  var $popup = $('#game-register');
  if (!$popup.length) {
    return;
  }
  $popup.find('input[name="game_id"]').val(gameId);
  $('.popup').removeClass('popup--active');
  $popup.addClass('popup--active');
  lockBodyScrollForPopup();
  hideHeaderForPopup();
}

function showGameOrderResultPopup(reserve) {
  closeAllPopups();
  if (reserve) {
    $('.popup.reserve').addClass('popup--active');
  } else {
    $('.popup.thank').addClass('popup--active');
  }
  lockBodyScrollForPopup();
  hideHeaderForPopup();
}

function showGameOrderErrorPopup(message) {
  closeAllPopups();
  if (message) {
    $('.js-popup-game-error-text').text(message);
  }
  $('.popup-game-error').addClass('popup--active');
  lockBodyScrollForPopup();
  hideHeaderForPopup();
}

function gameOrderFormErrorsToText(errors) {
  if (!errors || typeof errors !== 'object') {
    return '';
  }
  var parts = [];
  Object.keys(errors).forEach(function (field) {
    var msgs = errors[field];
    if (!msgs || !msgs.length) {
      return;
    }
    parts.push(msgs[0]);
  });
  return parts.join(' ');
}

function canSubmitGameFormViaFetch() {
  return typeof window.fetch === 'function' && typeof window.FormData === 'function';
}

function armGameOrderSubmitLock($f) {
  $f.data('submitting', true);
  $f.find('button[type="submit"]').prop('disabled', true);
  if (_gameFormSubmitFallbackTimer) {
    clearTimeout(_gameFormSubmitFallbackTimer);
  }
  _gameFormSubmitFallbackTimer = setTimeout(function () {
    _gameFormSubmitFallbackTimer = null;
    resetGameOrderFormSubmitLock($f);
  }, 25000);
}

function resetCommandNumberPickerToDefault($form) {
  var $picker = $form.find('[data-command-picker]');
  if (!$picker.length) {
    return;
  }
  var $input = $picker.find('input[name="command_number"]');
  if ($input.length) {
    $input.val('2');
  }
  $picker.find('.command-number-picker__btn').removeClass('command-number-picker__btn--selected').attr({ 'aria-checked': 'false', tabindex: -1 });
  var $btn = $picker.find('.command-number-picker__btn[data-value="2"]');
  $btn.addClass('command-number-picker__btn--selected').attr({ 'aria-checked': 'true', tabindex: 0 });
}

$(document).on('click', '.schedule__btn', function (e) {
  e.preventDefault();
  var gameId = $(this).attr('data-id');
  if (!gameId) {
    return;
  }
  openGameRegisterPopup(gameId);
});

// Восстановление после bfcache в Safari (назад к странице с формой — иначе кнопка «мертвая»).
$(window).on('pageshow', function (ev) {
  var oe = ev.originalEvent;
  if (oe && oe.persisted) {
    resetGameOrderFormSubmitLock($('form.game-form'));
    closeAllPopups();
  }
});

$(document).on('visibilitychange', function () {
  if (document.visibilityState === 'visible') {
    resetGameOrderFormSubmitLock($('form.game-form'));
  }
});

// AJAX-отправка: без полной перезагрузки страницы (стабильнее на iPhone Safari).
$(document).on('submit', 'form.game-form', function (e) {
  var $f = $(this);
  if ($f.data('submitting')) {
    e.preventDefault();
    return false;
  }

  var gameId = ($f.find('input[name="game_id"]').val() || '').trim();
  if (!gameId) {
    e.preventDefault();
    showGameOrderErrorPopup(
      'Не выбрана игра. Закройте окно и нажмите «Записаться» у нужной игры снова.'
    );
    return false;
  }

  if (!canSubmitGameFormViaFetch()) {
    armGameOrderSubmitLock($f);
    return true;
  }

  e.preventDefault();
  armGameOrderSubmitLock($f);

  var action = $f.attr('action') || window.location.pathname;
  var formEl = this;

  fetch(action, {
    method: 'POST',
    body: new FormData(formEl),
    credentials: 'same-origin',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      Accept: 'application/json',
    },
  })
    .then(function (res) {
      return res
        .json()
        .then(function (data) {
          return { ok: res.ok, data: data };
        })
        .catch(function () {
          return { ok: false, data: {} };
        });
    })
    .then(function (result) {
      resetGameOrderFormSubmitLock($f);
      if (result.ok && result.data && result.data.ok) {
        formEl.reset();
        resetCommandNumberPickerToDefault($f);
        showGameOrderResultPopup(!!result.data.reserve);
        return;
      }
      var errText = gameOrderFormErrorsToText(result.data && result.data.errors);
      showGameOrderErrorPopup(
        errText ||
          'Не удалось отправить заявку. Проверьте поля и попробуйте ещё раз.'
      );
    })
    .catch(function () {
      resetGameOrderFormSubmitLock($f);
      showGameOrderErrorPopup(
        'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.'
      );
    });

  return false;
});

$(document).on('click', '.popup__close, .popup__overflow', function (e) {
  e.preventDefault();
  closeAllPopups();

  var urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('reserve') || urlParams.has('error')) {
    window.location.replace('/');
  }
});







$(document).ready(function() {
  initCommandNumberPicker();

  // Получаем параметры URL
  var urlParams = new URLSearchParams(window.location.search);

  // Проверяем наличие параметра reserve
  if (urlParams.has('reserve')) {
      var reserveValue = urlParams.get('reserve');

      if (reserveValue === 'true') {
          showGameOrderResultPopup(true);
      } else if (reserveValue === 'false') {
          showGameOrderResultPopup(false);
      }
  }

  if (urlParams.has('error')) {
    var errorValue = urlParams.get('error');

    if (errorValue === 'true') {
        showGameOrderErrorPopup();
    }
}

  
});



$(document).on('click','.header__city',function(e){
  e.preventDefault()
 
  $('.city-popup').toggleClass('city-popup--active');


})



$(document).on('click','.city-popup__owerlay--close',function(e){
  e.preventDefault()
 
  $('.city-popup').removeClass('city-popup--active');


})