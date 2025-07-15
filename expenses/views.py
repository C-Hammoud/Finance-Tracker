from django.shortcuts import render, redirect, get_object_or_404
from .models import Consumption, Currency
from .forms import ConsumptionCreateForm, ConsumptionEditForm
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime
from calendar import month_name
from decimal import Decimal
import json
from .forms import UserRegisterForm

def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created! You’re now logged in.")
            return redirect("dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegisterForm()

    return render(request, "registration/register.html", {"form": form})




@login_required
def add_expense(request):
    if request.method == "POST":
        form = ConsumptionCreateForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, "Expense added successfully.")
            return redirect("dashboard")
        else:
            messages.error(request, "Could not add expense: " + str(form.errors))
    else:
        form = ConsumptionCreateForm()
    return render(request, "expenses/add_expense.html", {"form": form})


@login_required
def dashboard(request):
    months = [(i, month_name[i]) for i in range(1, 13)]
    years = list(range(2025, datetime.now().year + 1))

    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))

    monthly_expenses = Consumption.objects.filter(
        created_by=request.user,
        date__year=selected_year,
        date__month=selected_month,
        record_status="active",
    )

    total_usd = monthly_expenses.aggregate(Sum('amount_usd'))['amount_usd__sum'] or Decimal('0.00')
    total_count = monthly_expenses.count()

    pie_data = monthly_expenses.values('consumption_type').annotate(total=Sum('amount_usd'))
    labels = [item['consumption_type'].capitalize() for item in pie_data]
    values = [float(item['total']) for item in pie_data]

    breakdown = []
    for label, value in zip(labels, values):
        percent = round((value / float(total_usd)) * 100, 2) if total_usd > 0 else 0
        breakdown.append((label, value, percent))

    context = {
        'months': months,
        'years': years,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'total': total_usd,
        'total_count': total_count,
        'labels': json.dumps(labels),
        'values': json.dumps(values),
        'breakdown': breakdown,
    }

    return render(request, "expenses/dashboard.html", context)


# @login_required
# def monthly_list(request):
#     expenses = Consumption.objects.filter(
#         created_by=request.user,
#         record_status="active"
#     ).order_by('-date', '-amount_usd')

#     paginator = Paginator(expenses, 10)
#     page = request.GET.get("page")
#     expenses_paged = paginator.get_page(page)

#     return render(request, "expenses/monthly_list.html", {
#         'expenses': expenses_paged,
#     })

@login_required
def monthly_list(request):
    months = [(i, month_name[i]) for i in range(1, 13)]
    current_year = datetime.now().year
    years = list(range(2025, current_year + 1))

    selected_month = int(request.GET.get('month', datetime.now().month))
    selected_year  = int(request.GET.get('year', datetime.now().year))

    qs = Consumption.objects.filter(
        created_by=request.user,
        record_status='active',
        date__year=selected_year,
        date__month=selected_month,
    ).order_by('-created_at')

    total_usd = qs.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    expenses_page = paginator.get_page(page_number)

    return render(request, "expenses/monthly_list.html", {
        'months': months,
        'years': years,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'total_usd': total_usd,
        'expenses': expenses_page,
        'consumption_choices': Consumption.TYPE_CHOICES,
        'currency_choices': Currency.choices,
    })


@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Consumption, pk=pk, created_by=request.user)

    if request.method == "POST":
        form = ConsumptionEditForm(request.POST, instance=expense)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.modified_by = request.user
            exp.save()
            messages.success(request, "Expense updated successfully.")
        else:
            messages.error(request, "Could not save changes: " + str(form.errors))
    return redirect("monthly_list")


@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Consumption, pk=pk, created_by=request.user)
    if request.method == "POST":
        expense.record_status = "deleted"
        expense.modified_by = request.user
        expense.save()
        messages.success(request, "Expense deleted successfully.")
    return redirect("monthly_list")
