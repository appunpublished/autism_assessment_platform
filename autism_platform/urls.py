
from django.contrib import admin
from django.urls import path, include
from assessment.views import ScreeningGUIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('assessment.urls')),
    path('', ScreeningGUIView.as_view(), name='screening-gui'),
]
