from django.core.management import call_command
from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
from user.models import Loan, InvestmentPlan, UserInvestments, UserSavings, Activities, CoporativeMembership
from django.utils import timezone
from django.db import transaction
import calendar

class Command(BaseCommand):
    help = 'Check for overdue loans and expired investment plans and update their status'

    def handle(self, *args, **kwargs):
        self.check_overdue_loans()
        self.check_expired_investment_plans()
        self.check_expired_user_investments()
        self.check_matured_user_savings()
        self.update_monthly_dividend()
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

    def update_monthly_dividend(self):
        today = timezone.now()
        last_day = calendar.monthrange(today.year, today.month)[1]
        
        # Check if today is the last day of the month
        if today.day == last_day:
            active_memberships = CoporativeMembership.objects.filter(is_active=True)
            
            for membership in active_memberships:
                closing_balance = membership.balance
                dividend = round(0.02 * closing_balance)  # 2% of the balance
                
                # Prepare the entry for monthly_dividend
                month_year = today.strftime('%B %Y')
                entry = {
                    "date": today.strftime('%Y-%m-%d'),
                    "closing_balance": closing_balance,
                    "dividend": dividend,
                    "status": False
                }
                
                # Update the monthly_dividend field
                monthly_dividend = membership.monthly_dividend or {}  # if it's empty
                monthly_dividend[month_year] = entry
                
                membership.monthly_dividend = monthly_dividend
                membership.save()


