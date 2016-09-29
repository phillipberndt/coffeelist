from constance import config
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.db.models import Sum
from django.http import Http404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from django.utils.encoding import force_text

from wsgiref.util import FileWrapper

import StringIO
import os
import decimal
import mimetypes
import PIL.Image

from . import forms
from . import models
from . import utils
from . import mail

from utils import COFFEE_LINE_HEIGHT

def render_index_page(request, context=None):
    new_drinker_form = forms.NewCoffeeDrinkerForm()
    sheet_list = models.CoffeeList.objects.filter(processed=True).order_by("-pub_date")
    upload_form = forms.ManualSheetUpload()
    bank_transactions = ()
    bank_amount = 0
    deposited = 0
    bank_accounting_entry_form = forms.BankAccountingEntryForm()
    drinkers = models.CoffeeDrinker.objects.order_by("-active", "name")
    if request.user.is_authenticated():
        bank_transactions = models.BankAccountingEntry.objects.order_by("-date")
        try:
            bank_amount = decimal.Decimal(models.BankAccountingEntry.objects.aggregate(Sum("amount"))["amount__sum"])
        except TypeError:
            bank_amount = 0
        try:
            deposited = decimal.Decimal(models.CoffeeDrinker.objects.filter(deposit__gt=0).aggregate(Sum("deposit"))["deposit__sum"])
        except TypeError:
            deposited = 0
        if request.POST and "load_more" in request.POST:
            start = int(request.POST["load_more"])
            return render(request, "index-transaction.html", { "bank_transactions": bank_transactions[start:start+10] })
    else:
        drinkers = drinkers.filter(active=True)
    rcontext = {
        "new_drinker_form": new_drinker_form,
        "drinkers": drinkers,
        "sheet_list": sheet_list,
        "upload_form": upload_form,
        "bank_transactions": bank_transactions[:10],
        "total_transactions": len(bank_transactions),
        "bank_amount": bank_amount,
        "bank_accounting_entry_form": bank_accounting_entry_form,
        "intro_text": getattr(config, "COFFEE_PAGE_INTRO_TEXT", ""),
        "surplus": bank_amount - deposited,
    }
    rcontext.update(context or {})
    return render(request, "index.html", rcontext)

def index(request):
    return render_index_page(request)

@login_required
def edit_drinker(request, drinker_id=None):
    drinker = None
    if drinker_id:
        drinker = get_object_or_404(models.CoffeeDrinker, pk=drinker_id)
        drinker_form = forms.CoffeeDrinkerForm(request.POST if request.POST else None, instance=drinker)
    else:
        drinker_form = forms.NewCoffeeDrinkerForm(request.POST)
    if request.POST and drinker_form.is_valid():
        drinker = drinker_form.save(commit=False)
        if not drinker_id:
            drinker.active = True
            drinker.deposit = 0.0
        drinker.save()
    return render(request, "edit-drinker.html", {"drinker_form": drinker_form, "drinker": drinker})

@login_required
@transaction.atomic
def edit_drinker_make_deposit(request, drinker_id):
    drinker = get_object_or_404(models.CoffeeDrinker, pk=drinker_id)
    amount = decimal.Decimal(request.POST["amount"] or "0.0")
    account_globally = "account_globally" in request.POST and request.POST["account_globally"]
    if "description" in request.POST and request.POST["description"]:
        description = request.POST["description"]
    else:
        if amount > 0:
            description = "Made a deposit"
        else:
            description = "Made a withdrawal"
        if not account_globally:
            description = "%s (Fixup)" % description
    models.CoffeeDrinkerAccountingEntry.objects.create(coffee_drinker=drinker, amount=amount, text=description)
    if amount:
        if account_globally:
            models.BankAccountingEntry.objects.create(coffee_drinker=drinker, amount=amount, text="User %s made a %s" % (drinker, "deposit" if amount > 0 else "withdrawal"))
        drinker.deposit += amount
        drinker.save()
    return redirect(reverse("view-drinker", args=(drinker.pk,)))

def view_drinker(request, drinker_id=None):
    drinker = get_object_or_404(models.CoffeeDrinker, pk=drinker_id)
    transactions = drinker.custom_accounting.order_by("-date")
    deposit_form = forms.DepositForm()
    if request.POST and "load_more" in request.POST:
        start = int(request.POST["load_more"])
        return render(request, "drinker-transaction.html", { "transactions": transactions[start:start+10] })
    return render(request, "view-drinker.html", {
        "drinker": drinker,
        "transactions": transactions[:10],
        "total_transactions": len(transactions),
        "deposit_form": deposit_form
    })

