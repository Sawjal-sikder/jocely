from django.contrib import admin
from .models import Prayer, PrayerLike, PrayerComment


@admin.register(Prayer)
class PrayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post_preview', 'total_likes', 'total_comments', 'is_active', 'create_at')
    list_filter = ('is_active', 'create_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'post')
    readonly_fields = ('create_at', 'updated_at', 'total_likes', 'total_comments')
    list_editable = ('is_active',)
    ordering = ('-create_at',)
    
    def post_preview(self, obj):
        return obj.post[:100] + '...' if len(obj.post) > 100 else obj.post
    post_preview.short_description = 'Post Preview'


@admin.register(PrayerLike)
class PrayerLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'prayer_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'prayer__post')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def prayer_preview(self, obj):
        return obj.prayer.post[:50] + '...' if len(obj.prayer.post) > 50 else obj.prayer.post
    prayer_preview.short_description = 'Prayer'


@admin.register(PrayerComment)
class PrayerCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'prayer_preview', 'comment_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'prayer__post', 'comment')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def prayer_preview(self, obj):
        return obj.prayer.post[:30] + '...' if len(obj.prayer.post) > 30 else obj.prayer.post
    prayer_preview.short_description = 'Prayer'
    
    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'
