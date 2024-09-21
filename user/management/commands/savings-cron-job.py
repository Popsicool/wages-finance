from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from user.models import UserSavings, SavingsActivities

class Command(BaseCommand):
    help = 'Processes User Savings payments'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        savings = UserSavings.objects.filter(
            start_date__lte=today,
            withdrawal_date__gte=today,
            goal_met=False
        ).exclude(withdrawal_date__isnull=True)

        for saving in savings:
            with transaction.atomic():  # Start an atomic transaction
                user = saving.user
                payment_made = False
                remaining_amount = saving.amount  # Start with the full amount to be paid

                if saving.frequency == 'DAILY':
                    # Check if a payment has already been made today
                    for entry_str, details in saving.payment_details.items():
                        entry_datetime = datetime.strptime(entry_str, '%d/%m/%Y %H:%M:%S')
                        if entry_datetime.date() == today:
                            if details['paid_status']:
                                remaining_amount -= details['amount']  # Deduct the amount already paid
                            if remaining_amount <= 0:
                                payment_made = True
                                break

                elif saving.frequency == 'WEEKLY':
                    # Check if a payment has already been made in the last 6 days
                    start_of_week = today - timedelta(days=6)
                    for entry_str, details in saving.payment_details.items():
                        entry_datetime = datetime.strptime(entry_str, '%d/%m/%Y %H:%M:%S')
                        if start_of_week <= entry_datetime.date() <= today:
                            if details['paid_status']:
                                remaining_amount -= details['amount']  # Deduct the amount already paid
                            if remaining_amount <= 0:
                                payment_made = True
                                break

                elif saving.frequency == 'MONTHLY':
                    # Check if a payment has already been made in the last 30 days
                    start_of_month = today - timedelta(days=30)
                    for entry_str, details in saving.payment_details.items():
                        entry_datetime = datetime.strptime(entry_str, '%d/%m/%Y %H:%M:%S')
                        if start_of_month <= entry_datetime.date() <= today:
                            if details['paid_status']:
                                remaining_amount -= details['amount']  # Deduct the amount already paid
                            if remaining_amount <= 0:
                                payment_made = True
                                break

                if not payment_made and remaining_amount > 0:
                    if user.wallet_balance >= remaining_amount:
                        payment_datetime = timezone.now()
                        saving.mark_payment_as_made(payment_datetime, remaining_amount)
                        ttday = datetime.now().date()
                        days_to_withdrawal = (saving.withdrawal_date - ttday).days
                        interest = days_to_withdrawal * 0.000329 * remaining_amount
                        saving.all_time_saved += interest
                        saving.interest += interest
                        user.wallet_balance -= remaining_amount
                        user.save()

                        # Log the savings activity
                        new_savings_activity = SavingsActivities.objects.create(
                            savings=saving,
                            amount=remaining_amount,
                            balance=saving.saved,
                            user=user
                        )
                        new_savings_activity.save()

                        # Save the updated state of saving
                        saving.save()  # Save to prevent the same payment from being processed again

        self.stdout.write(self.style.SUCCESS('Successfully processed user savings payments.'))
