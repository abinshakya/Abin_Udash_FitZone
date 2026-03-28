from django.db import models

class HomeBanner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.TextField()
    image = models.ImageField(upload_to='banners/')
    link_text = models.CharField(max_length=50, default='Get Started')
    link_url = models.CharField(max_length=200, default='#')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class PremiumService(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='services/')
    button_text = models.CharField(max_length=50, default='Learn More')
    button_url = models.CharField(max_length=200, default='#')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title