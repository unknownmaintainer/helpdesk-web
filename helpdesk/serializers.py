from rest_framework import serializers
from .models import Ticket, CustomUser, TicketUpdate, IncidentAuditLog, MileageReport

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'full_name', 'email', 'role', 'department', 'profile_picture', 'created_at']

class TicketUpdateSerializer(serializers.ModelSerializer):
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = TicketUpdate
        fields = ['id', 'comment', 'updated_by', 'created_at']

class IncidentAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentAuditLog
        fields = ['id', 'actor_label', 'action', 'timestamp']

class LegacyTicketSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    updates = TicketUpdateSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'created_by', 'title', 'category', 'priority', 'source',
            'description', 'attachment', 'status', 'created_at', 'updated_at',
            'updates'
        ]

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'ticket_type', 'nist_stage', 'priority', 'source',
            'is_resolved', 'created_at'
        ]


class MileageReportSerializer(serializers.ModelSerializer):
    driver = UserSerializer(read_only=True)

    class Meta:
        model = MileageReport
        fields = [
            'id', 'driver', 'mileage', 'dashboard_alert',
            'fleet_valuation', 'procurement_cost', 'created_at'
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        
        user = None
        if request and hasattr(request, 'user'):
            user = request.user
            
        is_manager = user and (user.role == 'manager' or user.is_superuser)
        
        if not is_manager:
            representation['fleet_valuation'] = "$*,***,***.**"
            representation['procurement_cost'] = "$**,***.**"
            
        return representation
