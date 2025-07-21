from django.contrib import admin

from .models import Category, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'author', 'category',
        'created_at', 'updated_at'
    ]
    search_fields = ['title', 'content']
    list_filter = ['author', 'category', 'tags', 'created_at']
    date_hierarchy = 'created_at'