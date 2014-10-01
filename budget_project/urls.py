from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', 'budget_app.views.profile'),
    url(r'^budget_app/', include('budget_app.urls')),

    url(r'^accounts/', include('django.contrib.auth.urls')),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
