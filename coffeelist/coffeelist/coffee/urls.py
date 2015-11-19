from django.conf.urls import include, url
from django.contrib import admin

from . import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^edit-coffee-drinker$', views.edit_drinker, name="edit-drinker"),
    url(r'^edit-coffee-drinker/(?P<drinker_id>[0-9]+)$', views.edit_drinker, name="edit-drinker"),
    url(r'^edit-coffee-drinker/(?P<drinker_id>[0-9]+)/deposit$', views.edit_drinker_make_deposit, name="make-deposit"),
    url(r'^view-coffee-drinker/(?P<drinker_id>[0-9]+)$', views.view_drinker, name="view-drinker"),
    url(r'^new-sheet$', views.new_sheet, name="new-sheet"),
    url(r'^upload-sheet$', views.upload_sheet, name="upload-sheet"),
    url(r'^sheet/(?P<sheet_id>[0-9]+)$', views.view_sheet, name="view-sheet"),
    url(r'^sheet/(?P<sheet_id>[0-9]+)/(?P<page>[0-9]+)(?:/(?P<position>[0-9]+))?$', views.view_sheet_image, name="view-sheet-image"),
    url(r'^sheet/(?P<sheet_id>[0-9]+)/(?P<page>[0-9]+)/reverse$', views.reverse_sheet_page_click, name="reverse-sheet-page-click"),
    url(r'^sheet/(?P<sheet_id>[0-9]+)/(?P<page>[0-9]+)/fix$', views.fix_sheet_page_click, name="fix-sheet-page-click"),
    url(r'^sheet/(?P<sheet_id>[0-9]+)/approve$', views.approve_sheet, name="approve-sheet"),
    url(r'^sheet/(?P<sheet_id>[0-9]+)/download$', views.download_sheet, name="download-sheet"),
	url(r'^new-bank-accounting-entry$', views.new_bank_accounting_entry, name="new-bank-accounting-entry"),
	url(r'^view-attachment/(?P<log_id>[0-9]+)', views.view_attachment, name="view-attachment"),
]
