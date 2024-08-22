from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import calendar
from user.models import UserSavings, SavingsActivities

class Command(BaseCommand):
    help = 'Processes User Savings payments'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        now_time = timezone.now().time()

        savings = UserSavings.objects.filter(
            start_date__lte=today, 
            withdrawal_date__gte=today, 
            goal_met=False
        ).exclude(withdrawal_date__isnull=True)
        
        for saving in savings:
            user = saving.user
            if user.wallet_balance < saving.amount:
                continue

            if saving.frequency == 'DAILY':
                if saving.time == now_time :
                    saving.mark_payment_as_made(today, saving.amount)
                    user.wallet_balance -= saving.amount
                    user.save()

            elif saving.frequency == 'WEEKLY':
                if saving.day_week == today.strftime('%A') and saving.time == now_time :
                    saving.mark_payment_as_made(today, saving.amount)
                    user.wallet_balance -= saving.amount
                    user.save()

            elif saving.frequency == 'MONTHLY':
                if saving.day_month:
                    last_day_of_month = calendar.monthrange(today.year, today.month)[1]

                    # Check if it's the last day of the month and the specified day is not reached
                    if today.day == last_day_of_month and saving.day_month > today.day:
                        payment_date = today.replace(day=saving.day_month)
                    else:
                        payment_date = today

                    if payment_date.day == saving.day_month and saving.time == now_time :
                        saving.mark_payment_as_made(payment_date, saving.amount)
                        user.wallet_balance -= saving.amount
                        user.save()
            new_savings_activity = SavingsActivities.objects.create(savings=savings, amount=saving.amount,
                                                                    balance = savings.saved,
                                                                    user=user)
            new_savings_activity.save()
            # saving.save()

        self.stdout.write(self.style.SUCCESS('Successfully processed user savings payments.'))
