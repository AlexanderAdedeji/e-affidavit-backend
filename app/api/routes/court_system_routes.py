import json
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import (
    admin_and_head_of_unit_permission_dependency,
    admin_permission_dependency,
    get_currently_authenticated_user,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    ServerException,
    UnauthorizedEndpointException,
)
from app.core.settings.configurations import settings
from app.database.sessions.mongo_client import document_collection
from app.models.court_system_models import Court, Jurisdiction, State
from app.models.user_model import User
from app.repositories.court_system_repo import court_repo, jurisdiction_repo, state_repo
from app.repositories.head_of_unit_repo import head_of_unit_repo
from app.schemas.affidavit_schema import SlimDocumentInResponse, serialize_mongo_document
from app.schemas.court_system_schema import (
    CourtBase,
    CourtInResponse,
    CourtSystemBase,
    CourtSystemInDB,
    CreateCourt,
    CreateJurisdiction,
    FullCourtInDB,
    JurisdictionBase,
)
from app.schemas.shared_schema import SlimUserInResponse
from app.schemas.user_schema import UserInResponse
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response
from commonLib.utils.logger_config import logger

router = APIRouter()
ADMIN_USER_TYPE = settings.ADMIN_USER_TYPE
HEAD_OF_UNIT_USER_TYPE = settings.HEAD_OF_UNIT_USER_TYPE

# ============================================================================
# External Data Loading (for Jurisdictions & Courts)
# ============================================================================
json_path = Path(__file__).resolve().parent / "jurisdiction_data.json"


def load_jurisdiction_data(file_path: Optional[str] = None) -> dict:
    """
    Load jurisdiction data from a JSON file.
    Expected JSON structure:
      {
         "states": ["Abuja"],
         "jurisdictions": ["Gudu", "Mpape", ...],
         "courts": [
             {"jurisdiction": "Gudu", "court_name": "Upper Area Court Wuse"},
             {"jurisdiction": "Gudu", "court_name": "Grade 1 Area Court Wuse"},
             ...
         ]
      }
    """
    # file_path = file_path or settings.JURISDICTION_DATA_FILE

    file_path = json_path
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Jurisdiction data loaded from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading jurisdiction data from {file_path}: {e}")
        raise ServerException(detail="Failed to load jurisdiction data.")

# Cache the loaded data (so we only read the file once)
_jurisdiction_data_cache: Optional[dict] = None

def get_jurisdiction_data() -> dict:
    global _jurisdiction_data_cache
    if _jurisdiction_data_cache is None:
        _jurisdiction_data_cache = load_jurisdiction_data()
    return _jurisdiction_data_cache

# states = ["Abuja"]
# jurisdictions = ["Gudu", "Mpape", "Kado", "Kubwa", "Zuba", "Gwagwalada", "Jiwa", "Karu"]
# courts = [
#     ("Gudu", "Upper Area Court Wuse"),
#     ("Gudu", "Grade 1 Area Court Wuse"),
#     ("Mpape", "Upper Area Court Mpape"),
#     ("Mpape", "Grade 1 Area Court Mpape"),
#     ("Kado", "Upper Area Court Kado"),
#     ("Kado", "Grade 1 Area Court Kado"),
#     ("Kubwa", "Upper Area Court Kubwa"),
#     ("Kubwa", "Grade 1 Area Court Kubwa"),
#     ("Zuba", "Upper Area Court Zuba"),
#     ("Zuba", "Grade 1 Area Court Zuba"),
#     ("Gwagwalada", "Upper Area Court Gwagwalada"),
#     ("Gwagwalada", "Grade 1 Area Court Gwagwalada"),
#     ("Jiwa", "Upper Area Court Jiwa"),
#     ("Jiwa", "Grade 1 Area Court Jiwa"),
#     ("Karu", "Upper Area Court Karu"),
#     ("Karu", "Grade 1 Area Court Karu"),
# ]

# ============================================================================
# Data Population Helper
# ============================================================================

