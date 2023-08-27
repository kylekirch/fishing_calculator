from django.urls import path
from . import views #from current directory

app_name = "calculator"
urlpatterns = [
    path("", views.index, name="index"), #when example.com/calculator is opened
    path("calculate", views.calculate, name="calculate"),
]