"""
CKEditor для админки: основной ckeditor.js с CDN, init — из main/core/ckeditor/
(без collectstatic из site-packages).
Версия full-all соответствует CKEditor 4.18.x в django-ckeditor 6.3.2.
"""
from js_asset import JS
from ckeditor.widgets import CKEditorWidget

# Должен заканчиваться на / — подключаемые lang/skins/plugins идут отсюда.
CKEDITOR_CDN_BASE = "https://cdn.ckeditor.com/4.18.0/full-all/"


class CKEditorWidgetCDN(CKEditorWidget):
    class Media:
        js = (
            JS(
                "ckeditor/ckeditor-init.js",
                {
                    "id": "ckeditor-init-script",
                    "data-ckeditor-basepath": CKEDITOR_CDN_BASE,
                },
            ),
            CKEDITOR_CDN_BASE + "ckeditor.js",
        )
