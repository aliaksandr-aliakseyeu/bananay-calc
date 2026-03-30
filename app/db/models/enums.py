from enum import Enum


class RegionType(str, Enum):
    """Типы регионов РФ."""
    KRAI = "край"
    OBLAST = "область"
    RESPUBLIKA = "республика"
    AVTONOMNAYA_OBLAST = "автономная область"
    AVTONOMNY_OKRUG = "автономный округ"
    GOROD_FED_ZNACHENIYA = "город федерального значения"


class SettlementType(str, Enum):
    """Settlement types."""
    GOROD = "город"
    PGT = "пгт"
    SELO = "село"
    DEREVNYA = "деревня"
    POSELOK = "поселок"
    STANITSA = "станица"
    KHUTOR = "хутор"
    AUL = "аул"


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "ADMIN"
    PRODUCER = "PRODUCER"


class OnboardingStatus(str, Enum):
    """Onboarding status for users."""
    PENDING_EMAIL_VERIFICATION = "PENDING_EMAIL_VERIFICATION"
    PENDING_PROFILE_COMPLETION = "PENDING_PROFILE_COMPLETION"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class TutorialType(str, Enum):
    """Tutorial types for producer dashboard."""
    DASHBOARD_WELCOME = "DASHBOARD_WELCOME"
    DELIVERY_LISTS = "DELIVERY_LISTS"
    PRODUCT_SKU = "PRODUCT_SKU"
    DELIVERY_ORDERS = "DELIVERY_ORDERS"


class TutorialStatus(str, Enum):
    """Tutorial completion status."""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class DriverAccountStatus(str, Enum):
    """Driver account status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    BLOCKED = "blocked"


class DriverApplicationStatus(str, Enum):
    """Driver application (KYC-lite) status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class MediaFileOwnerType(str, Enum):
    """MediaFile owner entity type."""
    DRIVER = "driver"
    APPLICATION = "application"
    SHIFT = "shift"
    ROUTE_STEP = "route_step"
    VEHICLE = "vehicle"
    DAILY_CHECKIN = "daily_checkin"
    DRIVER_DELIVERY_TASK = "driver_delivery_task"
    COURIER = "courier"
    COURIER_DELIVERY_TASK = "courier_delivery_task"


class DriverOtpStatus(str, Enum):
    """Driver OTP code status (one-time use)."""
    PENDING = "pending"
    USED = "used"


class DailyCheckInStatus(str, Enum):
    """Daily check-in (EKF) status."""
    PENDING = "pending"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DailyCheckInPhotoKind(str, Enum):
    """Kind of photo in daily check-in."""
    SELFIE = "selfie"
    VEHICLE_FRONT = "vehicle_front"
    VEHICLE_LEFT = "vehicle_left"
    VEHICLE_RIGHT = "vehicle_right"
    VEHICLE_REAR = "vehicle_rear"
    VEHICLE_CARGO = "vehicle_cargo"


class DcAccountStatus(str, Enum):
    """Distribution center account status."""
    DRAFT = "draft"
    ACTIVE = "active"
    BLOCKED = "blocked"


class DcOtpStatus(str, Enum):
    """Distribution center OTP code status (one-time use)."""
    PENDING = "pending"
    USED = "used"


class CourierAccountStatus(str, Enum):
    """Courier account status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    BLOCKED = "blocked"


class CourierApplicationStatus(str, Enum):
    """Courier application (KYC-lite) status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class CourierOtpStatus(str, Enum):
    """Courier OTP code status (one-time use)."""
    PENDING = "pending"
    USED = "used"


class DeliveryPointAccountStatus(str, Enum):
    """Delivery point account status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class DeliveryPointOtpStatus(str, Enum):
    """Delivery point OTP code status (one-time use)."""
    PENDING = "pending"
    USED = "used"


class CourierTaskStatus(str, Enum):
    """Courier delivery task status."""
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
