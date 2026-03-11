
from django.contrib import admin
from django.urls import path, include
from assessment.views import LandingView, ParentPortalView, ScreeningGUIView

urlpatterns = [
    path('', include('assessment.portal_urls')),
    path('api/', include('assessment.urls')),
    path('', LandingView.as_view(), name='landing'),
    path('assessment/page/', ScreeningGUIView.as_view(), name='screening-gui'),
    path('parent/', ParentPortalView.as_view(), name='parent-portal'),
    path('admin/', admin.site.urls),
]
