from django.contrib import admin
from .models import User, Channel, Topic, DigestGroup, Post

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username')
    search_fields = ('telegram_id', 'username')

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('username', 'title')
    search_fields = ('username', 'title')

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(DigestGroup)
class DigestGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name',)
    filter_horizontal = ('channels',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('channel', 'date')
    list_filter = ('channel', 'date')
    search_fields = ('text',)
    filter_horizontal = ('topics',)

