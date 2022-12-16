from django.contrib import admin

from ticket.models import Event, TicketType, Ticket, OrderState, Order
# Register your models here.

admin.site.register(Event)
admin.site.register(TicketType)
admin.site.register(Ticket)
admin.site.register(OrderState)
admin.site.register(Order)