def populate_data(session: Session) -> None:
    """
    Populate the database with states, jurisdictions, and courts.
    Data is loaded from an external JSON file.
    Uses bulk commits to optimize performance.
    """
    data = get_jurisdiction_data()
    states_list = data.get("states", [])
    jurisdictions_list = data.get("jurisdictions", [])
    courts_list = data.get("courts", [])

    # Insert states if they do not exist
    for state_name in states_list:
        if not state_repo.get_by_field(session, field_name="name", field_value=state_name):
            session.add(State(name=state_name))
    session.commit()
    logger.info("States populated.")

    # Insert jurisdictions (for simplicity, assign each jurisdiction to the first state)
    first_state = session.query(State).filter(State.name == states_list[0]).first()
    if not first_state:
        logger.error("First state not found; cannot populate jurisdictions.")
        raise ServerException(detail="State data missing during jurisdiction population.")
    for jurisdiction_name in jurisdictions_list:
        if not jurisdiction_repo.get_by_name(session, name=jurisdiction_name):
            session.add(Jurisdiction(name=jurisdiction_name, state_id=first_state.id))
    session.commit()
    logger.info("Jurisdictions populated.")

    # Insert courts
    for court_entry in courts_list:
        jurisdiction_name = court_entry.get("jurisdiction")
        court_name = court_entry.get("court_name")
        if not jurisdiction_name or not court_name:
            logger.warning(f"Incomplete court entry: {court_entry}")
            continue
        jurisdiction_obj = session.query(Jurisdiction).filter(Jurisdiction.name == jurisdiction_name).first()
        if not jurisdiction_obj:
            logger.warning(f"Jurisdiction {jurisdiction_name} not found for court {court_name}")
            continue
        if not court_repo.get_by_name(session, name=court_name):
            session.add(Court(name=court_name, jurisdiction_id=jurisdiction_obj.id))
    session.commit()
    logger.info("Courts populated.")

# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/state",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_permission_dependency)],
)
def create_state(state: CourtSystemBase, db: Session = Depends(get_db)):
    """
    Create a new state.
    """
    try:
        state_exist = state_repo.get_by_field(db=db, field_name="name", field_value=state.name)
        if state_exist:
            logger.warning(f"State {state.name} already exists.")
            raise AlreadyExistsException(f"{state.name} already exists")
        new_state = state_repo.create(db, obj_in=state)
        logger.info(f"State {new_state.name} created successfully.")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{state.name} created successfully",
            data=CourtSystemInDB(id=str(new_state.id), name=new_state.name),
        )
    except Exception as e:
        logger.error("Error creating state: {err}", err=e, exc_info=True)
        raise ServerException(detail="Something went wrong while creating the state")


@router.get(
    "/states",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CourtSystemInDB]],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_all_states(db: Session = Depends(get_db)):
    """
    Retrieve a list of all states.
    """
    try:
        states_list = state_repo.get_all(db)
        logger.info(f"Retrieved {len(states_list)} states.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Successful",
            data=[CourtSystemInDB(id=str(state.id), name=state.name) for state in states_list],
        )
    except Exception as e:
        logger.error("Error retrieving states: {err}", err=e, exc_info=True)
        raise ServerException()


@router.get(
    "/state/{id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[CourtSystemInDB],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_state(id: int, db: Session = Depends(get_db)):
    """
    Get a specific state by its ID.
    """
    try:
        state_obj = state_repo.get(db, id=id)
        if not state_obj:
            logger.warning(f"State with id {id} does not exist.")
            raise DoesNotExistException(detail=f"State with id {id} does not exist.")
        logger.info(f"State {state_obj.name} retrieved successfully.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="State Retrieved Successfully",
            data=CourtSystemInDB(id=str(state_obj.id), name=state_obj.name),
        )
    except Exception as e:
        logger.error("Error retrieving state: {err}", err=e, exc_info=True)
        raise


@router.post(
    "/jurisdictions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_permission_dependency)],
)
def create_jurisdiction(jurisdiction: CreateJurisdiction, db: Session = Depends(get_db)):
    """
    Create a new jurisdiction.
    """
    try:
        state_obj = state_repo.get(db, id=jurisdiction.state_id)
        if not state_obj:
            logger.warning(f"State with id {jurisdiction.state_id} does not exist.")
            raise DoesNotExistException(detail=f"State with {jurisdiction.state_id} does not exist")
        if jurisdiction_repo.get_by_name(db=db, name=jurisdiction.name):
            logger.warning(f"Jurisdiction {jurisdiction.name} already exists.")
            raise AlreadyExistsException(f"{jurisdiction.name} already exists")
        new_jurisdiction = jurisdiction_repo.create(db, obj_in=jurisdiction.dict())
        logger.info(f"Jurisdiction {new_jurisdiction.name} created successfully.")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{new_jurisdiction.name} created successfully",
            data=CourtSystemInDB(id=new_jurisdiction.id, name=new_jurisdiction.name),
        )
    except Exception as e:
        logger.error("Error creating jurisdiction: {err}", err=e, exc_info=True)
        raise ServerException()


