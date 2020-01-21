from django.contrib import admin
from privatemessages.models import Thread, Message

# Register your models here.
@admin.register(Thread)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Message)
class TopicAdmin(admin.ModelAdmin):
    pass
