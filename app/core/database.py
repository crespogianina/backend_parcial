from sqlmodel import SQLModel, Session, create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)

def create_db_and_tables() -> None:
    import app.modules.usuarios.model
    import app.modules.categoria.models
    import app.modules.ingrediente.models
    import app.modules.producto.models
    import app.modules.direcciones.model
    import app.modules.pedido.models
    import app.modules.pago.models
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session