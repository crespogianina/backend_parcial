from sqlmodel import SQLModel, Session, create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)

def create_db_and_tables() -> None:
    import app.modules.categoria.models  # noqa: F401
    import app.modules.direcciones.model  # noqa: F401
    import app.modules.ingrediente.models  # noqa: F401
    import app.modules.pago.models  # noqa: F401
    import app.modules.pedido.models  # noqa: F401
    import app.modules.producto.models  # noqa: F401
    import app.modules.usuarios.model  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session