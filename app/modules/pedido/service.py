from sqlmodel import Session

class PedidoService:
    def __init__(self, session: Session):
        self._session = session
