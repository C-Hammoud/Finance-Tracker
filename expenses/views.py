from django.shortcuts import render, redirect, get_object_or_404
from .models import Consumption
from .forms import ConsumptionForm, ConsumptionEditForm
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from datetime import datetime
from django.contrib import messages
from calendar import month_name
import json


@login_required
def add_expense(request):
    if request.method == "POST":
        form = ConsumptionForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.created_at = datetime.now()
            expense.save()
            return redirect("dashboard")
    else:
        form = ConsumptionForm()
    return render(request, "expenses/add_expense.html", {"form": form})


@login_required
def dashboard(request):
    # Available months and years for dropdowns
    months = [(i, month_name[i]) for i in range(1, 13)]
    years = list(range(2025, datetime.now().year + 1))

    # Get selected month and year from GET params or default to current
    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))

    monthly_expenses = Consumption.objects.filter(
        created_by=request.user,
        date__year=selected_year,
        date__month=selected_month,
        record_status="active",
    )

    total = monthly_expenses.aggregate(Sum("amount"))["amount__sum"] or 0
    total_count = monthly_expenses.count()

    pie_data = monthly_expenses.values("consumption_type").annotate(total=Sum("amount"))

    labels = [item["consumption_type"].capitalize() for item in pie_data]
    values = [float(item["total"]) for item in pie_data]

    breakdown = []
    for label, value in zip(labels, values):
        print(label, value)
        value = float(value)
        percent = round((value / float(total)) * 100, 2) if total > 0 else 0
        breakdown.append((label, value, percent))

    context = {
        "months": months,
        "years": years,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "total": total,
        "total_count": total_count,
        "labels": json.dumps(labels),
        "values": json.dumps(values),
        "breakdown": breakdown,
    }

    return render(request, "expenses/dashboard.html", context)


@login_required
def monthly_list(request):
    expenses = Consumption.objects.filter(
        created_by=request.user, record_status="active"
    ).order_by("-date")

    paginator = Paginator(expenses, 10)
    page = request.GET.get("page")
    expenses_paged = paginator.get_page(page)

    context = {
        "expenses": expenses_paged,
        "consumption_choices": Consumption.TYPE_CHOICES,
    }
    return render(request, "expenses/monthly_list.html", context)

def edit_expense(request, pk):
    expense = get_object_or_404(Consumption, pk=pk, created_by=request.user)

    if request.method == "POST":
        form = ConsumptionEditForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated successfully.")
        else:
            print("Edit Expense form errors:", form.errors)
            messages.error(request, "Could not save changes: " + str(form.errors))
    return redirect("monthly_list")


@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Consumption, pk=pk, created_by=request.user)
    if request.method == "POST":
        expense.record_status = "deleted"
        expense.save()
        messages.success(request, "Expense deleted successfully.")
        return redirect("monthly_list")
    return render(
        request,
        "expenses/confirm_delete.html",
        {
            "expense": expense,
        },
    )
