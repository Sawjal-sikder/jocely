from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Prayer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prayers')
    post = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='prayer_images/', null=True, blank=True)
    video = models.FileField(upload_to='prayer_videos/', null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def total_likes(self):
        return self.likes.count()

    def total_comments(self):
        return self.comments.count()

    def __str__(self):
        title = ""
        if self.post:
            title = (self.post[:47] + '...') if len(self.post) > 50 else self.post
        else:
            title = f"Prayer {self.id}"
        return title


class PrayerLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prayer_likes')
    prayer = models.ForeignKey(Prayer, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'prayer')

    def __str__(self):
        return f"{self.user.email} likes Prayer {self.prayer.id}"
    
class PrayerComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prayer_comments')
    prayer = models.ForeignKey(Prayer, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.email} on Prayer {self.prayer.id}"