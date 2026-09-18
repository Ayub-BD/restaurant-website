from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from customers.models import Customer
from menu.forms import MenuCategoryForm, MenuItemForm, OfferForm
from menu.models import MenuCategory, MenuItem, Offer
from orders.models import Order, OrderItem, Payment
from reservations.models import Reservation
from reviews.forms import ReviewForm
from reviews.models import Review
from tables.forms import RestaurantTableForm
from tables.models import RestaurantTable

from .decorators import manager_required


def _staff_profile(request):
    """Returns the logged-in user's Staff profile, or None (e.g. for a raw superuser)."""
    return getattr(request.user, "staff_profile", None)


# ------------------------------------------------------------------
# DASHBOARD HOME
# ------------------------------------------------------------------
@manager_required
def dashboard_home(request):
    today = timezone.localdate()

    todays_orders = Order.objects.filter(created_at__date=today)
    todays_revenue = (
        todays_orders.filter(status="completed").aggregate(total=Sum("total"))["total"] or 0
    )

    context = {
        "todays_orders_count": todays_orders.count(),
        "todays_revenue": todays_revenue,
        "pending_orders_count": Order.objects.filter(
            status__in=["pending", "confirmed", "preparing"]
        ).count(),
        "available_tables_count": RestaurantTable.objects.filter(status="available").count(),
        "todays_reservations_count": Reservation.objects.filter(date=today).count(),
        "total_customers": Customer.objects.count(),
        "active_offers_count": len([o for o in Offer.objects.filter(is_active=True) if o.is_currently_active]),
        "pending_reviews_count": Review.objects.filter(is_approved=False).count(),
    }
    context["active"] = "home"
    return render(request, "dashboard/home.html", context)


# ------------------------------------------------------------------
# MENU MANAGEMENT
# ------------------------------------------------------------------
@manager_required
def menu_manage(request):
    if request.method == "POST" and "add_category" in request.POST:
        category_form = MenuCategoryForm(request.POST)
        if category_form.is_valid():
            category_form.save()
            messages.success(request, "Category added.")
            return redirect("dashboard_menu")
        else:
            for field, errors in category_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        category_form = MenuCategoryForm()

    context = {
        "categories": MenuCategory.objects.all(),
        "items": MenuItem.objects.select_related("category").all(),
        "category_form": category_form,
    }
    context["active"] = "menu"
    return render(request, "dashboard/menu.html", context)


@manager_required
def menu_category_edit(request, category_id):
    category = get_object_or_404(MenuCategory, pk=category_id)
    if request.method == "POST":
        form = MenuCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    return redirect("dashboard_menu")


@manager_required
def menu_category_toggle(request, category_id):
    category = get_object_or_404(MenuCategory, pk=category_id)
    if request.method == "POST":
        category.is_active = not category.is_active
        category.save(update_fields=["is_active"])
        messages.success(
            request,
            f"Category '{category.name}' is now {'active' if category.is_active else 'inactive'}.",
        )
    return redirect("dashboard_menu")


@manager_required
def menu_category_delete(request, category_id):
    category = get_object_or_404(MenuCategory, pk=category_id)
    if request.method == "POST":
        if category.items.exists():
            messages.error(
                request,
                f"Can't delete '{category.name}' -- it still has menu items in it. "
                "Move or delete those items first.",
            )
        else:
            category.delete()
            messages.success(request, "Category deleted.")
    return redirect("dashboard_menu")


@manager_required
def menu_item_add(request):
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Menu item added.")
            return redirect("dashboard_menu")
    else:
        form = MenuItemForm()
    return render(request, "dashboard/menu_item_form.html", {"form": form, "mode": "Add", "active": "menu"})


