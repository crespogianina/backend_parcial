from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.pago.repository import PagoRepository


class PagoUnitOfWork(UnitOfWork):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pagos = PagoRepository(session)
