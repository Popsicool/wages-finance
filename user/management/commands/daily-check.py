from django.core.management import call_command
from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
from user.models import Loan, InvestmentPlan, UserInvestments, UserSavings, Activities, CoporativeMembership, SavingsActivities
from django.utils import timezone
from django.db import transaction
import calendar
from datetime import datetime, timedelta
class Command(BaseCommand):
    help = 'Check for overdue loans and expired investment plans and update their status'

    def handle(self, *args, **kwargs):
        self.check_loan_repayment()
        self.check_overdue_loans()
        self.check_expired_investment_plans()
        self.check_expired_user_investments()
        self.check_matured_user_savings()
        self.update_monthly_dividend()
        self.check_savings()
        self.stdout.write(self.style.SUCCESS('Successfully updated overdue loans, expired user plan and expired investment plans'))

    def check_savings(self):
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
                        user.wallet_balance -= remaining_amount
                        user.wages_point += 5
                        user.save()
                        ttday = datetime.now().date()
                        days_to_withdrawal = (saving.withdrawal_date - ttday).days
                        interest = days_to_withdrawal * 0.000329 * remaining_amount

                        # Log the savings activity
                        new_savings_activity = SavingsActivities.objects.create(
                            savings=saving,
                            amount=remaining_amount,
                            balance=saving.saved,
                            user=user,
                            interest=interest
                        )
                        new_savings_activity.save()

                        # Save the updated state of saving
                        saving.save()  # Save to prevent the same payment from being processed again

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

    def check_loan_repayment(self):
        today = timezone.now().date()
        today_str = today.strftime("%d/%m/%Y")

        # Find all active loans where repayment_details are not null
        loans = Loan.objects.filter(is_active=True, repayment_details__isnull=False)

        for loan in loans:
            repayment_details = loan.repayment_details

            # Check if there's a payment scheduled for today in the repayment details
            if today_str in repayment_details:
                details = repayment_details[today_str]

                # Ensure the payment hasn't already been made
                if not details['paid_status']:
                    user = loan.user
                    amount_due = details['amount']

                    # Atomic block to ensure the entire transaction is either fully completed or rolled back
                    try:
                        with transaction.atomic():
                            # Check if user has enough balance in their wallet
                            if user.wallet_balance >= amount_due:
                                # Deduct the amount from the user's wallet
                                user.wallet_balance -= amount_due
                                user.wages_point += 5
                                # Update the repayment details to mark this payment as paid
                                repayment_details[today_str]['paid_status'] = True
                                loan.repayment_details = repayment_details
                                all_repaid = all(detail['paid_status'] for detail in repayment_details.values())
                                if all_repaid:
                                    loan.is_active = False
                                    loan.status = "REPAYED"
                                    loan.balance = 0
                                else:
                                    loan.balance -= amount_due
                                loan.amount_repayed += amount_due
                                Activities.objects.create(title="Loan Repayment", amount=amount_due, user=user)
                                loan.save()
                                user.save()

                    except Exception as e:
                        # Catch any exceptions and output an error message
                        pass