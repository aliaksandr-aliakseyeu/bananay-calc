"""
Delivery Order models for tracking product deliveries from producer to delivery points
"""
import enum

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    """Order status enum reflecting multi-stage delivery process"""
    DRAFT = "draft"  # Draft, not yet submitted
    PENDING = "pending"  # Created, waiting to be sent
    IN_TRANSIT_TO_DC = "in_transit_to_dc"  # In transit to Distribution Center
    AT_DC = "at_dc"  # At Distribution Center
    DRIVER_ASSIGNED = "driver_assigned"  # Driver assigned for delivery
    IN_DELIVERY = "in_delivery"  # In delivery process to points
    PARTIALLY_DELIVERED = "partially_delivered"  # Some points delivered
    COMPLETED = "completed"  # All points delivered
    CANCELLED = "cancelled"  # Order cancelled


class OrderPriority(str, enum.Enum):
    """Order priority enum"""
    NORMAL = "normal"  # Normal priority
    HIGH = "high"  # High priority
    URGENT = "urgent"  # Urgent priority


class DeliveryPointStatus(str, enum.Enum):
    """Status for individual delivery points"""
    PENDING = "pending"  # Not yet delivered
    IN_TRANSIT = "in_transit"  # Driver on the way
    DELIVERED = "delivered"  # Successfully delivered
    FAILED = "failed"  # Delivery failed


class DeliveryOrder(Base):
    """
    Delivery order for tracking product deliveries
    Represents a batch of one SKU being delivered to multiple points
    """
    __tablename__ = "delivery_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    producer_id = Column(Integer, ForeignKey("geo_users.id", ondelete="CASCADE"), nullable=False)
    producer_sku_id = Column(Integer, ForeignKey("producer_skus.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False)  # Number of SKU units
    total_cost = Column(Numeric(10, 2), nullable=True)  # Total delivery cost
    cost_per_unit = Column(Numeric(10, 2), nullable=True)  # Cost per SKU unit
    status = Column(SQLEnum(OrderStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=OrderStatus.DRAFT)
    priority = Column(SQLEnum(OrderPriority, values_callable=lambda x: [e.value for e in x]), nullable=False, default=OrderPriority.NORMAL)
    expected_pickup_date = Column(DateTime(timezone=True), nullable=True)  # When producer plans to hand over
    actual_pickup_date = Column(DateTime(timezone=True), nullable=True)  # When actually picked up
    delivery_deadline = Column(DateTime(timezone=True), nullable=True)  # Delivery deadline
    producer_notes = Column(Text, nullable=True)  # Notes from producer
    admin_notes = Column(Text, nullable=True)  # Internal admin notes
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    sent_to_dc_at = Column(DateTime(timezone=True), nullable=True)  # When sent to DC
    arrived_at_dc_at = Column(DateTime(timezone=True), nullable=True)  # When arrived at DC
    driver_assigned_at = Column(DateTime(timezone=True), nullable=True)  # When driver assigned
    delivery_started_at = Column(DateTime(timezone=True), nullable=True)  # When delivery started
    completed_at = Column(DateTime(timezone=True), nullable=True)  # When fully completed

    producer = relationship("User", back_populates="delivery_orders")
    producer_sku = relationship("ProducerSKU", back_populates="delivery_orders")
    delivery_points = relationship(
        "DeliveryOrderPoint",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    status_history = relationship(
        "DeliveryOrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="DeliveryOrderStatusHistory.created_at.desc()",
    )


class DeliveryOrderPoint(Base):
    """
    Individual delivery point within an order
    Stores delivery point directly for the order
    """
    __tablename__ = "delivery_order_points"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("delivery_orders.id", ondelete="CASCADE"), nullable=False)
    delivery_point_id = Column(Integer, ForeignKey("geo_delivery_points.id", ondelete="RESTRICT"), nullable=False)
    status = Column(SQLEnum(DeliveryPointStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=DeliveryPointStatus.PENDING)
    quantity = Column(Integer, nullable=False)  # Number of SKU units for this point
    photo_url = Column(String(500), nullable=True)  # Photo proof of delivery
    delivery_notes = Column(Text, nullable=True)  # Notes about this specific delivery
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)  # When delivered to this point
    order = relationship("DeliveryOrder", back_populates="delivery_points")
    delivery_point = relationship("DeliveryPoint")


class DeliveryOrderStatusHistory(Base):
    """
    Audit log for order status changes
    Tracks who changed status, when, and any notes
    """
    __tablename__ = "delivery_order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("delivery_orders.id", ondelete="CASCADE"), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("geo_users.id", ondelete="SET NULL"), nullable=True)
    old_status = Column(SQLEnum(OrderStatus, values_callable=lambda x: [e.value for e in x]), nullable=True)  # Null for initial creation
    new_status = Column(SQLEnum(OrderStatus, values_callable=lambda x: [e.value for e in x]), nullable=False)
    notes = Column(Text, nullable=True)  # Reason or notes about the change
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    order = relationship("DeliveryOrder", back_populates="status_history")
    changed_by = relationship("User")
