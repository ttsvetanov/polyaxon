from polyaxon.config_settings.apps import *
from polyaxon.config_settings.auditor_apps import AUDITOR_APPS

PROJECT_APPS = AUDITOR_APPS + (
    'apis.apps.APIsConfig',
)

THIRD_PARTY_APPS = (
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
)

INSTALLED_APPS += THIRD_PARTY_APPS + PROJECT_APPS