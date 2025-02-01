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


$(document).on('click','.schedule__btn',function(e){

  e.preventDefault();
  
  
  let gameId = $(this).attr('data-id')
  


  $('#game-'+gameId).addClass('popup--active');

  
  $('.header').hide();

  $('#id_game_id').val(gameId);

  $('body').addClass('body');

 
})

$(document).on('click','.popup__close, .popup__overflow',function(e){

  e.preventDefault();
  $('.popup').removeClass('popup--active');
  $('body').removeClass('body');
  $('.header').show();

  var urlParams = new URLSearchParams(window.location.search);
  // Проверяем наличие параметра reserve
  if (urlParams.has('reserve')) {
    window.location.href = "/";
  }

  
  
 
})







$(document).ready(function() {
  // Получаем параметры URL
  var urlParams = new URLSearchParams(window.location.search);

  // Проверяем наличие параметра reserve
  if (urlParams.has('reserve')) {
      var reserveValue = urlParams.get('reserve');

      if (reserveValue === 'true') {
          // Показываем попап для reserve=true
          $('.reserve').addClass('popup--active');


      } else if (reserveValue === 'false') {
          // Показываем попап для reserve=false
          $('.thank').addClass('popup--active');
      }
  }

  if (urlParams.has('error')) {
    var errorValue = urlParams.get('error');

    if (errorValue === 'true') {
        // Показываем попап для reserve=true
        $('.error').addClass('popup--active');
    }
}

  
});