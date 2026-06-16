import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.core.security import hash_password, create_access_token
from app.modules.usuarios.model import Usuario, Rol, UsuarioRol
from app.modules.categoria.models import Categoria
from app.modules.ingrediente.models import Ingrediente
from app.modules.producto.models import Producto, ProductoCategoria, UnidadMedida
from app.modules.pedido.models import Pedido, DetallePedido, HistorialEstadoPedido
from app.modules.pago.models import Pago
from app.modules.direcciones.model import DireccionEntrega

import app.modules.usuarios.model      # noqa: F401
import app.modules.categoria.models    # noqa: F401
import app.modules.ingrediente.models  # noqa: F401
import app.modules.producto.models     # noqa: F401
import app.modules.direcciones.model   # noqa: F401
import app.modules.pedido.models       # noqa: F401
import app.modules.pago.models         # noqa: F401

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def override_get_session():
        yield session
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="seed_roles")
def seed_roles_fixture(session: Session):
    roles = [
        Rol(codigo="ADMIN", nombre="Administrador"),
        Rol(codigo="CLIENT", nombre="Cliente"),
        Rol(codigo="STOCK", nombre="Stock"),
        Rol(codigo="PEDIDOS", nombre="Pedidos"),
    ]
    for r in roles:
        if not session.get(Rol, r.codigo):
            session.add(r)
    session.commit()


@pytest.fixture(name="seed_formas_pago")
def seed_formas_pago_fixture(session: Session):
    from app.modules.pedido.models import FormaPago
    formas = [
        FormaPago(codigo="MERCADOPAGO", nombre="MercadoPago", habilitado=True),
        FormaPago(codigo="EFECTIVO", nombre="Efectivo", habilitado=True),
        FormaPago(codigo="TRANSFERENCIA", nombre="Transferencia", habilitado=True),
    ]
    for f in formas:
        if not session.get(FormaPago, f.codigo):
            session.add(f)
    session.commit()


@pytest.fixture(name="seed_estados_pedido")
def seed_estados_pedido_fixture(session: Session):
    from app.modules.pedido.models import EstadoPedido
    estados = [
        EstadoPedido(codigo="PENDIENTE", descripcion="Pendiente", es_terminal=False),
        EstadoPedido(codigo="CONFIRMADO", descripcion="Confirmado", es_terminal=False),
        EstadoPedido(codigo="EN_PREPARACION", descripcion="En preparación", es_terminal=False),
        EstadoPedido(codigo="ENTREGADO", descripcion="Entregado", es_terminal=True),
        EstadoPedido(codigo="CANCELADO", descripcion="Cancelado", es_terminal=True),
    ]
    for e in estados:
        if not session.get(EstadoPedido, e.codigo):
            session.add(e)
    session.commit()


@pytest.fixture(name="seed_unidades_medida")
def seed_unidades_medida_fixture(session: Session):
    unidades = [
        UnidadMedida(nombre="Kilogramo", simbolo="kg", tipo="peso", factor=1000),
        UnidadMedida(nombre="Gramo", simbolo="g", tipo="peso", factor=1),
        UnidadMedida(nombre="Litro", simbolo="L", tipo="volumen", factor=1000),
        UnidadMedida(nombre="Mililitro", simbolo="ml", tipo="volumen", factor=1),
        UnidadMedida(nombre="Unidad", simbolo="ud", tipo="contable", factor=1),
        UnidadMedida(nombre="Porción", simbolo="porciones", tipo="contable", factor=1),
    ]
    for u in unidades:
        session.add(u)
    session.commit()
    session.flush()
    return session.query(UnidadMedida).all()


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session, seed_roles):
    user = Usuario(
        username="test_admin",
        nombre="Test",
        apellido="Admin",
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UsuarioRol(usuario_id=user.id, rol_codigo="ADMIN"))
    session.commit()
    uid = user.id
    session.expunge(user)
    user.id = uid
    return user


