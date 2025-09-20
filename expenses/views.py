from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from firebase_admin import auth as fb_auth, firestore
from firebase_client import get_firestore_client, get_storage_bucket

from .firestore_models import ConsumptionFS as Consumption
from .forms import ConsumptionCreateForm, ConsumptionEditForm, UserRegisterForm
from .models import Currency

from datetime import datetime
from calendar import month_name
from decimal import Decimal
import json
import io

# PDF + chart generation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

import matplotlib
matplotlib.use("Agg")   # for headless servers
import matplotlib.pyplot as plt



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

@login_required
def download_dashboard_pdf(request):
    """
    Generate a professional PDF report for the dashboard (month + year).
    Includes summary, styled breakdown table, pie chart, and footer.
    """

    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))

    # --- Fetch Data ---
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

    # --- Metadata ---
    extracted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    extractor_name = request.user.get_full_name() or request.user.username

    # --- Pie Chart ---
    pie_image = None
    if total_usd > 0 and totals:
        fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=100)
        ax.pie(
            list(totals.values()),
            labels=list(totals.keys()),
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 8}
        )
        ax.axis("equal")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", transparent=True)
        plt.close(fig)
        buf.seek(0)
        pie_image = ImageReader(buf)

    # --- PDF Setup ---
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin_x, margin_y = 25 * mm, 20 * mm
    y = height - margin_y

    # --- Header (colored band) ---
    header_h = 22 * mm
    p.setFillColorRGB(0.12, 0.44, 0.71)  # dark blue
    p.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin_x, height - header_h + 8, "Finance Tracker")
    p.setFont("Helvetica", 10)
    p.drawString(margin_x, height - header_h + 2, "Dashboard Report")

    # --- Subtitle ---
    y = height - header_h - 15
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(margin_x, y, f"{month_name[selected_month]} {selected_year}")
    p.setFont("Helvetica", 10)
    p.drawRightString(width - margin_x, y, f"Records: {total_count}")
    y -= 20

    # --- Summary box ---
    p.setFillColor(colors.whitesmoke)
    p.roundRect(margin_x, y - 30, width - 2 * margin_x, 30, 6, fill=1, stroke=1)
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(margin_x + 10, y - 12, f"Total Expenses: {total_usd:,.2f} USD")
    p.setFont("Helvetica", 10)
    p.drawString(margin_x + 10, y - 24, f"Number of Records: {total_count}")
    y -= 50

    # --- Pie chart (centered) ---
    if pie_image:
        chart_w, chart_h = 80 * mm, 80 * mm
        chart_x = (width - chart_w) / 2
        chart_y = y - chart_h
        p.drawImage(pie_image, chart_x, chart_y, chart_w, chart_h, mask="auto")
        y = chart_y - 30

    # --- Breakdown Table ---
    p.setFont("Helvetica-Bold", 12)
    p.drawString(margin_x, y, "Breakdown by Type")
    y -= 18

    if total_usd > 0:
        # Table Header
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_x, y, "Type")
        p.drawRightString(width - margin_x - 100, y, "Amount (USD)")
        p.drawRightString(width - margin_x, y, "%")
        y -= 12
        p.setStrokeColor(colors.grey)
        p.line(margin_x, y, width - margin_x, y)
        y -= 15

        # Table Rows
        p.setFont("Helvetica", 10)
        for label, amt in totals.items():
            percent = (amt / total_usd) * 100
            p.drawString(margin_x, y, label)
            p.drawRightString(width - margin_x - 100, y, f"{amt:,.2f}")
            p.drawRightString(width - margin_x, y, f"{percent:.1f}%")
            y -= 15
            if y < margin_y + 50:  # New page if running out of space
                p.showPage()
                y = height - margin_y
    else:
        p.setFont("Helvetica", 10)
        p.drawString(margin_x, y, "No data available for this period.")
        y -= 20

    # --- Footer ---
    p.setStrokeColor(colors.lightgrey)
    p.setLineWidth(0.5)
    p.line(margin_x, margin_y + 10, width - margin_x, margin_y + 10)
    p.setFont("Helvetica", 8)
    p.drawString(margin_x, margin_y, f"Generated by: {extractor_name}")
    p.drawRightString(width - margin_x, margin_y, f"Extracted: {extracted_at}")

    # Save
    p.save()
    buffer.seek(0)

    filename = f"Finance_Dashboard_{month_name[selected_month]}_{selected_year}.pdf"
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'
    return response
