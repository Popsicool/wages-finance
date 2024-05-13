from django.contrib import admin
from .models import User, EmailVerification
# Register your models here.
# admin.site.register(User)
class UserAdmin(admin.ModelAdmin):
  
    list_display = ('id','firstname', 'lastname', 'email', 'role')
    search_fields = ('role',)
    # search_fields =  ('first_name', 'last_name', 'matric_number',
    #                 'faculty', 'department', 'block',
    #                 'room', 'bunk', 'space')
    list_per_page = 100
admin.site.register(User, UserAdmin)
admin.site.register(EmailVerification)
