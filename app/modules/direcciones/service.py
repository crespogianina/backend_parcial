from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.direcciones.schemas import (
    DireccionCreate,
    DireccionList,
    DireccionPublic,
    DireccionUpdate,
)
from app.modules.direcciones.unit_of_work import DireccionUnitOfWork
from app.modules.direcciones.model import DireccionEntrega
from app.modules.usuarios.schemas import UserPublic


class DireccionService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_public(self, direccion: DireccionEntrega) -> DireccionPublic:
        return DireccionPublic(
            **direccion.model_dump(),
            activo=direccion.deleted_at is None,
        )

    def _get_owned_or_404(
        self,
        uow: DireccionUnitOfWork,
        direccion_id: int,
        usuario_id: int,
    ) -> DireccionEntrega:
        direccion = uow.direcciones.get_by_id_for_user(direccion_id, usuario_id)

        if not direccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dirección con id={direccion_id} no encontrada",
            )

        return direccion

    def create(self, usuario: UserPublic, data: DireccionCreate) -> DireccionPublic:
        with DireccionUnitOfWork(self._session) as uow:
            activas = uow.direcciones.count_active_for_user(usuario.id)
            es_principal = data.es_principal if data.es_principal is not None else activas == 0

            if es_principal:
                uow.direcciones.clear_principal_for_user(usuario.id)

            direccion = DireccionEntrega(
                usuario_id=usuario.id,
                alias=data.alias,
                linea1=data.linea1,
                linea2=data.linea2,
                ciudad=data.ciudad,
                provincia=data.provincia,
                codigo_postal=data.codigo_postal,
                latitud=data.latitud,
                longitud=data.longitud,
                es_principal=es_principal,
            )
            uow.direcciones.add(direccion)
            result = self._to_public(direccion)

        return result

    def list_all(
        self,
        usuario: UserPublic,
        offset: int = 0,
        limit: int = 50,
    ) -> DireccionList:
        with DireccionUnitOfWork(self._session) as uow:
            direcciones = uow.direcciones.get_all_for_user(usuario.id, offset=offset, limit=limit)
            total = uow.direcciones.count_active_for_user(usuario.id)

            return DireccionList(
                data=[self._to_public(d) for d in direcciones],
                total=total,
            )

    def get_by_id(self, usuario: UserPublic, direccion_id: int) -> DireccionPublic:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_owned_or_404(uow, direccion_id, usuario.id)
            return self._to_public(direccion)

    def update(
        self,
        usuario: UserPublic,
        direccion_id: int,
        data: DireccionUpdate,
    ) -> DireccionPublic:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_owned_or_404(uow, direccion_id, usuario.id)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(direccion, field, value)

            direccion.updated_at = datetime.utcnow()
            uow.direcciones.add(direccion)
            result = self._to_public(direccion)

        return result

    def soft_delete(self, usuario: UserPublic, direccion_id: int) -> None:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_owned_or_404(uow, direccion_id, usuario.id)
            era_principal = direccion.es_principal

            direccion.deleted_at = datetime.utcnow()
            direccion.es_principal = False
            direccion.updated_at = datetime.utcnow()
            uow.direcciones.add(direccion)

            if era_principal:
                otra = uow.direcciones.get_first_active_for_user(usuario.id)
                if otra:
                    otra.es_principal = True
                    otra.updated_at = datetime.utcnow()
                    uow.direcciones.add(otra)

    def set_principal(self, usuario: UserPublic, direccion_id: int) -> DireccionPublic:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_owned_or_404(uow, direccion_id, usuario.id)

            uow.direcciones.clear_principal_for_user(usuario.id)
            direccion.es_principal = True
            direccion.updated_at = datetime.utcnow()
            uow.direcciones.add(direccion)
            result = self._to_public(direccion)

        return result
