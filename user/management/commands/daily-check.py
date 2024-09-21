from django.core.management import call_command
from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
from user.models import Loan, InvestmentPlan, UserInvestments, UserSavings, Activities
from django.utils import timezone
from django.db import transaction

class Command(BaseCommand):
    help = 'Check for overdue loans and expired investment plans and update their status'

    def handle(self, *args, **kwargs):
        self.check_overdue_loans()
        self.check_expired_investment_plans()
        self.check_expired_user_investments()
        self.check_matured_user_savings()
        self.stdout.write(self.style.SUCCESS('Successfully updated overdue loans, expired user plan and expired investment plans'))

    def check_overdue_loans(self):
        loans = Loan.objects.filter(status='APPROVED')
        for loan in loans:
            if loan.is_overdue():
                loan.status = 'OVERDUE'
                loan.save()

    def check_expired_investment_plans(self):
        today = timezone.now().date()
        investment_plans = InvestmentPlan.objects.filter(is_active=True, end_date__lte=today)
        for plan in investment_plans:
            plan.is_active = False
            plan.save()
    def check_expired_user_investments(self):
        today = timezone.now().date()
        investment_plans = UserInvestments.objects.filter(status="ACTIVE", due_date__lte=today)
        for plan in investment_plans:
            plan.status = "MATURED"
            int_rate = plan.investment.interest_rate * 0.01 * plan.amount
            plan.interest = int_rate
            plan.save()
    def check_matured_user_savings(self):
        today = timezone.now().date()
        all_user_savings =  UserSavings.objects.filter(withdrawal_date__lte=today, is_active=True)
        for user_savings in all_user_savings:
            refund = user_savings.saved + user_savings.interest
            with transaction.atomic():
                user = user_savings.user
                user.wallet_balance += refund
                user.save()
                user_savings.amount = 0
                user_savings.saved = 0
                user_savings.is_active = False
                user_savings.withdrawal_date = None
                user_savings.start_date = None
                user_savings.target_amount = None
                user_savings.goal_met = False
                user_savings.payment_details = None
                user_savings.interest = 0
                user_savings.time = None
                user_savings.day_week = None
                user_savings.day_month = None
                user_savings.save()
                Activities.objects.create(title="Savings Payout", amount=refund, user=user, activity_type="CREDIT")

            # new_savings_activity = SavingsActivities.objects.create(savings=user_savings, amount=refund,
            #                                                         balance = 0, interest=0,
            #                                                         user=user, activity_type="WITHDRAWAL")
            # new_savings_activity.save()