@pytest.fixture(name="client_user")
def client_user_fixture(session: Session, seed_roles):
    user = Usuario(
        username="test_client",
        nombre="Test",
        apellido="Client",
        email="client@test.com",
        password_hash=hash_password("Client1234!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UsuarioRol(usuario_id=user.id, rol_codigo="CLIENT"))
    session.commit()
    uid = user.id
    session.expunge(user)
    user.id = uid
    return user


@pytest.fixture(name="pedidos_user")
def pedidos_user_fixture(session: Session, seed_roles):
    user = Usuario(
        username="test_pedidos",
        nombre="Test",
        apellido="Pedidos",
        email="pedidos@test.com",
        password_hash=hash_password("Pedidos1234!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UsuarioRol(usuario_id=user.id, rol_codigo="PEDIDOS"))
    session.commit()
    uid = user.id
    session.expunge(user)
    user.id = uid
    return user


@pytest.fixture(name="stock_user")
def stock_user_fixture(session: Session, seed_roles):
    user = Usuario(
        username="test_stock",
        nombre="Test",
        apellido="Stock",
        email="stock@test.com",
        password_hash=hash_password("Stock1234!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UsuarioRol(usuario_id=user.id, rol_codigo="STOCK"))
    session.commit()
    uid = user.id
    session.expunge(user)
    user.id = uid
    return user


def get_auth_headers(session: Session, user: Usuario) -> dict[str, str]:
    roles = session.query(UsuarioRol).filter(UsuarioRol.usuario_id == user.id).all()
    roles_codigos = [r.rol_codigo for r in roles]
    token = create_access_token(
        data={"sub": str(user.id), "roles": roles_codigos}
    )
    return {"access_token": token}


@pytest.fixture(name="categoria_base")
def categoria_base_fixture(session: Session):
    cat = Categoria(nombre="Categoría Test", descripcion="Para tests")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    cid = cat.id
    session.expunge(cat)
    cat.id = cid
    return cat


@pytest.fixture(name="unidad_ud")
def unidad_ud_fixture(session: Session, seed_unidades_medida):
    return session.query(UnidadMedida).filter(UnidadMedida.simbolo == "ud").first()


@pytest.fixture(name="unidad_g")
def unidad_g_fixture(session: Session, seed_unidades_medida):
    return session.query(UnidadMedida).filter(UnidadMedida.simbolo == "g").first()


@pytest.fixture(name="ingrediente_base")
def ingrediente_base_fixture(session: Session, unidad_g):
    ing = Ingrediente(
        nombre="Carne de res test",
        descripcion="Para tests",
        es_alergeno=False,
        stock_cantidad=1000,
        precio_base=100.0,
        unidad_medida_id=unidad_g.id,
    )
    session.add(ing)
    session.commit()
    session.refresh(ing)
    iid = ing.id
    session.expunge(ing)
    ing.id = iid
    return ing


@pytest.fixture(name="producto_final")
def producto_final_fixture(session: Session, categoria_base, unidad_ud):
    prod = Producto(
        nombre="Producto Final Test",
        descripcion="Para tests",
        precio_base=1000.0,
        stock_cantidad=50,
        disponible=True,
        es_producto_final=True,
        unidad_medida_id=unidad_ud.id,
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)
    session.add(ProductoCategoria(
        producto_id=prod.id,
        categoria_id=categoria_base.id,
        es_principal=True,
    ))
    session.commit()
    pid = prod.id
    session.expunge(prod)
    prod.id = pid
    return prod


@pytest.fixture(name="pedido_pendiente")
def pedido_pendiente_fixture(session: Session, client_user, producto_final, seed_estados_pedido, seed_formas_pago):
    pedido = Pedido(
        usuario_id=client_user.id,
        estado_codigo="PENDIENTE",
        forma_pago_codigo="EFECTIVO",
        subtotal=1000.0,
        descuento=0.0,
        costo_envio=0.0,
        total=1000.0,
    )
    session.add(pedido)
    session.commit()
    session.refresh(pedido)

    detalle = DetallePedido(
        pedido_id=pedido.id,
        producto_id=producto_final.id,
        nombre_snapshot="Producto Final Test",
        cantidad=1,
        precio_snapshot=1000.0,
        subtotal_snap=1000.0,
    )
    session.add(detalle)

    historial = HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_desde=None,
        estado_hacia="PENDIENTE",
        usuario_id=client_user.id,
        motivo="Pedido creado",
    )
    session.add(historial)
    session.commit()

    pid = pedido.id
    session.expunge(pedido)
    pedido.id = pid
    return pedido


@pytest.fixture(name="pedido_confirmado")
def pedido_confirmado_fixture(session: Session, client_user, producto_final, seed_estados_pedido, seed_formas_pago):
    pedido = Pedido(
        usuario_id=client_user.id,
        estado_codigo="CONFIRMADO",
        forma_pago_codigo="EFECTIVO",
        subtotal=1000.0,
        descuento=0.0,
        costo_envio=0.0,
        total=1000.0,
    )
    session.add(pedido)
    session.commit()
    session.refresh(pedido)

    historial = HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_desde=None,
        estado_hacia="PENDIENTE",
        usuario_id=client_user.id,
        motivo="Pedido creado",
    )
    session.add(historial)
    session.commit()

    pid = pedido.id
    session.expunge(pedido)
    pedido.id = pid
    return pedido