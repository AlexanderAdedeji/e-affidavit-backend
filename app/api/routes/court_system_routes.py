from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import DoesNotExistException
from app.database.sessions.session import SessionLocal
from app.repositories.court_system_repo import (
    state_repo,
    court_repo,
    jurisdiction_repo,
)

from app.models.court_system_models import Court, Jurisdiction, State
from app.schemas.court_system import (
    CourtSystemInDB,
    CreateCourt,
    FullCourtInDB,
)
from commonLib.response.response_schema import create_response


router = APIRouter()


@router.get("/court_system")
def court_system_base():
    # populate_data(session)
    return {"msg": "court_system"}


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
            name=jurisdiction_name,
            state_id=session.query(State.id).filter(State.name == "Abuja").first()[0],
        )
        session.add(jurisdiction)

    session.commit()

    # Populate courts
    for jurisdiction_name, court_name in courts:
        court = Court(
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


@router.get("/populate_court_system")
def populate_court_system(db: Session = Depends(get_db)):
    """Populates the database with data about states and their respective jurisdictions."""
    populate_data(db)


@router.get("/states")
def get_all_states(db: Session = Depends(get_db)):
    """Return a list of all states"""
    try:
        states = state_repo.get_all(db)
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Successful",
            data=[CourtSystemInDB(id=state.id, name=state.name) for state in states],
        )
    except Exception as e:
        logger.error(e)


@router.get("/state/{id}")
def get_state(id: int, db: Session = Depends(get_db)):
    """Get information on a specific state by its ID."""
    state = state_repo.get(db, id=id)
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Successful",
        data=CourtSystemInDB(id=state.id, name=state.name),
    )


@router.get("/jurisdictions")
def get_all_jurisdictions(db: Session = Depends(get_db)):
    """Return a list of all jurisdictions"""
    try:
        jurisdictions = jurisdiction_repo.get_all(db)
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Successful",
            data=[
                CourtSystemInDB(id=jurisdiction.id, name=jurisdiction.name)
                for jurisdiction in jurisdictions
            ],
        )
    except Exception as e:
        logger.error(e)


@router.get("/courts")
def get_all_courts(db: Session = Depends(get_db)):
    """Return a list of all courts"""
    try:
        courts = court_repo.get_all(db)
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Successful",
            data=[CourtSystemInDB(id=court.id, name=court.name) for court in courts],
        )
    except Exception as e:
        logger.error(e)


@router.post("/create_court", status_code=status.HTTP_201_CREATED)
def create_court(court: CreateCourt, db: Session = Depends(get_db)):
    if not state_repo.exist(db=db, id=court.state_id):
        raise DoesNotExistException(
            detail=f"State with id {court.state_id} does not exist."
        )
    if not jurisdiction_repo.exist(db, id=court.jurisdiction_id):
        raise DoesNotExistException(
            detail=f"Jurisdiction with id {court.jurisdiction_id} does not exist."
        )

    new_court = court_repo.create(db, obj_in=court)
    return create_response(
        message=f"{new_court.name} created successfully",
        data=FullCourtInDB(**new_court.__dict__),
    )
