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
    """Типы населенных пунктов."""
    GOROD = "город"
    PGT = "пгт"
    SELO = "село"
    DEREVNYA = "деревня"
    POSELOK = "поселок"
    STANITSA = "станица"
    KHUTOR = "хутор"
    AUL = "аул"
