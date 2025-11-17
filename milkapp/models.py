from django.db import models
from django.contrib.auth.models import User

class MilkRecord(models.Model):
    SESSION_CHOICES = [
        ('Morning', 'Morning'),
        ('Evening', 'Evening'),
    ]
    farmer = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    session = models.CharField(max_length=10, choices=SESSION_CHOICES)
    quantity = models.FloatField(help_text="Litres")
    fat_content = models.FloatField(help_text="Fat %")
    snf = models.FloatField(help_text="SNF %", null=True, blank=True)
    rate = models.FloatField(null=True, blank=True) 

    def __str__(self):
        return f"{self.farmer.username} - {self.date} ({self.session})"



