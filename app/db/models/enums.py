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
