from django.urls import path
from . import views

urlpatterns = [
    # ---------- Basic Pages ----------
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),  # ✅ fixed here
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),

    # ---------- Prediction Pages ----------
    path('predict/price/', views.predict_price, name='predict_price'),
    path('predict/quality/', views.predict_quality, name='predict_quality'),
    path('predict/breed/', views.predict_breed, name='predict_breed'),
    path("predict_price_page/", views.predict_price_page, name="predict_price_page"),

]

