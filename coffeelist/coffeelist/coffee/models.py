import decimal
import re
import StringIO

from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse

from django.core.mail import send_mail

from . import utils

COST_PER_COFFEE = decimal.Decimal(".5")

class CoffeeDrinker(models.Model):
    name = models.CharField(help_text="Name of him (or her) who drinks le coffee", max_length=100)
    email = models.EmailField(help_text="A means to reach the coffee enthusiast")
    deposit = models.DecimalField(help_text="Assets (Splendid!) or debit (Argh!)", max_digits=5, decimal_places=2)
    active = models.BooleanField(help_text="Whether to include this user on coffee lists", default=True)
    prefill = models.IntegerField(help_text="Pre-fill some crosses for this drinker in new lists, for flatrates. If set, only these crosses count, the scan is ignored!", default=0)
    note = models.TextField("Note (for admins)", blank=True)

    def __str__(self):
        return self.name

    __unicode__ = __str__

    def get_absolute_url(self):
        return reverse("view-drinker", args=(self.pk,))

class CoffeeDrinkerAccountingEntry(models.Model):
    coffee_drinker = models.ForeignKey(CoffeeDrinker, related_name="custom_accounting")
    date = models.DateTimeField(verbose_name="Date", auto_now_add=True)
    text = models.CharField(verbose_name="Description", max_length=255, help_text="A detailed description of the transaction")
    amount = models.DecimalField(verbose_name="Amount", max_digits=5, decimal_places=2, help_text="The amount of money deposited into the drinker's account. Use negative values for spendings.")
    related_sheet_entry = models.OneToOneField("CoffeeListEntry", null=True)

    def __str__(self):
        return "For %s on %s: %s [%2.2f]" % (self.coffee_drinker, self.date, self.text, self.amount)

    def __unicode__(self):
        return u"For %s on %s: %s [%2.2f]" % (self.coffee_drinker, self.date, self.text, self.amount)

class BankAccountingEntry(models.Model):
    coffee_drinker = models.ForeignKey(CoffeeDrinker, related_name="bank_accounting", null=True)
    date = models.DateTimeField(verbose_name="Date", auto_now_add=True)
    text = models.CharField(verbose_name="Description", max_length=255, help_text="A detailed description of the transaction")
    amount = models.DecimalField(verbose_name="Amount", max_digits=5, decimal_places=2, help_text="The amount of money deposited into the bank. Use negative values for spendings.")
    attachment = models.FileField(verbose_name="Attachment", help_text="E.g. a scan of a receipt", blank=True)

    def __str__(self):
        return "%sOn %s: %s [%2.2f]" % (("For %s" % self.coffee_drinker) if self.coffee_drinker else "", self.date, self.text, self.amount)

    def __unicode__(self):
        return u"%sOn %s: %s [%2.2f]" % ((u"For %s" % self.coffee_drinker) if self.coffee_drinker else u"", self.date, self.text, self.amount)

class CoffeeList(models.Model):
    pub_date = models.DateField(verbose_name="Publication date", auto_now_add=True)
    processed = models.BooleanField(verbose_name="Processed?", help_text="Whether all pages were scanned", default=False)
    approved = models.BooleanField(verbose_name="Approved?", help_text="Whether this was checked by the team and found ok", default=False)

    def __str__(self):
        return "CoffeeList from %s" % (self.pub_date,)

    def __unicode__(self):
        return "CoffeeList from %s" % (self.pub_date,)

    @transaction.atomic
    def approve(self):
        assert not self.approved

        deposit_changes = {}
        for page in self.pages.all():
            for entry in page.entries.filter(cross_count__gt=0):
                cost = entry.cross_count * COST_PER_COFFEE
                CoffeeDrinkerAccountingEntry.objects.create(coffee_drinker=entry.coffee_drinker,
                                                            text="%d coffee in list from %s" % (entry.cross_count, self.pub_date),
                                                            amount=-cost, related_sheet_entry=entry)
                entry.coffee_drinker.deposit -= cost
                deposit_changes[entry.coffee_drinker.pk] = entry.cross_count, cost
                entry.coffee_drinker.save()

        self.approved = True
        self.save()
        return deposit_changes

    def get_pdf(self, title="Coffee list"):
        lists = []
        for sheet in self.pages.all().order_by("page_number"):
            lists.append((sheet.pk, [ entry.coffee_drinker.name for entry in sheet.entries.all().order_by("position") ] ))

        output_pdf = utils.generate_lists(lists, title)
        output_pdf.seek(0)
        return output_pdf

    @staticmethod
    @transaction.atomic
    def create_new_list(title="Coffee list"):
        drinkers = list(CoffeeDrinker.objects.filter(active=True).order_by("name"))
        new_list = CoffeeList.objects.create()

        current_sheet_number = 0
        lists = []
        while drinkers:
            current_sheet_number += 1
            current_sheet = CoffeeListPage.objects.create(page_number=current_sheet_number,
                                                         coffee_list=new_list)
            sheet_user_number = -1
            names_for_sheet = []
            prefill_for_sheet = {}
            while drinkers and sheet_user_number < utils.COFFEE_COUNT_PER_PAGE - 2:
                drinker = drinkers.pop(0)
                sheet_user_number += 1
                CoffeeListEntry.objects.create(coffee_list_page=current_sheet,
                                               coffee_drinker=drinker,
                                               position=sheet_user_number)

                names_for_sheet.append(drinker.name)
                if drinker.prefill:
                    prefill_for_sheet[drinker.name] = drinker.prefill
            lists.append((current_sheet.pk, names_for_sheet, prefill_for_sheet))

        output_pdf = utils.generate_lists(lists, title)
        output_pdf.seek(0)

        return output_pdf

