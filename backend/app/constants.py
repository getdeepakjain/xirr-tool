from enum import Enum


class AssetClass(str, Enum):
    MF = "MF"
    STOCKS = "Stocks"
    FD = "FD"
    BONDS = "Bonds"
    NPS = "NPS"
    PF = "PF"
    CRYPTO = "Crypto"
    POLICIES = "Policies"
    GRATUITY = "Gratuity"


ASSET_CLASSES = [a.value for a in AssetClass]


class TxnType(str, Enum):
    BUY = "buy"           # money going in (investment / contribution / premium)
    SELL = "sell"         # money coming out (redemption / withdrawal)
    DIVIDEND = "dividend"  # payout received while holding
    CASHBACK = "cashback"  # policy survival benefit / cashback


# Asset classes whose current value is quantity * latest unit price.
UNIT_PRICED = {AssetClass.MF.value, AssetClass.STOCKS.value, AssetClass.NPS.value, AssetClass.CRYPTO.value}
