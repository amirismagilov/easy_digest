from django.db import models

class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return self.username or str(self.telegram_id)

class Channel(models.Model):
    username = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class Topic(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class DigestGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    channels = models.ManyToManyField(Channel, related_name="digest_groups")

    def __str__(self):
        return f"{self.user} — {self.name}"

class Post(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    text = models.TextField()
    date = models.DateTimeField()
    topics = models.ManyToManyField(Topic, related_name="posts")

    def __str__(self):
        return f"{self.channel.title} — {self.date.strftime('%Y-%m-%d %H:%M')}"
