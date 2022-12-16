from datetime import datetime, timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets, exceptions, generics, status
from rest_framework.decorators import action

from .models import Event, TicketType, Order, OrderState, Ticket
from .serializers import EventSerializer, TicketTypeSerializer, OrderSerializer


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.prefetch_related('ticket_types')


class OrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet, mixins.UpdateModelMixin):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        order = serializer.save(user=self.request.user)
        order.book_tickets()
        if not order.fulfilled:
            order.delete()
            raise exceptions.ValidationError("Couldn't book tickets")


class OrderCancellation(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def partial_update(self, request, *args, **kwargs):
        try:
            order_to_cancel = self.get_object()
        except Exception as e:
            return JsonResponse(status=status.HTTP_400_BAD_REQUEST,
                                data={"success": False, "errors": f"Cancellation failed: {e}"})

        timediff_minutes = (datetime.now(timezone.utc) - order_to_cancel.created).total_seconds() / 60

        if timediff_minutes > 30:
            return JsonResponse(status=status.HTTP_200_OK, data={"success": False,
                                                                 "errors": "Cancellation is not available anymore"})

        updated_order = order_to_cancel.__dict__
        new_state = get_object_or_404(OrderState, name='Cancelled')
        updated_order['state_id'] = new_state.id

        serializer = self.serializer_class(order_to_cancel, data=updated_order, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(status=status.HTTP_200_OK, data=serializer.data)

        return JsonResponse(status=status.HTTP_400_BAD_REQUEST, data={"success": False,
                                                                      "errors": "Cancellation failed"})


class CustomStatistics(viewsets.ViewSet):

    @action(detail=False, url_path=r"event/(?P<pk>\d+)")
    def event_stats(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        ticket_types = TicketType.objects.filter(event_id=event.pk)
        orders = Order.objects.filter(ticket_type_id__in=ticket_types)
        cancelled = Order.objects.filter(ticket_type_id__in=ticket_types, state__name='Cancelled')

        cancelled_percentage = 100 * float(len(cancelled))/float(len(orders))

        results = {
            'Event': f'{event.pk} - {event.name}',
            'total_orders': len(orders),
            'total_cancelled_orders': len((cancelled)),
            'cancellation_rate': f'{cancelled_percentage}%'
        }
        return JsonResponse(status=status.HTTP_200_OK, data=results)

    @action(detail=False, url_path=r"cancellation_dates")
    def event_stats(self, request):

        total_tickets = Ticket.objects.all()

        max_cancelled = 0
        max_cancelled_date = None

        for ticket in total_tickets:
            if ticket.order.state.name == 'Cancelled':
                if ticket.order.quantity > max_cancelled:
                    max_cancelled = ticket.order.quantity
                    max_cancelled_date = ticket.order.created

        """
        !!! Not sure what date is requested, so for the sake of the test I used the only available date.
            It could be any date stored.
            Could be the date of the event, the date of the purchase or the date of cancellation.
        """

        results = {
            'date with most cancelled tickets': f'{max_cancelled_date}',
            'Maximum cancelled tickets ': max_cancelled,
        }
        return JsonResponse(status=status.HTTP_200_OK, data=results)
