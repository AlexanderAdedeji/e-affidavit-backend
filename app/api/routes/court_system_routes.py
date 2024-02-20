from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    ServerException,
)
from app.database.sessions.session import SessionLocal
from app.repositories.court_system_repo import (
    state_repo,
    court_repo,
    jurisdiction_repo,
)
from app.api.dependencies.authentication import (
    admin_permission_dependency,
    admin_and_head_of_unit_permission_dependency,
)
from app.models.court_system_models import Court, Jurisdiction, State
from app.schemas.court_system import (
    CourtSystemBase,
    CourtSystemInDB,
    CreateCourt,
    CreateJurisdiction,
    FullCourtInDB,
    Jurisdiction,
    Court,
)
from app.schemas.shared_schema import SlimUserInResponse
from app.schemas.user_schema import (
  
    UserInResponse,

)

  
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response

# from commonLib.response.response_schema import create_response


router = APIRouter()


states = ["Abuja"]
jurisdictions = ["Gudu", "Mpape", "Kado", "Kubwa", "Zuba", "Gwagwalada", "Jiwa", "Karu"]
courts = [
    ("Gudu", "Upper Area Court Wuse"),
    ("Gudu", "Grade 1 Area Court Wuse"),
    ("Mpape", "Upper Area Court Mpape"),
    ("Mpape", "Grade 1 Area Court Mpape"),
    ("Kado", "Upper Area Court Kado"),
    ("Kado", "Grade 1 Area Court Kado"),
    ("Kubwa", "Upper Area Court Kubwa"),
    ("Kubwa", "Grade 1 Area Court Kubwa"),
    ("Zuba", "Upper Area Court Zuba"),
    ("Zuba", "Grade 1 Area Court Zuba"),
    ("Gwagwalada", "Upper Area Court Gwagwalada"),
    ("Gwagwalada", "Grade 1 Area Court Gwagwalada"),
    ("Jiwa", "Upper Area Court Jiwa"),
    ("Jiwa", "Grade 1 Area Court Jiwa"),
    ("Karu", "Upper Area Court Karu"),
    ("Karu", "Grade 1 Area Court Karu"),
    # ... continue for other jurisdictions
]


def populate_data(session):
    # Populate states
    for state_name in states:
        state = State(name=state_name)
        session.add(state)

    session.commit()

    # Populate jurisdictions
    for jurisdiction_name in jurisdictions:
        jurisdiction = Jurisdiction(
            id=uuid4().hex,
            name=jurisdiction_name,
            state_id=session.query(State.id).filter(State.name == "Abuja").first()[0],
        )
        session.add(jurisdiction)

    session.commit()

    # Populate courts
    for jurisdiction_name, court_name in courts:
        court = Court(
            id=uuid4().hex,
            name=court_name,
            jurisdiction_id=session.query(Jurisdiction.id)
            .filter(Jurisdiction.name == jurisdiction_name)
            .first()[0],
        )
        session.add(court)

    session.commit()


# def get_courts_under_jurisdiction(session, jurisdiction_name):
#     jurisdiction_id = (
#         session.query(Jurisdiction.id)
#         .filter(Jurisdiction.name == jurisdiction_name)
#         .first()[0]
#     )
#     courts = (
#         session.query(Court.name).filter(Court.jurisdiction_id == jurisdiction_id).all()
#     )
#     return [court[0] for court in courts]


# Running the script
# session = SessionLocal()
# populate_data(session)

# Example usage
# courts_in_gudu = get_courts_under_jurisdiction(session, "Gudu")
# print("Courts in Gudu:", courts_in_gudu)

# Close the session
# session.close()


@router.post(
    "/state",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_permission_dependency)],
)
def create_state(state: CourtSystemBase, db: Session = Depends(get_db)):

    try:
        state_exist = state_repo.get_by_field(
            db=db, field_name="name", field_value=state.name
        )
        if state_exist:
            raise AlreadyExistsException(f"{state.name} already exists")
        new_state = state_repo.create(db, obj_in=state)
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{state.name} created successfully",
            data=CourtSystemInDB(id=str(new_state.id), name=new_state.name),
        )
    except Exception as e:
        logger.error("Something went wrong  while creating the state: {err}", err=e)
        raise ServerException(detail="Something went wrong while creating the state")


@router.get(
    "/states",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CourtSystemInDB]],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_all_states(db: Session = Depends(get_db)):
    """Return a list of all states"""
    try:
        states = state_repo.get_all(db)
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Successful",
            data=[
                CourtSystemInDB(id=str(state.id), name=state.name) for state in states
            ],
        )
    except Exception as e:
        logger.error(e)


@router.get(
    "/state/{id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[CourtSystemInDB],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_state(id: int, db: Session = Depends(get_db)):
    """Get information on a specific state by its ID."""
    try:

        state = state_repo.get(db, id=id)
        if not state:
            raise DoesNotExistException(detail=f"State with id {id} does not exist.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="State Retrieved Successful",
            data=CourtSystemInDB(id=str(state.id), name=state.name),
        )

    except Exception as e:
        logger.error(e)


@router.post(
    "/jusrisdiction",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_permission_dependency)],
)
def create_jurisdiction(
    jurisdiction: CreateJurisdiction, db: Session = Depends(get_db)
):
    try:
        state_exist = state_repo.get(db, id=jurisdiction.state_id)
        if not state_exist:
            raise DoesNotExistException(
                f"State with {jurisdiction.state_id} does not exist"
            )
        jurisdiction_exist = jurisdiction_repo.get_by_name(
            db=db, name=jurisdiction.name
        )

        if jurisdiction_exist:
            raise AlreadyExistsException(f"{jurisdiction.name} already exists")
        new_jurisdiction = jurisdiction_repo.create(
            db, obj_in=dict(**jurisdiction.dict(), id=uuid4())
        )
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{new_jurisdiction.name} created successfully",
            data=CourtSystemInDB(id=new_jurisdiction.id, name=new_jurisdiction.name),
        )

    except Exception as e:
        logger.error(
            "Something went wrong  while creating the jusridiction: {err}", err=e
        )
        raise ServerException(
            detail="Something went wrong  while creating the jusridiction:"
        )


