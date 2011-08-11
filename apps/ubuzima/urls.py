#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.conf.urls.defaults import *
import ubuzima.views as views

urlpatterns = patterns('',
    url(r'^ubuzima$', views.index),
    url(r'^ubuzima/reporter/(?P<pk>\d+)$', views.by_reporter),
    url(r'^ubuzima/patient/(?P<pk>\d+)$', views.by_patient),
    url(r'^ubuzima/type/(?P<pk>\d+)$', views.by_type),
    url(r'^ubuzima/triggers$', views.triggers),
    url(r'^ubuzima/trigger/(?P<pk>\d+)$', views.trigger),
    url(r'^ubuzima/reminders$', views.view_reminders),
    url(r'^ubuzima/reminders/type/(?P<pk>\d+)$', views.remlog_by_type),
    url(r'^ubuzima/report/(?P<pk>\d+)$', views.view_report),
    url(r'^ubuzima/stats$', views.view_stats),
    url(r'^ubuzima/stats/csv$', views.view_stats_csv),
    url(r'^ubuzima/stats/reports/csv$', views.view_stats_reports_csv),
    url(r'^ubuzima/indicator/(?P<indic>\d+)/(?P<format>html|csv)$', views.view_indicator),
    url(r'^ubuzima/important/(?P<format>\w+)/(?P<dat>\w+)$',
        views.important_data),
    url(r'^ubuzima/stats/anc$',
        views.view_anc),
    url(r'^ubuzima/stats/anc/(?P<format>\w+)/(?P<dat>\w+)$',
        views.anc_stats),
    url(r'^ubuzima/stats/chihe$',views.view_chihe),
    url(r'^ubuzima/stats/chihe/(?P<format>\w+)/(?P<dat>\w+)$',
        views.chihe_stats),
    url(r'^ubuzima/stats/death$', views.view_death),
    url(r'^ubuzima/stats/death/(?P<format>\w+)/(?P<dat>\w+)$',
        views.death_stats),
    url(r'^ubuzima/stats/pregnancy$', views.view_pregnancy),
    url(r'^ubuzima/stats/pregnancy/(?P<format>\w+)/(?P<dat>\w+)$',
        views.pregnancy_stats),
    url(r'^ubuzima/location/(?P<pk>\d+)$', views.by_location),
    url(r'^ubuzima/locationcache$', views.shorthand_locations)
)
