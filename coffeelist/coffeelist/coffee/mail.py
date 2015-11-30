# encoding: utf-8

from django.core import mail
from django.db.models import Q
from django.template.loader import get_template
from django.template import Context
from django.conf import settings

from . import models

def render_balance_mail(deposit_changes, drinker, mail_template=None):
    if mail_template is None:
        mail_template = get_template("balance-mail.txt")
    cross_count, cost = deposit_changes.get(drinker.pk, (0, 0))
    mail_text = mail_template.render(Context({
        "drinker": drinker,
        "cross_count": cross_count,
        "cost": cost,
        "signature": getattr(settings, "COFFEE_SIGNATURE", "- coffee team -"),
        "homepage": getattr(settings, "COFFEE_HOMEPAGE", "-"),
    }))
    return mail_text


def send_balance_mails(deposit_changes):
    """
        Inform users of their current balance if it changed in a recent
        approval or if they are in debt.

        Parameters:
            deposit_changes: A dictionary mapping CoffeeDrinker.pk to
                             (cross_count, cost) tuples.
    """
    messages = []
    drinkers = models.CoffeeDrinker.objects.filter((Q(deposit__lt=0) | Q(pk__in=deposit_changes.keys())) & ~Q(email=""))
    mail_template = get_template("balance-mail.txt")
    for drinker in drinkers:
        mail_text = render_balance_mail(deposit_changes, drinker, mail_template)
        messages.append(mail.EmailMessage("Coffee balance", mail_text, settings.EMAIL_SENDER, (drinker.email,),
                                          headers={"Content-Type": "text/plain; charset=utf8"}))

    connection = mail.get_connection()
    connection.open()
    connection.send_messages(messages)
    connection.close()