@login_required
def new_sheet(request):
    output_pdf = models.CoffeeList.create_new_list("Coffee list")

    response = HttpResponse(FileWrapper(output_pdf), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=coffee-list.pdf'
    return response

@login_required
def upload_sheet(request):
    upload_form = forms.ManualSheetUpload(request.POST, request.FILES)
    if upload_form.is_valid():
        try:
            page = models.CoffeeListPage.process_scan(PIL.Image.open(request.FILES["sheet"]))
            return redirect(reverse("view-sheet", args=(page.coffee_list.pk,)))
        except models.CoffeeListPage.ScanDeniedError as e:
            upload_form.add_error("sheet", e.message)
        except models.CoffeeListPage.ScanFailedError as e:
            upload_form.add_error("sheet", e.message)
    return render_index_page(request, { "upload_form": upload_form })

def view_sheet(request, sheet_id):
    sheet = get_object_or_404(models.CoffeeList, pk=sheet_id)
    cross_count = sheet.pages.aggregate(sum=Sum("entries__cross_count"))["sum"]
    COST_PER_COFFEE = getattr(config, "COST_PER_COFFEE", decimal.Decimal(".5"))
    try:
        first_entry = sheet.pages.get(page_number=1).entries.get(position=0)
        mail_preview = mail.render_balance_mail({
            first_entry.coffee_drinker.pk: (first_entry.cross_count, COST_PER_COFFEE * first_entry.cross_count),
        }, first_entry.coffee_drinker)
    except:
        mail_preview = False
    upload_form = forms.ManualSheetUpload()
    return render(request, "view-sheet.html", {
        "sheet": sheet,
        "mail_preview": mail_preview,
        "upload_form": upload_form,
        "cross_count": cross_count,
    })

def view_sheet_image(request, sheet_id, page, position=None):
    sheet = get_object_or_404(models.CoffeeListPage, page_number=page, coffee_list__pk=sheet_id)
    if not sheet.scan:
        raise Http404
    sheet.scan.open()
    image = PIL.Image.open(sheet.scan)
    if position:
        entry = sheet.entries.get(position=position)
        image = image.crop((0, entry.position_in_scan, image.size[0], entry.position_in_scan + int(COFFEE_LINE_HEIGHT * 100) - 5))
    outfile = StringIO.StringIO()
    image.save(outfile, format="JPEG")
    outfile.seek(0)
    return HttpResponse(outfile, content_type="image/jpeg")

def reverse_sheet_page_click(request, sheet_id, page):
    sheet = get_object_or_404(models.CoffeeListPage, page_number=page, coffee_list__pk=sheet_id)
    y = int(request.GET["y"]) - 40
    entry = sheet.entries.filter(position_in_scan__gte=y).order_by("position_in_scan")[0]
    return redirect(reverse("view-drinker", args=(entry.coffee_drinker.pk,)))

@login_required
@csrf_protect
def fix_sheet_page_click(request, sheet_id, page):
    sheet = get_object_or_404(models.CoffeeListPage, page_number=page, coffee_list__pk=sheet_id)
    y = int(request.GET["y"]) - 40
    try:
        entry = sheet.entries.filter(position_in_scan__gte=y).order_by("position_in_scan")[0]
    except IndexError:
        return JsonResponse({ "error": "The entry could not be found, processing failed." })
    if request.POST:
        entry.cross_count = request.POST["cross_count"]
        entry.save()
    return JsonResponse({ "cross_count": entry.cross_count, "name": force_text(entry.coffee_drinker) })

@login_required
def approve_sheet(request, sheet_id):
    sheet = get_object_or_404(models.CoffeeList, pk=sheet_id)
    deposit_changes = sheet.approve()
    mail.send_balance_mails(deposit_changes)
    return redirect(reverse("view-sheet", args=(sheet_id,)))

@login_required
def download_sheet(request, sheet_id):
    sheet = get_object_or_404(models.CoffeeList, pk=sheet_id)
    outfile = sheet.get_pdf()
    outfile.seek(0)
    return HttpResponse(outfile, content_type="application/pdf")

@login_required
def new_bank_accounting_entry(request):
    new_entry = forms.BankAccountingEntryForm(request.POST, request.FILES)
    if new_entry.is_valid():
        new_entry.save()
        return redirect("/")
    return render_index_page(request, {"bank_accounting_entry_form": new_entry})

@login_required
def view_attachment(request, log_id):
    log_entry = get_object_or_404(models.BankAccountingEntry, pk=log_id)
    response = HttpResponse(log_entry.attachment, content_type=mimetypes.guess_type(log_entry.attachment.name)[0])
    response["Content-Disposition"] = "inline; filename=%s" % (os.path.basename(log_entry.attachment.name),)
    return response
