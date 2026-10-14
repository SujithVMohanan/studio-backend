from django.urls import path

from apps.studios.views import CreateClassApiView, GetClassesApiView

app_name = "classes"

urlpatterns = [
    path("create-class/", CreateClassApiView.as_view(), name="create-class"),
    path("get-classes/", GetClassesApiView.as_view(), name="get-classes"),
]