@router.get(
    "/jurisdictions",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CourtSystemInDB]],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_all_jurisdictions(db: Session = Depends(get_db)):
    """Return a list of all jurisdictions"""
    try:
        jurisdictions = jurisdiction_repo.get_all(db)

        return create_response(
            status_code=status.HTTP_200_OK,
            message="Jurisdictions Retrieved Successfully",
            data=[
                CourtSystemInDB(id=jurisdiction.id, name=jurisdiction.name)
                for jurisdiction in jurisdictions
            ],
        )
    except Exception as e:
        logger.error(e)


@router.get(
    "/jurisdiction/{jurisdiction_id}",
    status_code=status.HTTP_200_OK,
    # response_model=GenericResponse[CourtSystemInDB],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_jurisdiction(jurisdiction_id: str, db: Session = Depends(get_db)):
    """Return  jurisdiction"""
    try:
        jurisdiction = jurisdiction_repo.get(db, id=jurisdiction_id)

        if not jurisdiction:
            raise DoesNotExistException(
                detail=f"No Jurisdiction with id {jurisdiction_id} exists"
            )

        return (
            (
                create_response(
                    status_code=status.HTTP_200_OK,
                    message="Jurisdictions Retrieved Successfully",
                    data=Jurisdiction(
                        id=jurisdiction.id,
                        date_created=jurisdiction.CreatedAt,
                        name=jurisdiction.name,
                        state=CourtSystemInDB(
                            id=jurisdiction.state.id, name=jurisdiction.state.name
                        ),
                        courts=[
                            CourtSystemInDB(id=court.id, name=court.name)
                            for court in jurisdiction.courts
                        ],
                        head_of_units=SlimUserInResponse(
                            id=jurisdiction.head_of_unit.id,
                            first_name=jurisdiction.head_of_unit.first_name,
                            last_name=jurisdiction.head_of_unit.last_name,
                            email=jurisdiction.head_of_unit.email,
                        ),
                    ),
                ),
            ),
        )

    except Exception as e:
        logger.error(e)


@router.get(
    "/court",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CourtSystemInDB]],
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
)
def get_all_courts(db: Session = Depends(get_db)):
    """Return a list of all courts"""
    try:
        courts = court_repo.get_all(db)
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Courts Retrieved Successfully",
            data=[CourtSystemInDB(id=court.id, name=court.name) for court in courts],
        )
    except Exception as e:
        logger.error(e)


@router.post(
    "/create_court",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_permission_dependency)],
)
def create_court(court: CreateCourt, db: Session = Depends(get_db)):
    if not jurisdiction_repo.exist(db=db, id=court.jurisdiction_id):
        raise DoesNotExistException(
            detail=f"Jurisdiction with id {court.jurisdiction_id} does not exist."
        )

    new_court = court_repo.create(db, obj_in=dict(**court.dict(), id=uuid4()))
    return dict(
        message=f"{new_court.name} created successfully",
        data=CourtSystemInDB(**new_court.__dict__),
    )


@router.get("/courts/{court_id}")
def get__court(court_id: str, db: Session = Depends(get_db)):
    """Get information about one specific court"""
    court = court_repo.get(db, id=court_id)
    if not court:
        raise DoesNotExistException(detail=f"Court with id {court_id} deos not exists")

    return create_response(
        message=f"{court.name} retrieved successfully",
        status_code=status.HTTP_200_OK,
        data=Court(
            id=court.id,
            date_created=court.CreatedAt,
            name=court.name,
            state=CourtSystemInDB(
                id=court.jurisdiction.state.id, name=court.jurisdiction.state.name
            ),
            Jurisdiction=[
                CourtSystemInDB(id=court.jurisdiction.id, name=court.jurisdiction.name)
            ],
            head_of_unit=SlimUserInResponse(
                id=court.jurisdiction.head_of_unit.id,
                first_name=court.jurisdiction.head_of_unit.first_name,
                last_name=court.jurisdiction.head_of_unit.last_name,
                email=court.jurisdiction.head_of_unit.email,
            ),
        ),
    )


# @router.get("/courts/{court_id}/commissioners")
# def get_commissioners_by_court(db: Session = Depends(get_db)):
#     return {}


# @router.get("/jurisdictions/{jurisdiction_id}/courts")
# def get_courts_by_jurisdiction(db: Session = Depends(get_db)):
#     return {}


# @router.get("/jurisdictions/{jurisdiction_id}/head_of_units")
# def get_head_of_unit_by_jurisdiction(db: Session = Depends(get_db)):
#     return {}


# @router.get("/states/{state_id}/jurisdiction")
# def get_jurisdictions_by_state(db: Session = Depends(get_db)):
#     return {}


@router.get("/populate_court_system")
def populate_court_system(db: Session = Depends(get_db)):
    """Populates the database with data about states and their respective jurisdictions."""
    populate_data(db)
