// Установка сессии на показ и скрытие сайдбара
$(document).on('click','.tabs',function(e){

  if ($(this).children('.tabs__glider').hasClass('tabs__glider--active')) {
    $.get( "/admin/sidebar_show/", function() {
        // console.log('!!!')
    });
  } else {
    $.get( "/admin/sidebar_hide/", function() {
      // console.log('!!!')
    });
  }


})

// slugify

function makeSlug(str)
{
  var from="а б в г д е ё ж з и й к л м н о п р с т у ф х ц ч ш щ ъ ы ь э ю я ā ą ä á à â å č ć ē ę ě é è ê æ ģ ğ ö ó ø ǿ ô ő ḿ ŉ ń ṕ ŕ ş ü ß ř ł đ þ ĥ ḧ ī ï í î ĵ ķ ł ņ ń ň ř š ś ť ů ú û ứ ù ü ű ū ý ÿ ž ź ż ç є ґ".split(' ');
  var to=  "a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh shch # y # e yu ya a a ae a a a a c c e e e e e e e g g oe o o o o o m n n p r s ue ss r l d th h h i i i i j k l n n n r s s t u u u u u u u u y y z z z c ye g".split(' ');
	
  str = str.toLowerCase();
  
  // remove simple HTML tags
  str = str.replace(/(<[a-z0-9\-]{1,15}[\s]*>)/gi, '');
  str = str.replace(/(<\/[a-z0-9\-]{1,15}[\s]*>)/gi, '');
  str = str.replace(/(<[a-z0-9\-]{1,15}[\s]*\/>)/gi, '');
  
  str = str.replace(/^\s+|\s+$/gm,''); // trim spaces
  
  for(i=0; i<from.length; ++i)
    str = str.split(from[i]).join(to[i]);
  
  // Replace different kind of spaces with dashes
  var spaces = [/(&nbsp;|&#160;|&#32;)/gi, /(&mdash;|&ndash;|&#8209;)/gi,
     /[(_|=|\\|\,|\.|!)]+/gi, /\s/gi];

  for(i=0; i<from.length; ++i)
  	str = str.replace(spaces[i], '-');
  str = str.replace(/-{2,}/g, "-");

  // remove special chars like &amp;
  str = str.replace(/&[a-z]{2,7};/gi, '');
  str = str.replace(/&#[0-9]{1,6};/gi, '');
  str = str.replace(/&#x[0-9a-f]{1,6};/gi, '');
  
  str = str.replace(/[^a-z0-9\-]+/gmi, ""); // remove all other stuff
  str = str.replace(/^\-+|\-+$/gm,''); // trim edges
  
  return str;
};

$(document).on('keyup','#id_name',function(){
    var url = document.location.href;

    if(url.includes('edit')) {

    } else {
      var getVal = $(this).val()

      var res = makeSlug(getVal)

      
      
      $('#id_slug').val(res)
     
    }
    

})




// end slugify

// Одиночные вставки кода

// Удаление изображения опции option__images-remove
$(document).on('click','.option__images-remove',function(e){
  e.preventDefault();

  if (confirm('Удалить изображение?')) { 
    var href = $(this).attr('href');
  
    $.get(href);
    $("#product-content-4").load(location.href + " .product-content__inner-4");
  }
})
// end Удаление изображения опции

// Удаление опции
$(document).on('click','.option__remove',function(e){
  e.preventDefault();
  if (confirm('Удалить опцию?')) { 
    var href = $(this).attr('href');
  
    $.get(href);
    $("#product-content-4").load(location.href + " .product-content__inner-4");
  }
  
})
// end Удаление опции

// Удаление характеристики
$(document).on('click','.char__remove',function(e){
  e.preventDefault();
  if (confirm('Удалить характеристику?')) { 
    var href = $(this).attr('href');
  
    $.get(href);
    $("#product-content-5").load(location.href + " .product-content__inner-5");
  }
  
})
// end Удаление характеристики

// Удаление дополнительного изображения
$(document).on('click','.product-block__old-remove',function(e){
  e.preventDefault();
  if (confirm('Удалить характеристику?')) { 
    var href = $(this).attr('href');
  
    $.get(href);
    $("#product-content-7").load(location.href + " .product-content__inner-7");
  }
  
})
// end Удаление дополнительного изображения

// Замена запятой в поле для прайса
jQuery(document).ready(function () {

  var oldItem = $('.input-price')
  $(oldItem).each(function(){
    var getVal = $(this).val()
    var newItem = getVal.replace(",", ".")
    $(this).val(newItem)
  })

});
// end Замена запятой в поле для прайса

// Если у категории есть родитель то скрываем возможность поставить галку на главное меню и колонки
$(document).on('change','#id_parent',function(){
  var selVal = $(this).val()
  if (selVal != '') {
    $('#id_column').parent('p').hide()
    $('#id_top').parent('p').hide()
  } else {
    $('#id_column').parent('p').show()
    $('#id_top').parent('p').show()
  }
})
jQuery(document).ready(function () {
  var selVal = $('#id_parent').val()
  // console.log(selVal)
  if (selVal != '') {
    $('#id_column').parent('p').hide()
    $('#id_top').parent('p').hide()
  } else {
    $('#id_column').parent('p').show()
    $('#id_top').parent('p').show()
  }
});
// end

// save form
$(document).on('click','#save',function(e){
  e.preventDefault();

  // Очистка пустых полей перед сохранением
  var option_val = $('.option__paste #id_value')
  var id_type = $('.option__paste #id_type')
  $(option_val).each(function( index ) {
      if ($(this).val() == '') {
        $(this).parent().parent('.option__row').next('.option__images').remove()
        $(this).parent().parent('.option__row').remove()
      }
  });
  $(id_type).each(function( index ) {
    if ($(this).val() == '') {
      $(this).parent().parent('.option__row').next('.option__images').remove()
      $(this).parent().parent('.option__row').remove()
    }
  });

  var option_val = $('.char__paste #id_char_value')
  var id_name = $('.char__paste #id_name')
  $(option_val).each(function( index ) {
      if ($(this).val() == '') {
        $(this).parent().parent('.char__row').remove()
      }
  });
  $(id_name).each(function( index ) {
    if ($(this).val() == '') {
      $(this).parent().parent('.char__row').remove()
    }
  });
  $('.form').submit();
})
// end save form


// Удаление модели
$(document).on('click','.remove',function(e){
  var href = $(this).attr('href')
  return confirm("Данное действие необратимо. Вы уверены?");
})
// end Удаление модели


// Отправка формы при смене статуса заказа order
$(document).on('change','#id_status',function(){


    $(this).parent('form').submit()
  
  
})

// end Отправка формы при смене статуса заказа order




// end Одиночные вставки кода




// Активные ссылки
jQuery(document).ready(function ($) {
  var url = document.location.href;
  $.each($(".sidebar__link"), function () {

    var has_active = $(this).parent().parent().hasClass('sidebar__drop--max')

    if (has_active==false) {
      // console.log(has_active)
      if (this.href == url) {
        $(this).addClass('sidebar__link--active');
        $(this).parent().parent('.sidebar__drop').addClass('sidebar__drop--active');
        
      } else if(url.includes(this.href)) {
        $(this).addClass('sidebar__link--active');
        $(this).parent().parent('.sidebar__drop').addClass('sidebar__drop--active');
      }
    }
  });
});

jQuery(document).ready(function ($) {
  var url = document.location.href;
  $.each($(".sidebar__title"), function () {
    if (this.href == url) {
      $(this).addClass('sidebar__title--active');
    }
  });
});
// end Активные ссылки


// Поиск
$(document).on('click','.header__search',function(){
  $('.header__search-inner').show()
  $('.header__search-input').focus()
})
$(document).on('blur','.header__search-input',function(){

    $('.header__search-inner').hide()
})

// обновление url при поиске
$(document).on('keyup','.header__search-input',function(){
  var href = '?q='+$(this).val()

  function setLocation(curLoc){
    try {
      history.pushState(null, null, curLoc);
      return;
    } catch(e) {}
    location.hash = '#' + curLoc;
  }

  setLocation(href)
  $(".search").load(location.href + " .search__inner");
  $(".breadcrumb").load(location.href + " .breadcrumb__inner");

  if ($(this).val() == '') {
    var path = window.location.pathname
    setLocation(path)
    $(".search").load(location.href + " .search__inner");
    $(".breadcrumb").load(location.href + " .breadcrumb__inner");

  }
})

// Сброс поиска
$(document).on('click','#refresh',function(e){
  e.preventDefault();
  function setLocation(curLoc){
    try {
      history.pushState(null, null, curLoc);
      return;
    } catch(e) {}
    location.hash = '#' + curLoc;
  }
  var path = window.location.pathname
  setLocation(path)
  $(".search").load(location.href + " .search__inner");
  $(".breadcrumb").load(location.href + " .breadcrumb__inner");
})

// end Поиск


// Сортировка на страницах
$(document).on('click','.sort',function(e){
  e.preventDefault();
  var sort = $(this).attr('data-sort')
  
  url = '?sort='+sort

  function setLocation(curLoc){
    try {
      history.pushState(null, null, curLoc);
      return;
    } catch(e) {}
    location.hash = '#' + curLoc;
  }
  setLocation(url)
  $(".search").load(location.href + " .search__inner");
})

// end Сортировка на страницах



// Выпадающее меню в sidebar
$(document).on('click','.sidebar__title--max',function(){
  $('.sidebar__drop').removeClass('sidebar__drop--active')
  $(this).next('.sidebar__drop').toggleClass('sidebar__drop--active')
})
$(document).on('click','.content__inner--max',function(){
  $('.sidebar__drop').removeClass('sidebar__drop--active')
})
$(document).on('click','.sidebar__title--min',function(){
  // $('.sidebar__drop').removeClass('sidebar__drop--active')
  $(this).next('.sidebar__drop').toggleClass('sidebar__drop--active')
})
// end Выпадающее меню в sidebar


// Размер sidebar и content
$(document).on('click','.tabs',function(){
  $('.tabs__glider').toggleClass('tabs__glider--active')
  $('.content__inner').toggleClass('content__inner--max')
  $('.sidebar').toggleClass('sidebar--min')
  $('.sidebar__drop').removeClass('sidebar__drop--active')
  $('.sidebar__title').toggleClass('sidebar__title--max')
  $('.sidebar__title').toggleClass('sidebar__title--min')
}) 
// end Размер sidebar и content


// Попапы



// end Попапы




// Добавление товара
// Добавление дополнительных изображений товара
$(document).on('click','.product-block__plus',function(){
  var image = '<div class="product-block__inner"><p><label for="id_src">Выбрать изображение:</label><input type="file" multiple="multiple" name="src" accept="image/*" required="" id="id_src"></p><div class="product-block__minus"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path d="M416 208H32c-17.67 0-32 14.33-32 32v32c0 17.67 14.33 32 32 32h384c17.67 0 32-14.33 32-32v-32c0-17.67-14.33-32-32-32z"></path></svg></div></div>'
  $('.product-block__paste').append(image)
}) 
$(document).on('click','.product-block__minus',function(){
  $(this).parent('.product-block__inner').remove()
}) 
// end Добавление дополнительных изображений товара


// Добавление дополнительных Опций товара
$(document).on('click','.option__add',function(){
  var typesdss = $('#id_type').html()
  var count = 0
  $('.option__row').each(function( ) {
      count +=1
  });
  var form_html = '<div class="option__row"><input type="text" value="' +count+ '" hidden class="optionCount"><p><label for="id_type">Тип опции:</label><select name="type" class="input" placeholder="Тип опции" id="id_type">'+ typesdss +'</select></p><p><label for="id_value">Артикул:</label><input type="text" name="option_sku" class="input" placeholder="Артикул" maxlength="250" required="required" id="id_option_sku"></p><p><label for="id_value">Значение:</label><input type="text" name="option_value" class="input" placeholder="Значение" maxlength="250" required="required" id="id_value"></p><p><label for="id_stock">Количество:</label><input type="number" name="option_stock" class="input" placeholder="Количество" min="0" required="required" id="id_stock" value="1"></p><p><label for="id_price">Добавить стоимость:</label><input type="number" name="option_price" class="input" placeholder="Добавить стоимость" required="required" step="0.10" id="id_price" value="0"> </p><p><label for="id_subtract">Вычитать со склада:</label><input type="checkbox" class="id_subtract_get"><input type="text" name="option_subtract" class="id_subtract_paste" value="False"></p><p><label for="id_image_status">Включить изображения:</label><input type="checkbox" class="id_image_get"><input type="text" name="image_status" class="id_image_paste" value="False"></p><div class="option__minus"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path d="M416 208H32c-17.67 0-32 14.33-32 32v32c0 17.67 14.33 32 32 32h384c17.67 0 32-14.33 32-32v-32c0-17.67-14.33-32-32-32z"/></svg></div></div><div class="option__images"></div>'
  $('.option__paste').append(form_html)
});
$(document).on('click','.option__minus',function(){
  $(this).parent('.option__row').next('.option__images').remove()
  $(this).parent('.option__row').remove()
});
// end Добавление дополнительных Опций товара


// Заполнение скрытых полей при добавлении опций

$(document).on('change','.id_subtract_get',function(){

  var paste = $(this).next('.id_subtract_paste')
  if (paste.val() == 'False') {
    paste.val('True')
  } else {
    paste.val('False')
  }
});


// Добавление изображений к опциям
$(document).on('change','.id_image_get',function(){
  var paste = $(this).next('.id_image_paste')
  if (paste.val() == 'False') {
    paste.val('True')

    var count = $(this).parent().parent().children('.optionCount').val()
    $(this).parent().parent().next('.option__images').append('<input type="file" multiple="multiple" name="option_images-' + count + '">')

  } else {
    $(this).parent().parent().next('.option__images').html('')
    paste.val('False')
  }
});
// end Заполнение скрытых полей при добавлении опций


$(document).on('change','.id_image_old',function(){
  var paste = $(this).next('.id_image_paste')
  if (paste.val() == 'False') {
    paste.val('True')
    var count = $(this).parent().parent().children('.old_count').val()
    var res = count - 1
    $(this).parent().parent().next('.option__images').append('<input type="file" multiple="multiple" name="option_images_old-' + res + '">')

  } else {
    $(this).parent().parent().next('.option__images').html('')
    paste.val('False')
  }
});

// image_add
// image_add
$(document).on('click','.image_add',function(){
  var count = $(this).parent().prev('.option__old-row').children('.old_count').val()
  var res = count - 1
  $(this).prev('.image_paste-'+count).append('<input type="file" multiple="multiple" name="option_images_old-' + res + '">')
  $(this).remove()
});



// Добавление характеристик товара
$(document).on('click','.char__plus',function(){
  var get_html = $('#id_char_name').html()
  var form_html = '<div class="char__row"><p><label for="id_name">Название характеристики:</label><select name="text_name" class="input" placeholder="Название характеристики" id="id_name">' + get_html + '</select></p><p><label for="id_char_value">Значение:</label><input type="text" name="char_value" class="input" placeholder="Значение" required="" id="id_char_value"></p><div class="char__minus"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path d="M416 208H32c-17.67 0-32 14.33-32 32v32c0 17.67 14.33 32 32 32h384c17.67 0 32-14.33 32-32v-32c0-17.67-14.33-32-32-32z"></path></svg></div></div>'
  $('.char__paste').append(form_html)
  
});
$(document).on('click','.char__minus',function(){
  $(this).parent('.char__row').remove()
});
// end Добавление характеристик товара


// Очистка пустых полей при заполнении товара
$(document).on('click','.product-tabs label',function(){
  var option_val = $('.option__paste #id_value')
  var id_type = $('.option__paste #id_type')

  $(option_val).each(function( index ) {
      if ($(this).val() == '') {
        $(this).parent().parent('.option__row').next('.option__images').remove()
        $(this).parent().parent('.option__row').remove()
      }
  });
  $(id_type).each(function( index ) {
    if ($(this).val() == '') {
      $(this).parent().parent('.option__row').next('.option__images').remove()
      $(this).parent().parent('.option__row').remove()
    }
  });

  var option_val = $('.char__paste #id_char_value')
  var id_name = $('.char__paste #id_name')

  $(option_val).each(function( index ) {
      
      if ($(this).val() == '') {
        $(this).parent().parent('.char__row').remove()
      }
  });
  $(id_name).each(function( index ) {
      
    if ($(this).val() == '') {
      $(this).parent().parent('.char__row').remove()
    }
  });

});

// end Очистка пустых полей при заполнении товара



// Создание поста в блоге

$(document).on('click','.draft',function(e){
    e.preventDefault()
    var action = $(this).attr("data-action")
    $('.form').attr("action", action)
    $('.form').submit()
});




$(document).on('click','.ck-add-new-item',function(e){

  e.preventDefault()
  var parent = $(this).parent('.taxtarea-find') 
  var textareas = parent.find('textarea');
  textareas.each(function () {
    var textareaId = $(this).attr('id'); // Получаем id текущего поля textarea
    CKEDITOR.replace(textareaId); // Инициализируем CKEditor на данном поле
  });

});

// Добавление форм
$(document).on('click','.post-result__text',function(e){
  e.preventDefault()
  var htmlGet = $('.form-text').html()
  $('.post-result__paste').append(htmlGet)
  

});

$(document).on('click','.post-result__title',function(e){
  e.preventDefault()
  var htmlGet = $('.form-title').html()
  $('.post-result__paste').append(htmlGet)
});
$(document).on('click','.post-result__image',function(e){
  e.preventDefault()
  var htmlGet = $('.form-image').html()
  $('.post-result__paste').append(htmlGet)

});
$(document).on('click','.post-result__video',function(e){
  e.preventDefault()
  var htmlGet = $('.form-video').html()
  $('.post-result__paste').append(htmlGet)

});

// .form-hidden__remove
$(document).on('click','.form-hidden__remove',function(e){
  e.preventDefault()
  $(this).parent().remove()
});

$(document).on('click','.post-resul__item',function(e){
  e.preventDefault()

  var count = 0
  $('.post-result__inner form').each(function( ) {
      count +=1
  });
  // console.log(count)
  $('.order-block').val(count)
});



// Удаление блока поста без перезагрузки
$(document).on('click','.post-result__remove',function(e){
  e.preventDefault();
  var url = $(this).attr('href')
  $.get(url, function() {
    $(".post-result").load(location.href + " .post-result__refresh");
  });
});



// ajax для постов
$(function() {
  $(document).on('submit','.form-ajax',function(e){
    var $form = $(this);
    $.ajax({
      type: $form.attr('method'),
      url: $form.attr('action'),
      data: $form.serialize()
    }).done(function() {
      $(".post-result").load(location.href + " .post-result__refresh");
      
    }).fail(function() {
      console.log('fail');
    });
    e.preventDefault();
  });
});

$(function() {
  $(document).on('submit','.form-ajax-file',function(e){
    var $form = $(this);
    
    $.ajax({
			type: $form.attr('method'),
			url: $form.attr('action'),
			cache: false,
			contentType: false,
			processData: false,
			data: new FormData(this),
			dataType : 'json',
      success: function(msg){
        
				if (msg.error == '') {
          
				
				} else {
				
				}
			}
		});
    
    e.preventDefault();

    function explode(){
      $(".post-result").load(location.href + " .post-result__refresh");
    }
    setTimeout(explode, 2000);
   
  });
});


$(document).on('blur','.submit, .ck',function(){
  if($(this).val() != '') {
    $(this).parent().submit()
  }
  
});


$(document).on('change','.submit-file',function(){
  $(this).parent().submit()
});



// end Создание поста в блоге




$(document).on('click','.show',function(e){
  e.preventDefault();
  $('.add-popup').show()
});

$(document).on('click','.add-popup__layout',function(e){
  e.preventDefault();
  $('.add-popup').hide()
});



// add blocks


$(document).ready(function(){ 

  var block_st = $("#id_block_class").val();


  if(block_st=='slider') {

    $('.hidden-inputs__input').remove()

    var slider = $('.hidden-inputs__slider').clone().addClass('hidden-inputs__input')

    $('#id_block_class').after(slider)

  } else if (block_st=='photo') {

    $('.hidden-inputs__input').remove()

    var photo = $('.hidden-inputs__photo').clone().addClass('hidden-inputs__input')

    $('#id_block_class').after(photo)


  } else if (block_st=='video') {
    $('.hidden-inputs__input').remove()


    var video = $('.hidden-inputs__video').clone().addClass('hidden-inputs__input')
    $('#id_block_class').after(video)


  }
  

  $(document).on('click','#id_block_class',function(){

    var block_type = $("#id_block_class").val();

    if(block_type=='slider') {

      $('.hidden-inputs__input').remove()

      var slider = $('.hidden-inputs__slider').clone().addClass('hidden-inputs__input')

      $(this).after(slider)

    } else if (block_type=='photo') {

      $('.hidden-inputs__input').remove()

      var photo = $('.hidden-inputs__photo').clone().addClass('hidden-inputs__input')

      $(this).after(photo)


    } else if (block_type=='video') {
      $('.hidden-inputs__input').remove()


      var video = $('.hidden-inputs__video').clone().addClass('hidden-inputs__input')
      $(this).after(video)


    }

    


  });


 

});

// end add blocks
