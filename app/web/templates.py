from fastapi.templating import Jinja2Templates
from app.config import BASE_DIR, APP_VERSION
from app.web.optionen import VERTRAULICHKEIT_OPTIONS

# Eine gemeinsame Instanz für alle Route-Module. Vorher legte jedes Modul
# seine eigene an (achtmal dieselbe Zeile), wodurch es keinen Ort gab, an dem
# sich etwas für *alle* Templates hinterlegen lässt.
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# Als Jinja-Global verfügbar, damit die Version in base.html steht, ohne dass
# jede einzelne Route sie in ihren Kontext legen muss.
templates.env.globals["app_version"] = APP_VERSION

# Aus demselben Grund die Vertraulichkeitsstufen: sie stehen in fünf Templates,
# die von drei verschiedenen Route-Modulen bedient werden. Über den Kontext
# durchgereicht hiesse das fünf Stellen, an denen sie fehlen kann.
templates.env.globals["vertraulichkeit_options"] = VERTRAULICHKEIT_OPTIONS