class CoffeeListPage(models.Model):
    coffee_list = models.ForeignKey(CoffeeList, related_name="pages")
    page_number = models.SmallIntegerField(verbose_name="Page number")
    scan = models.FileField(verbose_name="Scanned coffee list")

    class ScanDeniedError(RuntimeError):
        def __init__(self):
            super(RuntimeError, self).__init__("This sheet has already been approved and can not be scanned again")
    class ScanFailedError(RuntimeError):
        def __init__(self):
            super(RuntimeError, self).__init__("Failed to detect a valid sheet")

    @staticmethod
    @transaction.atomic
    def process_scan(image):
        try:
            marked_image, meta_data, markings, mark_y_positions = utils.scan_list(image)
            page_id = int(re.search("id=([0-9]+)", meta_data).group(1))
        except Exception as e:
            raise CoffeeListPage.ScanFailedError()

        page = CoffeeListPage.objects.get(pk=page_id)
        if page.coffee_list.approved:
            raise CoffeeListPage.ScanDeniedError()

        for entry in CoffeeListEntry.objects.filter(coffee_list_page=page):
            entry.cross_count = markings[entry.position]
            if entry.coffee_drinker.prefill:
                entry.cross_count = entry.coffee_drinker.prefill
            entry.position_in_scan = mark_y_positions[entry.position]
            entry.save()

        scan_data = StringIO.StringIO()
        marked_image.save(scan_data, "JPEG")
        page.scan.save("scan.jpg", ContentFile(scan_data.getvalue()))
        page.save()

        if len(page.coffee_list.pages.filter(scan="")) == 0:
            page.coffee_list.processed = True
            page.coffee_list.save()

        return page

    def get_pdf(self, title="Coffee list"):
        output_pdf = utils.generate_list(self.pk,
                [ entry.coffee_drinker.name for entry in self.entries.all().order_by("position") ],
                title)
        output_pdf.seek(0)
        return output_pdf

    def __str__(self):
        return "CoffeeListPage #%d from %s" % (self.page_number, self.coffee_list.pub_date)

    def __unicode__(self):
        return u"CoffeeListPage #%d from %s" % (self.page_number, self.coffee_list.pub_date)

    def get_absolute_url(self):
        return reverse("view-sheet-image", args=(self.coffee_list.pk, self.page_number))


class CoffeeListEntry(models.Model):
    coffee_list_page = models.ForeignKey(CoffeeListPage, related_name="entries")
    coffee_drinker = models.ForeignKey(CoffeeDrinker, related_name="listings")
    position = models.IntegerField(verbose_name="Position")
    position_in_scan = models.IntegerField(verbose_name="Position in scan", default=0)
    cross_count = models.IntegerField(verbose_name="Number of crosses on this page", default=0)

    def __str__(self):
        return "CoffeeListEntry for %s from %s: %d crosses" % (self.coffee_drinker, self.coffee_list_page.coffee_list.pub_date, self.cross_count)

    def __unicode__(self):
        return u"CoffeeListEntry for %s from %s: %d crosses" % (self.coffee_drinker, self.coffee_list_page.coffee_list.pub_date, self.cross_count)

    def get_absolute_url(self):
        return reverse("view-sheet-image", args=(self.coffee_list_page.coffee_list.pk, self.coffee_list_page.page_number, self.position))
