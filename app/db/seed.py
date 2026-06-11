from sqlmodel import Session, select

from app.core.database import engine, create_db_and_tables
from app.core.security import hash_password
from app.modules.usuarios.model import Rol, Usuario, UsuarioRol
from app.modules.pedido.models import EstadoPedido, FormaPago
from app.modules.producto.models import UnidadMedida

ROLES = [
    {"codigo": "ADMIN",   "nombre": "Administrador", "descripcion": "Acceso total sin restricciones"},
    {"codigo": "STOCK",   "nombre": "Stock",          "descripcion": "Actualiza stock y disponibilidad"},
    {"codigo": "PEDIDOS", "nombre": "Pedidos",        "descripcion": "Avanza estados de pedidos"},
    {"codigo": "CLIENT",  "nombre": "Cliente",        "descripcion": "Opera solo sus propios datos"},
]

USUARIOS = [
    {
        "nombre":   "Administrador",
        "apellido": "Sistema",
        "email":    "admin@foodstore.com",
        "password": "Admin1234!",
        "roles":    ["ADMIN"],
    },
    {
        "nombre":   "Juan",
        "apellido": "Pérez",
        "email":    "juan@example.com",
        "password": "Juan1234!",
        "roles":    ["CLIENT"],
    },
]

ESTADOS_PEDIDO = [
    {"codigo": "PENDIENTE",      "descripcion": "Pedido creado, esperando pago",    "orden": 1, "es_terminal": False},
    {"codigo": "CONFIRMADO",     "descripcion": "Pago aprobado, stock decrementado","orden": 2, "es_terminal": False},
    {"codigo": "EN_PREPARACION", "descripcion": "En cocina/preparación",            "orden": 3, "es_terminal": False},
    {"codigo": "EN_CAMINO",      "descripcion": "En camino al cliente",             "orden": 4, "es_terminal": False},
    {"codigo": "ENTREGADO",      "descripcion": "Entregado correctamente",          "orden": 5, "es_terminal": True},
    {"codigo": "CANCELADO",      "descripcion": "Cancelado",                        "orden": 6, "es_terminal": True},
]

FORMAS_PAGO = [
    {"codigo": "MP",       "descripcion": "Mercado Pago", "habilitado": True},
    {"codigo": "EFECTIVO", "descripcion": "Efectivo",     "habilitado": True},
    {"codigo": "TRANSFERENCIA", "descripcion": "Transferencia",     "habilitado": True},
]

UNIDADES_MEDIDA = [
    {"nombre": "Kilogramo", "simbolo": "kg",  "tipo": "peso"},
    {"nombre": "Gramo",     "simbolo": "g",   "tipo": "peso"},
    {"nombre": "Litro",     "simbolo": "L",   "tipo": "volumen"},
    {"nombre": "Mililitro", "simbolo": "ml",  "tipo": "volumen"},
    {"nombre": "Unidad",    "simbolo": "ud",  "tipo": "contable"},
    {"nombre": "Porción",   "simbolo": "porciones", "tipo": "contable"},
]

def seed_roles(session: Session) -> None:
    print("\n── Roles ──")
    for data in ROLES:
        existing = session.exec(select(Rol).where(Rol.codigo == data["codigo"])).first()
        if existing:
            print(f"  [=] Ya existe: {data['codigo']}")
        else:
            session.add(Rol(**data))
            print(f"  [+] Creado:    {data['codigo']}")
    session.commit()


def seed_usuarios(session: Session) -> None:
    print("\n── Usuarios ──")
    for data in USUARIOS:
        existing = session.exec(
            select(Usuario).where(Usuario.email == data["email"])
        ).first()

        if existing:
            print(f"  [=] Ya existe: {data['email']}")
            usuario = existing
        else:
            usuario = Usuario(
                nombre=data["nombre"],
                apellido=data["apellido"],
                email=data["email"],
                password_hash=hash_password(data["password"]),
            )
            session.add(usuario)
            session.commit()
            session.refresh(usuario)
            print(f"  [+] Creado:    {data['email']} / {data['password']}")

        for rol_codigo in data["roles"]:
            existing_rol = session.exec(
                select(UsuarioRol).where(
                    UsuarioRol.usuario_id == usuario.id,
                    UsuarioRol.rol_codigo == rol_codigo,
                )
            ).first()
            if not existing_rol:
                session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo=rol_codigo))
                print(f"      → Rol asignado: {rol_codigo}")
            else:
                print(f"      → Rol ya asignado: {rol_codigo}")

    session.commit()


def seed_estados_pedido(session: Session) -> None:
    print("\n── Estados de Pedido ──")
    for data in ESTADOS_PEDIDO:
        existing = session.exec(
            select(EstadoPedido).where(EstadoPedido.codigo == data["codigo"])
        ).first()
        if existing:
            print(f"  [=] Ya existe: {data['codigo']}")
        else:
            session.add(EstadoPedido(**data))
            print(f"  [+] Creado:    {data['codigo']}")
    session.commit()


def seed_formas_pago(session: Session) -> None:
    print("\n── Formas de Pago ──")
    for data in FORMAS_PAGO:
        existing = session.exec(
            select(FormaPago).where(FormaPago.codigo == data["codigo"])
        ).first()
        if existing:
            print(f"  [=] Ya existe: {data['codigo']}")
        else:
            session.add(FormaPago(**data))
            print(f"  [+] Creado:    {data['codigo']}")
    session.commit()


def seed_unidades_medida(session: Session) -> None:
    print("\n── Unidades de Medida ──")
    for data in UNIDADES_MEDIDA:
        existing = session.exec(
            select(UnidadMedida).where(UnidadMedida.simbolo == data["simbolo"])
        ).first()
        if existing:
            print(f"  [=] Ya existe: {data['simbolo']}")
        else:
            session.add(UnidadMedida(**data))
            print(f"  [+] Creado:    {data['simbolo']}")
    session.commit()


def run() -> None:
    print("=== Seed — Food Store ===")
    create_db_and_tables()

    with Session(engine) as session:
        seed_roles(session)
        seed_usuarios(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)
        seed_unidades_medida(session)

    print("\n── Usuarios disponibles ──")
    print("  admin@foodstore.com / Admin1234!  → ADMIN")
    print("  juan@example.com   / Juan1234!   → CLIENT")
    print()


if __name__ == "__main__":
    run()