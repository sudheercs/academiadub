from django.urls import path
from .views import CodeRunView

urlpatterns = [
    path("run/", CodeRunView.as_view(), name="codelab-run"),
]