@manager_required
def menu_item_edit(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Menu item updated.")
            return redirect("dashboard_menu")
    else:
        form = MenuItemForm(instance=item)
    return render(request, "dashboard/menu_item_form.html", {"form": form, "mode": "Edit", "active": "menu"})


@manager_required
def menu_item_delete(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Menu item deleted.")
    return redirect("dashboard_menu")


# ------------------------------------------------------------------
# OFFER MANAGEMENT
# ------------------------------------------------------------------
@manager_required
def offer_manage(request):
    return render(request, "dashboard/offers.html", {"offers": Offer.objects.all(), "active": "offers"})


@manager_required
def offer_add(request):
    if request.method == "POST":
        form = OfferForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Offer added.")
            return redirect("dashboard_offers")
    else:
        form = OfferForm()
    return render(request, "dashboard/offer_form.html", {"form": form, "mode": "Add", "active": "offers"})


@manager_required
def offer_edit(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id)
    if request.method == "POST":
        form = OfferForm(request.POST, request.FILES, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, "Offer updated.")
            return redirect("dashboard_offers")
    else:
        form = OfferForm(instance=offer)
    return render(request, "dashboard/offer_form.html", {"form": form, "mode": "Edit", "active": "offers"})


@manager_required
def offer_delete(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id)
    if request.method == "POST":
        offer.delete()
        messages.success(request, "Offer deleted.")
    return redirect("dashboard_offers")


# ------------------------------------------------------------------
# REVIEW MANAGEMENT
# ------------------------------------------------------------------
@manager_required
def review_manage(request):
    return render(request, "dashboard/reviews.html", {"reviews": Review.objects.all(), "active": "reviews"})


@manager_required
def review_add(request):
    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Review added.")
            return redirect("dashboard_reviews")
    else:
        form = ReviewForm(initial={"is_approved": True})
    return render(request, "dashboard/review_form.html", {"form": form, "active": "reviews"})


@manager_required
def review_approve(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    if request.method == "POST":
        review.is_approved = True
        review.save()
        messages.success(request, "Review approved.")
    return redirect("dashboard_reviews")


@manager_required
def review_reject(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    if request.method == "POST":
        review.is_approved = False
        review.save()
        messages.success(request, "Review rejected.")
    return redirect("dashboard_reviews")


@manager_required
def review_delete(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted.")
    return redirect("dashboard_reviews")


# ------------------------------------------------------------------
# POS / ORDER MANAGEMENT
# ------------------------------------------------------------------
NEXT_STATUS = {
    Order.STATUS_CONFIRMED: (Order.STATUS_PREPARING, "Start Preparing"),
    Order.STATUS_PREPARING: (Order.STATUS_READY, "Mark as Ready"),
    Order.STATUS_READY: (Order.STATUS_SERVED, "Mark as Served"),
    Order.STATUS_SERVED: (Order.STATUS_COMPLETED, "Complete Order"),
}


@manager_required
def order_list(request):
    orders = Order.objects.select_related("table").all()
    return render(request, "dashboard/orders.html", {"orders": orders, "active": "orders"})


@manager_required
def pos_start(request):
    if request.method == "POST":
        table = get_object_or_404(RestaurantTable, pk=request.POST.get("table_id"), status="available")
        order = Order.objects.create(table=table, created_by=_staff_profile(request))
        table.status = RestaurantTable.STATUS_OCCUPIED
        table.save(update_fields=["status"])
        return redirect("dashboard_order_detail", order_number=order.order_number)

    tables = RestaurantTable.objects.filter(status="available")
    return render(request, "dashboard/pos_start.html", {"tables": tables, "active": "pos"})


@manager_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    if request.method == "POST":
        if "add_item" in request.POST:
            menu_item = get_object_or_404(MenuItem, pk=request.POST.get("menu_item_id"))
            quantity = int(request.POST.get("quantity", 1) or 1)
            notes = request.POST.get("notes", "")
            OrderItem.objects.create(
                order=order, menu_item=menu_item, quantity=quantity, notes=notes
            )
            order.recalculate_totals()

        elif "remove_item" in request.POST:
            OrderItem.objects.filter(pk=request.POST.get("item_id"), order=order).delete()
            order.recalculate_totals()

        elif "set_discount" in request.POST:
            try:
                offer_id = request.POST.get("discount", "0")
                discount_val = Decimal("0.00")
                
                if offer_id and offer_id != "0":
                    try:
                        selected_offer = Offer.objects.get(pk=offer_id)
                        if hasattr(selected_offer, 'discount_percent'):
                            discount_val = Decimal(str(selected_offer.discount_percent))
                        elif hasattr(selected_offer, 'discount_value'):
                            discount_val = Decimal(str(selected_offer.discount_value))
                    except (Offer.DoesNotExist, ValueError, TypeError):
                        discount_val = Decimal("0.00")
                
                sub = order.subtotal or Decimal("0.00")
                if discount_val > 0 and discount_val <= 100:
                    calculated_discount = (sub * discount_val) / Decimal("100")
                    order.discount = calculated_discount.quantize(Decimal("0.01"))
                else:
                    order.discount = discount_val.quantize(Decimal("0.01"))
                    
            except (ValueError, TypeError, InvalidOperation):
                order.discount = Decimal("0.00")
            
            sub = order.subtotal or Decimal("0.00")
            disc = order.discount or Decimal("0.00")
            tax_val = getattr(order, 'tax', Decimal("0.00")) or Decimal("0.00")
            order.total = max(Decimal("0.00"), sub - disc + tax_val)
            
            order.save(update_fields=["discount", "total"])
            messages.success(request, "Discount applied successfully.")

        elif "confirm_order" in request.POST:
            payment_method = request.POST.get("payment_method")
            order.payment_method = payment_method
            order.save(update_fields=["payment_method"])
            Payment.objects.update_or_create(
                order=order, defaults={"method": payment_method, "amount": order.total}
            )
            order.set_status(Order.STATUS_CONFIRMED, changed_by=_staff_profile(request))
            messages.success(request, f"Order {order.order_number} confirmed.")

        elif "advance_status" in request.POST:
            next_status = NEXT_STATUS.get(order.status)
            if next_status:
                order.set_status(next_status[0], changed_by=_staff_profile(request))
                if next_status[0] == Order.STATUS_COMPLETED and order.table:
                    order.table.status = RestaurantTable.STATUS_AVAILABLE
                    order.table.save(update_fields=["status"])
                messages.success(request, f"Order {order.order_number} is now {next_status[0]}.")

        elif "cancel_order" in request.POST:
            order.set_status(Order.STATUS_CANCELLED, changed_by=_staff_profile(request))
            if order.table:
                order.table.status = RestaurantTable.STATUS_AVAILABLE
                order.table.save(update_fields=["status"])
            messages.success(request, f"Order {order.order_number} cancelled.")

        return redirect("dashboard_order_detail", order_number=order.order_number)

    active_offers = Offer.objects.filter(is_active=True)

    context = {
        "order": order,
        "menu_items": MenuItem.objects.filter(is_available=True).select_related("category"),
        "next_status": NEXT_STATUS.get(order.status),
        "active_offers": active_offers,
    }
    context["active"] = "orders"
    return render(request, "dashboard/order_detail.html", context)


@manager_required
def print_receipt(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, "print/receipt.html", {"order": order})


@manager_required
def print_kitchen_ticket(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, "print/kitchen_ticket.html", {"order": order})


# ------------------------------------------------------------------
# TABLE MANAGEMENT
# ------------------------------------------------------------------
@manager_required
def table_manage(request):
    if request.method == "POST" and "add_table" in request.POST:
        form = RestaurantTableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Table added.")
            return redirect("dashboard_tables")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RestaurantTableForm()

    context = {
        "tables": RestaurantTable.objects.all(),
        "table_form": form,
        "active": "tables",
    }
    return render(request, "dashboard/tables.html", context)


@manager_required
def table_add(request):
    return redirect("dashboard_tables")


@manager_required
def table_edit(request, table_id):
    table = get_object_or_404(RestaurantTable, pk=table_id)
    if request.method == "POST":
        form = RestaurantTableForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            messages.success(request, f"Table {table.table_number} updated.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    return redirect("dashboard_tables")


@manager_required
def table_set_status(request, table_id):
    table = get_object_or_404(RestaurantTable, pk=table_id)
    if request.method == "POST":
        status = request.POST.get("status")
        if status in dict(RestaurantTable.STATUS_CHOICES):
            table.status = status
            table.save(update_fields=["status"])
            messages.success(request, f"Table {table.table_number} marked as {table.get_status_display()}.")
    return redirect("dashboard_tables")


@manager_required
def table_delete(request, table_id):
    table = get_object_or_404(RestaurantTable, pk=table_id)
    if request.method == "POST":
        if table.orders.exists() or table.reservations.exists():
            messages.error(
                request,
                f"Can't delete table {table.table_number} -- it has order/reservation history.",
            )
        else:
            table.delete()
            messages.success(request, "Table deleted.")
    return redirect("dashboard_tables")


# ------------------------------------------------------------------
# RESERVATIONS
# ------------------------------------------------------------------
@manager_required
def reservation_list(request):
    reservations = Reservation.objects.select_related("table", "customer").all()
    context = {
        "reservations": reservations,
        "tables": RestaurantTable.objects.all(),
        "active": "reservations",
    }
    return render(request, "dashboard/reservations.html", context)


@manager_required
def reservation_update(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    if request.method == "POST":
        status = request.POST.get("status")
        table_id = request.POST.get("table_id")

        if status in dict(Reservation.STATUS_CHOICES):
            reservation.status = status

        if table_id:
            reservation.table = get_object_or_404(RestaurantTable, pk=table_id)
            if status == Reservation.STATUS_CONFIRMED:
                reservation.table.status = RestaurantTable.STATUS_RESERVED
                reservation.table.save(update_fields=["status"])
        elif table_id == "":
            reservation.table = None

        reservation.save()
        messages.success(request, f"Reservation for {reservation.name} updated.")

    return redirect("dashboard_reservations")
