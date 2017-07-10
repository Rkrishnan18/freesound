#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.contrib.auth.models import User
from django.db.models import Count
from django.core.management.base import BaseCommand
from django.core.cache import cache
from donations.models import DonationsEmailSettings
from sounds.models import Download
from donations.models import Donation
from utils.mail import send_mail_template
import datetime
import logging

logger = logging.getLogger("web")

class Command(BaseCommand):
    help = 'Send donation emails'

    def handle(self, **options):
        logger.info("Sending donation emails")

        donation_settings, _ = DonationsEmailSettings.objects.get_or_create()

        # Send reminder email to users that donated more than N days ago.
        donation_time_span = datetime.datetime.now()-datetime.timedelta(days=donation_settings.minimum_days_since_last_donation)
        email_sent = User.objects.filter(profile__last_donation_email_sent__gt=donation_time_span)

        # Get all donations older than X days for which we didn't sent an email to the user
        donations = Donation.objects.filter(user__isnull=False, created__lte=donation_time_span).exclude(user__in=email_sent)
        for donation in donations.all():
            # Check if the user is uploader
            if not donation_settings.never_send_email_to_uploaders or donation.user.profile.num_sounds == 0:
                # Check if there exists a donation in the last X days for the user, otherwise send email
                last_donation = Donation.objects.filter(user=donation.user, created__gt=donation_time_span)
                if last_donation.count() == 0:
                    send_mail_template(
                        u'Donation',
                        'donations/email_donation_reminder.txt', {
                            'user': donation.user,
                            }, None, donation.user.email)
                    donation.user.profile.last_donation_email_sent = datetime.datetime.now()
                    donation.user.profile.save()
                    logger.info("Reminder of donation sent to user %i" % donation.user_id)

        # Send email to users that downloaded more than X sounds in the last Y days
        # excluding uploaders and excluding users that donated in less than Z days.
        email_time_span = datetime.datetime.now()-datetime.timedelta(days=donation_settings.minimum_days_since_last_donation_email)
        email_sent = User.objects.filter(profile__last_donation_email_sent__gt=email_time_span)
        donations = Donation.objects.filter(user__isnull=False, created__gt=donation_time_span).values_list('user_id', flat=True)
        # Get number of downloads in last Z days for each user excluding those that donated and those that received an email
        users_downloads = Download.objects.filter(created__gte=email_time_span).exclude(user__in=email_sent)\
                .exclude(user_id__in=donations).values('user_id').annotate(num_download=Count('user_id'))\
                .order_by('num_download')
        for user in users_downloads.all():
            if user['num_download'] > donation_settings.downloads_in_period:
                user = User.objects.get(id=user['user_id'])
                # Check if the user is an uploader
                if not donation_settings.never_send_email_to_uploaders or user.profile.num_sounds == 0:
                    # If the user has donated in the past count the number of downloads after the donation "expired"
                    last_donation = Donation.objects.filter(user=user, created__gt=donation_time_span).order_by('-created')
                    user_downloads = None
                    if last_donation.count() > 0:
                        donation = last_donation.first()
                        if donation.created > email_time_span:
                            downloads_date_interval = donation.created
                        else:
                            downloads_date_interval = email_time_span
                        user_downloads = Download.objects.filter(created__gte=downloads_date_interval, user=user).count()
                    if last_donation.count() == 0 or user_downloads > donation_settings.downloads_in_period:
                        send_mail_template(
                            u'Donation',
                            'donations/email_donation_request.txt', {
                                'user': user,
                                }, None, user.email)
                        user.profile.last_donation_email_sent = datetime.datetime.now()
                        user.profile.save()
                        logger.info("Donation request sent to user %i" % user.id)

        logger.info("Finished sending donation emails")
