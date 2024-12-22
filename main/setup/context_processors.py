from .models import BaseSettings, CustomCode, Colors, ThemeSettings

def setup(request):
    try:
        setup = BaseSettings.objects.get()
    except:
        setup = []
    return {'setup': setup}


def codes(request):
    try:
        codes = CustomCode.objects.all()
    except:
        codes = []
    return {'codes': codes}


def colors(request):
    try:
        colors = Colors.objects.get()
    except:
        colors = []
    return {'colors': colors}


def theme(request):
    try:
        theme = ThemeSettings.objects.get()
    except:
        theme = []
    return {'theme': theme}