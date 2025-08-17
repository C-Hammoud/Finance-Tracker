from django.shortcuts import render, redirect
from .firestore_models import ConsumptionFS as Consumption
from .forms import ConsumptionCreateForm, ConsumptionEditForm, UserRegisterForm
from firebase_admin import auth as fb_auth, firestore
from firebase_client import get_firestore_client, get_storage_bucket
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from datetime import datetime
from calendar import month_name
from decimal import Decimal
import json
from .models import Currency

def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_user = authenticate(
                request,
                username=form.cleaned_data.get("username"),
                password=form.cleaned_data.get("password1"),
            )
            if auth_user is not None:
                login(request, auth_user)
            else:
                user.backend = "django.contrib.auth.backends.ModelBackend"
                login(request, user)
            messages.success(request, "Account created! You’re now logged in.")
            return redirect("dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegisterForm()
    return render(request, "registration/register.html", {"form": form})

def upload_to_firebase(file_obj, filename):
    bucket = get_storage_bucket()
    if bucket is None:
        raise RuntimeError("Firebase storage bucket not initialized.")
    blob = bucket.blob(filename)
    blob.upload_from_file(file_obj)
    blob.make_public()
    return blob.public_url

@login_required
def add_expense(request):
    if request.method == "POST":
        form = ConsumptionCreateForm(request.POST)
        if form.is_valid():
            expense = form.save(created_by=request.user)
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
    current_year = 2025
    print(f"Current year: {current_year}")
    start_year = 2025
    years = [(y) for y in range(start_year, current_year + 2)]
    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))

    try:
        all_items = Consumption.list(limit=2000)
    except Exception as e:
        print(f"Error fetching Firestore data: {e}")
        all_items = []

    monthly = [
        i for i in all_items
        if i.record_status == "active"
        and i.created_by == str(request.user.id)
        and getattr(i, "date", None) is not None
        and i.date.year == selected_year
        and i.date.month == selected_month
    ]

    total_usd = sum([float(i.amount_usd) for i in monthly]) if monthly else 0.0
    total_count = len(monthly)

    totals = {}
    for i in monthly:
        key = (i.consumption_type or "other").capitalize()
        totals[key] = totals.get(key, 0.0) + float(i.amount_usd)

    labels = list(totals.keys())
    values = [totals[k] for k in labels]
    breakdown = []
    for label, value in zip(labels, values):
        percent = round((value / total_usd) * 100, 2) if total_usd > 0 else 0
        breakdown.append((label, value, percent))

    context = {
        "months": months,
        "years": years,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "total": total_usd,
        "total_count": total_count,
        "labels": json.dumps(labels),
        "values": json.dumps(values),
        "breakdown": breakdown,
    }
    return render(request, "expenses/dashboard.html", context)

@login_required
def monthly_list(request):
    months = [(i, month_name[i]) for i in range(1, 13)]
    current_year = datetime.now().year
    years = list(range(2025, current_year + 1))

    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))

    try:
        all_items = Consumption.list(limit=2000)
    except Exception as e:
        print(f"Error fetching Firestore data: {e}")
        all_items = []

    qs = [
        i for i in all_items
        if i.record_status == "active"
        and i.created_by == str(request.user.id)
        and getattr(i, "date", None) is not None
        and i.date.year == selected_year
        and i.date.month == selected_month
    ]
    qs.sort(key=lambda x: getattr(x, "created_at", datetime.min), reverse=True)

    total_usd = sum([float(i.amount_usd) for i in qs]) if qs else Decimal('0.00')

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    expenses_page = paginator.get_page(page_number)

    return render(request, "expenses/monthly_list.html", {
        'months': months,
        'years': years,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'total_usd': total_usd,
        'expenses': expenses_page,
        'consumption_choices': [(c, c.capitalize()) for c in ['market', 'transport' , 'food', 'other']],
        'currency_choices': Currency.choices,
    })

@login_required
def edit_expense(request, pk):
    inst = Consumption.get(str(pk))
    if not inst or inst.created_by != str(request.user.id):
        messages.error(request, "Expense not found or not owned by you.")
        return redirect("monthly_list")

    if request.method == "POST":
        form = ConsumptionEditForm(request.POST, instance=inst)
        if form.is_valid():
            form.save(modified_by=request.user)
            messages.success(request, "Expense updated successfully.")
            return redirect("monthly_list")
        else:
            messages.error(request, "Could not save changes: " + str(form.errors))
    else:
        form = ConsumptionEditForm(instance=inst)
    return render(request, "expenses/edit_expense.html", {"form": form})

@login_required
def delete_expense(request, pk):
    inst = Consumption.get(str(pk))
    if not inst or inst.created_by != str(request.user.id):
        messages.error(request, "Expense not found or not owned by you.")
        return redirect("monthly_list")
    if request.method == "POST":
        inst.record_status = "deleted"
        inst.modified_by = str(request.user.id)
        inst.modified_at = datetime.utcnow()
        inst.save()
        messages.success(request, "Expense deleted successfully.")
    return redirect("monthly_list")

@csrf_exempt
def firebase_token_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    token = request.POST.get("idToken") or request.headers.get("Authorization")
    if not token:
        return JsonResponse({"error": "missing token"}, status=400)
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]

    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception:
        return JsonResponse({"error": "invalid token"}, status=401)

    uid = decoded.get("uid")
    email = decoded.get("email", "")
    name = decoded.get("name") or decoded.get("displayName") or ""
    photo = decoded.get("picture")
    email_verified = decoded.get("email_verified", False)

    try:
        db = get_firestore_client()
        user_ref = db.collection("users").document(uid)
        snapshot = user_ref.get()
        user_payload = {
            "uid": uid,
            "email": email,
            "name": name,
            "photo": photo,
            "email_verified": email_verified,
        }
        if not snapshot.exists:
            user_ref.set({
                **user_payload,
                "created_at": firestore.SERVER_TIMESTAMP,
                "last_login": firestore.SERVER_TIMESTAMP,
            })
        else:
            user_ref.update({
                **user_payload,
                "last_login": firestore.SERVER_TIMESTAMP,
            })
    except Exception as e:
        print(f"Firestore error: {e}")

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=uid,
        defaults={"email": email, "first_name": name or ""}
    )
    if not created and email and user.email != email:
        user.email = email
        user.save(update_fields=["email"])

    login(request, user)
    return JsonResponse({"ok": True})