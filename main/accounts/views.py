# account/views.py
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from allauth.account.forms import SignupForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render


from setup.models import ThemeSettings
try:
    theme_address = ThemeSettings.objects.get().name
except:
    theme_address = 'default'


from django.shortcuts import render, get_object_or_404
from .models import UserProfile


from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from allauth.account.views import SignupView, _ajax_response



from django.contrib import messages

from django.contrib.sites.shortcuts import get_current_site
from django.http import (
    Http404,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateResponseMixin, TemplateView, View
from django.views.generic.edit import FormView

from allauth.exceptions import ImmediateHttpResponse
from allauth.utils import get_form_class, get_request_param
from allauth.account import app_settings, signals
from allauth.account.adapter import get_adapter

from .forms import (
    AddEmailForm,
    ChangePasswordForm,
    LoginForm,
    ResetPasswordForm,
    ResetPasswordKeyForm,
    SetPasswordForm,
    SignupForm,
    UserTokenForm,
    ProfileForm
)
from allauth.account.models import EmailAddress, EmailConfirmation, EmailConfirmationHMAC
from allauth.account.utils import (
    complete_signup,
    get_login_redirect_url,
    get_next_redirect_url,
    logout_on_password_change,
    passthrough_next_redirect_url,
    perform_login,
    sync_user_email_addresses,
    url_str_to_user_pk,
)

from allauth.account.views import RedirectAuthenticatedUserMixin, AjaxCapableProcessFormViewMixin, CloseableSignupMixin

INTERNAL_RESET_URL_KEY = "set-password"
INTERNAL_RESET_SESSION_KEY = "_password_reset_key"


sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters("oldpassword", "password", "password1", "password2")
)


class SignUpView(generic.CreateView):
    
    template_name = 'account/signup.html'
    

class Login(LoginView):
    template_name = 'account/login.html'


class Logout(LogoutView):
    template_name = 'account/logged_out.html'



from .forms import ProfileForm
@login_required
def profile(request):
    user = request.user

    try:
        user_profile = user.profile
    except:
        user_profile = UserProfile(user=user)
        user_profile.save()

    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        telephone = request.POST['telephone']
        address = request.POST['address']
        apartment = request.POST['apartment']
        postal_code = request.POST['postal_code']
        city = request.POST['city']

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        user_profile.telephone = telephone
        user_profile.address = address
        user_profile.apartment = apartment
        user_profile.postal_code = postal_code
        user_profile.city = city
        user_profile.save()

        return redirect('account:account_profile')
    

    default_data = {
        'first_name': user.first_name, 
        'last_name': user.last_name, 
        'telephone': user_profile.telephone, 
        'address': user_profile.address, 
        'apartment': user_profile.apartment, 
        'postal_code': user_profile.postal_code, 
        'city': user_profile.city, 
    }
    profile_form = ProfileForm(default_data)

    context = {
        'user': user, 
        'profile_form': profile_form,
        
    }

    return render(request, 'account/profile.html', context)



@login_required
def profile_orders(request):


    
    return render(request, 'account/profile_orders.html')



@login_required
def profile_wishlist(request):
    
    return render(request, 'account/profile_wishlist.html')


@login_required
def profile_history(request):
    

    context = {

    }

    return render(request, 'account/profile_history.html', context)



@login_required
def profile_update(request):
    
    context = {

    }

    return render(request, 'account/profile_update.html', context)






class LoginView(RedirectAuthenticatedUserMixin, AjaxCapableProcessFormViewMixin, FormView):
    form_class = LoginForm
    # template_name = "account/login." + app_settings.TEMPLATE_EXTENSION
    template_name = 'account/login.html'
    success_url = None
    redirect_field_name = "next"

    @sensitive_post_parameters_m
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(LoginView, self).get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_form_class(self):
        return get_form_class(app_settings.FORMS, "login", self.form_class)

    def form_valid(self, form):
        success_url = self.get_success_url()
        try:
            return form.login(self.request, redirect_url=success_url)
        except ImmediateHttpResponse as e:
            return e.response

    def get_success_url(self):
        # Explicitly passed ?next= URL takes precedence
        ret = (
            get_next_redirect_url(self.request, self.redirect_field_name)
            or self.success_url
        )
        return ret

    def get_context_data(self, **kwargs):
        ret = super(LoginView, self).get_context_data(**kwargs)
        signup_url = passthrough_next_redirect_url(
            self.request, reverse("account_signup"), self.redirect_field_name
        )
        redirect_field_value = get_request_param(self.request, self.redirect_field_name)
        site = get_current_site(self.request)

        ret.update(
            {
                "signup_url": signup_url,
                "site": site,
                "redirect_field_name": self.redirect_field_name,
                "redirect_field_value": redirect_field_value,
            }
        )
        return ret


login = LoginView.as_view()





class SignupView(
    RedirectAuthenticatedUserMixin,
    CloseableSignupMixin,
    AjaxCapableProcessFormViewMixin,
    FormView,
    ):
    template_name = 'account/signup.html'
    form_class = SignupForm
    redirect_field_name = "next"
    success_url = None

    @sensitive_post_parameters_m
    def dispatch(self, request, *args, **kwargs):
        return super(SignupView, self).dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return get_form_class(app_settings.FORMS, "signup", self.form_class)

    def get_success_url(self):
        # Explicitly passed ?next= URL takes precedence
        ret = (
            get_next_redirect_url(self.request, self.redirect_field_name)
            or self.success_url
        )
        return ret

    def form_valid(self, form):
        # By assigning the User to a property on the view, we allow subclasses
        # of SignupView to access the newly created User instance
        self.user = form.save(self.request)
        try:
            return complete_signup(
                self.request,
                self.user,
                app_settings.EMAIL_VERIFICATION,
                self.get_success_url(),
            )
        except ImmediateHttpResponse as e:
            return e.response

    def get_context_data(self, **kwargs):
        ret = super(SignupView, self).get_context_data(**kwargs)
        form = ret["form"]
        email = self.request.session.get("account_verified_email")
        if email:
            email_keys = ["email"]
            if app_settings.SIGNUP_EMAIL_ENTER_TWICE:
                email_keys.append("email2")
            for email_key in email_keys:
                form.fields[email_key].initial = email
        login_url = passthrough_next_redirect_url(
            self.request, reverse("account_login"), self.redirect_field_name
        )
        redirect_field_name = self.redirect_field_name
        site = get_current_site(self.request)
        redirect_field_value = get_request_param(self.request, redirect_field_name)
        ret.update(
            {
                "login_url": login_url,
                "redirect_field_name": redirect_field_name,
                "redirect_field_value": redirect_field_value,
                "site": site,
            }
        )
        return ret


signup = SignupView.as_view()