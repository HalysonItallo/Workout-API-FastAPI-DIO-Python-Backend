from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, status
from fastapi_pagination import Page, paginate
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from workout_api.atleta.models import AtletaModel
from workout_api.atleta.schemas import AtletaGetAllDetails, AtletaIn, AtletaOut, AtletaUpdate
from workout_api.categorias.models import CategoriaModel
from workout_api.centro_treinamento.models import CentroTreinamentoModel
from workout_api.contrib.dependencies import DatabaseDependency

router = APIRouter()


@router.post(
    path="/",
    summary="Criar um novo atleta",
    status_code=status.HTTP_201_CREATED,
    response_model=AtletaOut,
)
async def post(db_session: DatabaseDependency, atleta_in: AtletaIn = Body(...)):

    categoria_name = atleta_in.categoria.nome
    centro_treinamento_name = atleta_in.centro_treinamento.nome

    categoria = (
        (
            await db_session.execute(
                select(CategoriaModel).filter_by(nome=categoria_name),
            )
        )
        .scalars()
        .first()
    )

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A Categoria {categoria_name} não encontrada.",
        )

    centro_treinamento = (
        (await db_session.execute(select(CentroTreinamentoModel).filter_by(nome=centro_treinamento_name)))
        .scalars()
        .first()
    )

    if not centro_treinamento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O centro de treinamento {categoria_name} não foi encontrado.",
        )

    atleta_out = AtletaOut(id=uuid4(), criado_em=datetime.utcnow(), **atleta_in.model_dump())

    try:
        atleta_model = AtletaModel(**atleta_out.model_dump(exclude={"categoria", "centro_treinamento"}))
        atleta_model.categoria_id = categoria.pk_id
        atleta_model.centro_treinamento_id = centro_treinamento.pk_id

        db_session.add(atleta_model)
        await db_session.commit()

        return atleta_out
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail=f"Já existe um atleta cadastrado com o cpf: {atleta_out.cpf}",
        )


@router.get(
    path="/",
    summary="Consultar todas os atletas",
    status_code=status.HTTP_200_OK,
    response_model=Page[AtletaGetAllDetails],
)
async def get_all(db_session: DatabaseDependency) -> list[AtletaGetAllDetails]:

    atletas = (await db_session.execute(select(AtletaModel))).scalars().all()
    return paginate([AtletaGetAllDetails.model_validate(atleta) for atleta in atletas])


@router.get(
    path="/{id}",
    summary="Consultar um atleta pelo id",
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut,
)
async def get_by_id(id: UUID4, db_session: DatabaseDependency) -> AtletaOut:

    atleta = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Atleta não encontrada com o id: {id}",
        )

    return atleta


@router.get(
    path="/por-nome/{nome}",
    summary="Consultar um atleta pelo nome",
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut,
)
async def get_by_name(nome: str, db_session: DatabaseDependency) -> AtletaOut:

    atleta = (await db_session.execute(select(AtletaModel).filter_by(nome=nome))).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Atleta não encontrada com o nome: {nome}",
        )

    return atleta


@router.get(
    path="/por-cpf/{cpf}",
    summary="Consultar um atleta pelo nome",
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut,
)
async def get_by_cpf(cpf: str, db_session: DatabaseDependency) -> AtletaOut:

    atleta = (await db_session.execute(select(AtletaModel).filter_by(cpf=cpf))).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Atleta não encontrada com o cpf: {cpf}",
        )

    return atleta


@router.patch(
    path="/{id}",
    summary="Editar um atleta pelo id",
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut,
)
async def partial_update(
    id: UUID4,
    db_session: DatabaseDependency,
    atleta_up: AtletaUpdate = Body(...),
) -> AtletaOut:

    atleta = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Atleta não encontrada com o id: {id}",
        )

    atleta_update = atleta_up.model_dump(exclude_unset=True)

    for key, value in atleta_update.items():
        setattr(atleta, key, value)

    await db_session.commit()
    await db_session.refresh(atleta)

    return atleta


@router.delete(
    path="/{id}",
    summary="Deletar um atleta pelo id",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete(id: UUID4, db_session: DatabaseDependency) -> None:

    atleta = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Atleta não encontrada com o id: {id}",
        )

    await db_session.delete(atleta)
    await db_session.commit()
