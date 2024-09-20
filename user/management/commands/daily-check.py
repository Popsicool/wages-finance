from django.core.management import call_command
from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
from user.models import Loan, InvestmentPlan, UserInvestments
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check for overdue loans and expired investment plans and update their status'

    def handle(self, *args, **kwargs):
        self.check_overdue_loans()
        self.check_expired_investment_plans()
        self.check_expired_user_investments()
        self.stdout.write(self.style.SUCCESS('Successfully updated overdue loans, expired user plan and expired investment plans'))

    def check_overdue_loans(self):
        loans = Loan.objects.filter(status='APPROVED')
        for loan in loans:
            if loan.is_overdue():
                loan.status = 'OVERDUE'
                loan.save()

    def check_expired_investment_plans(self):
        today = timezone.now().date()
        investment_plans = InvestmentPlan.objects.filter(is_active=True, end_date__lt=today)
        for plan in investment_plans:
            plan.is_active = False
            plan.save()
    def check_expired_user_investments(self):
        today = timezone.now().date()
        investment_plans = UserInvestments.objects.filter(status="ACTIVE", due_date__lt=today)
        for plan in investment_plans:
            plan.status = "MATURED"
            int_rate = plan.investment.interest_rate * 0.01 * plan.amount
            plan.interest = int_rate
            plan.save()