@router.get(
    "/jurisdictions",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CourtSystemInDB]],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_all_jurisdictions(db: Session = Depends(get_db)):
    """
    Retrieve a list of all jurisdictions.
    """
    try:
        jurisdictions_list = jurisdiction_repo.get_all(db)
        logger.info(f"Retrieved {len(jurisdictions_list)} jurisdictions.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Jurisdictions Retrieved Successfully",
            data=[CourtSystemInDB(id=jurisdiction.id, name=jurisdiction.name) for jurisdiction in jurisdictions_list],
        )
    except Exception as e:
        logger.error("Error retrieving jurisdictions: {err}", err=e, exc_info=True)
        raise ServerException()


@router.get(
    "/jurisdiction/{jurisdiction_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[JurisdictionBase],
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
)
def get_jurisdiction_endpoint(
    jurisdiction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve a jurisdiction by its ID.
    For head of unit users, verifies if the jurisdiction belongs to them.
    """

    
    if current_user.user_type.name == HEAD_OF_UNIT_USER_TYPE and current_user.head_of_unit.jurisdiction_id != jurisdiction_id:
        logger.warning("Unauthorized access attempt to jurisdiction.")
        raise UnauthorizedEndpointException(detail="This court is not in your jurisdiction")
    try:
        jurisdiction_obj = jurisdiction_repo.get(db, id=jurisdiction_id)
        if not jurisdiction_obj:
            logger.warning(f"Jurisdiction with id {jurisdiction_id} does not exist.")
            raise DoesNotExistException(detail=f"No Jurisdiction with id {jurisdiction_id} exists")
        logger.info(f"Jurisdiction {jurisdiction_obj.name} retrieved successfully.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Jurisdiction Retrieved Successfully",
            data=JurisdictionBase(
                id=jurisdiction_obj.id,
                date_created=jurisdiction_obj.CreatedAt,
                name=jurisdiction_obj.name,
                state=CourtSystemInDB(id=jurisdiction_obj.state.id, name=jurisdiction_obj.state.name),
                courts=[CourtSystemInDB(id=court.id, name=court.name) for court in jurisdiction_obj.courts],
                head_of_unit=SlimUserInResponse(
                    id=jurisdiction_obj.head_of_unit.id,
                    first_name=jurisdiction_obj.head_of_unit.user.first_name,
                    last_name=jurisdiction_obj.head_of_unit.user.last_name,
                    email=jurisdiction_obj.head_of_unit.user.email,
                ),
            ),
        )
    except Exception as e:
        logger.error("Error retrieving jurisdiction: {err}", err=e, exc_info=True)
        raise


@router.get(
    "/courts",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CourtBase]],
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
)
async def get_all_courts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve a list of all courts.
    For head of unit users, returns only courts in their jurisdiction.
    """
    try:
        if current_user.user_type.name == settings.HEAD_OF_UNIT_USER_TYPE:
            courts_list = head_of_unit_repo.get_courts_under_jurisdiction(
                db=db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
            )
        else:
            courts_list = court_repo.get_all(db)
        logger.info(f"Retrieved {len(courts_list)} courts.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Courts Retrieved Successfully",
            data=[CourtBase(
                id=court.id,
                date_created=court.CreatedAt,
                name=court.name,
                state=CourtSystemInDB(id=court.jurisdiction.state.id, name=court.jurisdiction.state.name),
                Jurisdiction=CourtSystemInDB(id=court.jurisdiction.id, name=court.jurisdiction.name),
            ) for court in courts_list],
        )
    except Exception as e:
        logger.error("Error retrieving courts: {err}", err=e, exc_info=True)
        raise


@router.post(
    "/court",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[CourtSystemInDB]
)
def create_court(court: CreateCourt, db: Session = Depends(get_db)):
    """
    Create a new court.
    """
    if not jurisdiction_repo.exist(db=db, id=court.jurisdiction_id):
        logger.warning(f"Jurisdiction with id {court.jurisdiction_id} does not exist.")
        raise DoesNotExistException(detail=f"Jurisdiction with id {court.jurisdiction_id} does not exist.")
    if court_repo.get_by_name(db=db, name=court.name):
        logger.warning(f"Court {court.name} already exists.")
        raise AlreadyExistsException(detail=f"Court with name {court.name} already exist.")
    try:
        new_court = court_repo.create(db, obj_in=court.dict())
        logger.info(f"Court {new_court.name} created successfully.")
        return create_response(
            message=f"{new_court.name} created successfully",
            data=CourtSystemInDB(**new_court.__dict__),
        )
    except Exception as e:
        logger.error("Error creating court: {err}", err=e, exc_info=True)
        raise ServerException()


@router.get(
    "/courts/{court_id}",
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
)
def get_court(
    court_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve a court by its ID.
    For head of unit users, verifies that the court belongs to their jurisdiction.
    """
    try:
        court_obj = court_repo.get(db, id=court_id)
        if not court_obj:
            logger.warning(f"Court with id {court_id} does not exist.")
            raise DoesNotExistException(detail=f"Court with id {court_id} does not exist")
        if current_user.user_type.name == HEAD_OF_UNIT_USER_TYPE and current_user.head_of_unit.jurisdiction_id != court_obj.jurisdiction_id:
            logger.warning("Unauthorized access attempt for court retrieval.")
            raise UnauthorizedEndpointException(detail="This court is not in your jurisdiction")
        logger.info(f"Court {court_obj.name} retrieved successfully.")
        return create_response(
            message=f"{court_obj.name} retrieved successfully",
            status_code=status.HTTP_200_OK,
            data=CourtBase(
                id=court_obj.id,
                date_created=court_obj.CreatedAt,
                name=court_obj.name,
                state=CourtSystemInDB(id=court_obj.jurisdiction.state.id, name=court_obj.jurisdiction.state.name),
                Jurisdiction=CourtSystemInDB(id=court_obj.jurisdiction.id, name=court_obj.jurisdiction.name),
                head_of_unit=SlimUserInResponse(
                    id=court_obj.jurisdiction.head_of_unit.id,
                    first_name=court_obj.jurisdiction.head_of_unit.user.first_name,
                    last_name=court_obj.jurisdiction.head_of_unit.user.last_name,
                    email=court_obj.jurisdiction.head_of_unit.user.email,
                ),
                commissioners=[
                    SlimUserInResponse(
                        id=commissioner.user.id,
                        first_name=commissioner.user.first_name,
                        last_name=commissioner.user.last_name,
                        email=commissioner.user.email,
                    )
                    for commissioner in court_obj.commissioner_profiles
                ],
            ),
        )
    except Exception as e:
        logger.error("Error retrieving court: {err}", err=e, exc_info=True)
        raise


@router.get(
    "/jurisdictions/{jurisdiction_id}/courts",
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
)
def get_courts_by_jurisdiction(
    jurisdiction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve all courts in a specific jurisdiction.
    For head of unit users, verifies that the jurisdiction is within their domain.
    """
    if current_user.user_type.name == HEAD_OF_UNIT_USER_TYPE and current_user.head_of_unit.jurisdiction_id != jurisdiction_id:
        logger.warning("Unauthorized access attempt: court not in user's jurisdiction.")
        raise UnauthorizedEndpointException(detail="This court is not in your jurisdiction")
    try:
        courts_list = db.query(Court).filter(Court.jurisdiction_id == jurisdiction_id).all()
        logger.info(f"Retrieved {len(courts_list)} courts for jurisdiction {jurisdiction_id}.")
        return create_response(
            message="Courts retrieved successfully",
            status_code=status.HTTP_200_OK,
            data=[CourtBase(
                id=court.id,
                date_created=court.CreatedAt,
                name=court.name,
                state=CourtSystemInDB(id=court.jurisdiction.state.id, name=court.jurisdiction.state.name),
                Jurisdiction=[CourtSystemInDB(id=court.jurisdiction.id, name=court.jurisdiction.name)],
                head_of_unit=SlimUserInResponse(
                    id=court.jurisdiction.head_of_unit.id,
                    first_name=court.jurisdiction.head_of_unit.first_name,
                    last_name=court.jurisdiction.head_of_unit.last_name,
                    email=court.jurisdiction.head_of_unit.email,
                ),
            ) for court in courts_list],
        )
    except Exception as e:
        logger.error("Error retrieving courts by jurisdiction: {err}", err=e, exc_info=True)
        raise
