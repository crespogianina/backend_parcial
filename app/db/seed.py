from sqlmodel import Session, select

from app.core.database import engine, create_db_and_tables
from app.core.security import hash_password
from app.modules.usuarios.model import Rol, Usuario, UsuarioRol


# ---------------------------------------------------------------------------
# Roles según ERD (PK semántica)
# ---------------------------------------------------------------------------

ROLES = [
    {"codigo": "ADMIN",   "nombre": "Administrador", "descripcion": "Acceso total sin restricciones"},
    {"codigo": "STOCK",   "nombre": "Stock",          "descripcion": "Actualiza stock y disponibilidad"},
    {"codigo": "PEDIDOS", "nombre": "Pedidos",         "descripcion": "Avanza estados de pedidos"},
    {"codigo": "CLIENT",  "nombre": "Cliente",         "descripcion": "Opera solo sus propios datos"},
]

# ---------------------------------------------------------------------------
# Usuarios iniciales
# ---------------------------------------------------------------------------

USUARIOS = [
    {
        "username":  "admin",
        "nombre":    "Administrador",
        "apellido":  "Sistema",
        "email":     "admin@example.com",
        "password":  "Admin1234!",
        "roles":     ["ADMIN"],
    },
    {
        "username":  "juan",
        "nombre":    "Juan",
        "apellido":  "Pérez",
        "email":     "juan@example.com",
        "password":  "Juan1234!",
        "roles":     ["CLIENT"],
    },
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
        existing = session.exec(select(Usuario).where(Usuario.username == data["username"])).first()

        if existing:
            print(f"  [=] Ya existe: {data['username']}")
            usuario = existing
        else:
            usuario = Usuario(
                username=data["username"],
                nombre=data["nombre"],
                apellido=data["apellido"],
                email=data["email"],
                password_hash=hash_password(data["password"]),
            )
            session.add(usuario)
            session.commit()
            session.refresh(usuario)
            print(f"  [+] Creado:    {data['username']} / {data['password']}")

        # Asignar roles si no los tiene ya
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


def run() -> None:
    print("=== Seed — Food Store ===")
    create_db_and_tables()

    with Session(engine) as session:
        seed_roles(session)
        seed_usuarios(session)

    print("\nUsuarios disponibles:")
    print("  admin / Admin1234!  → ADMIN")
    print("  juan  / Juan1234!   → CLIENT")
    print()


if __name__ == "__main__":
    run()