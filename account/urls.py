from django.conf.urls import url
from account.views import login

urlpatterns = [
    # login
    url(r'^/user_login$', login.user_login, name="account-user-login"),
    url(r'^/user_logout$', login.user_logout, name="account-user-logout"),
    url(r'^/check_login', login.check_login, name="account-check-login"),
]