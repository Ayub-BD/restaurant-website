from cloudinary.models import CloudinaryField
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class MenuCategory(models.Model):
    """e.g. Burgers, Pizza, Pasta, Drinks -- used to filter the menu."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Menu Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MenuItem(models.Model):
    """A single dish/drink on the menu."""

    category = models.ForeignKey(
        MenuCategory, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=8, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Leave blank if there's no discount to show.",
    )

    # Cloudinary Integration for Media Uploads
    image = CloudinaryField("image", folder="menu", blank=True, null=True)

    is_available = models.BooleanField(
        default=True,
        help_text="Uncheck to hide temporarily (e.g. sold out) without deleting.",
    )
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__display_order", "name"]

    def __str__(self):
        return self.name

    @property
    def discount_percent(self):
        """Returns an int percentage off, or None if there's no old_price to compare."""
        if self.old_price and self.old_price > self.price:
            return round((1 - (self.price / self.old_price)) * 100)
        return None


class Offer(models.Model):
    """A time-bound promotion, e.g. '20% off all pizzas this weekend'."""

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    
    # Cloudinary Integration for Media Uploads
    image = CloudinaryField("image", folder="offers", blank=True, null=True)
    discount_percent = models.PositiveIntegerField(help_text="e.g. 20 for 20% off")

    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(
        default=True,
        help_text="Manual on/off switch. The offer must ALSO be within its date range to show publicly.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        today = timezone.localdate()
        start = (
            self.start_date.date()
            if hasattr(self.start_date, "date")
            else self.start_date
        )
        end = (
            self.end_date.date()
            if hasattr(self.end_date, "date")
            else self.end_date
        )
        return bool(self.is_active and start <= today <= end)

    @property
    def get_discount_value(self):
        return self.discount_percent
