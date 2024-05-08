import datetime
from typing import List
import uuid
from app.schemas.report_schema import (
    CommissionerReport,
    CommissionersReport,
    DocumentReports,
)
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.authentication import (
    get_currently_authenticated_user,
    head_of_unit_permission_dependency,
    admin_permission_dependency,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    UnauthorizedEndpointException,
)
from app.models.user_model import User
from app.repositories.user_invite_repo import user_invite_repo
from app.database.sessions.mongo_client import document_collection
from app.repositories.user_repo import user_repo
from app.repositories.head_of_unit_repo import head_of_unit_repo
from app.repositories.user_type_repo import user_type_repo
from app.core.settings.configurations import settings
from app.schemas.affidavit_schema import (
    SlimDocumentInResponse,
    serialize_mongo_document,
)
from app.schemas.court_system_schema import CourtBase, CourtSystemInDB
from app.schemas.shared_schema import DateRange, SlimUserInResponse
from app.schemas.stats_schema import AdminDashboardStat, HeadOfUnitDashboardStat
from app.schemas.user_schema import (
    CommissionerCreate,
    CommissionerInResponse,
    CommissionerProfileBase,
    FullCommissionerInResponse,
    FullHeadOfUniteInResponse,
    HeadOfUnitBase,
    HeadOfUnitCreate,
    HeadOfUnitInResponse,
    OperationsCreateForm,
    UserCreate,
    UserInResponse,
)
from app.repositories.commissioner_profile_repo import comm_profile_repo
from app.schemas.user_type_schema import UserTypeInDB
from app.repositories.court_system_repo import court_repo
from commonLib.response.response_schema import create_response, GenericResponse


router = APIRouter()


@router.get(
    "/get_dashboard_stats",
    # dependencies=[Depends(admin_permission_dependency)]
)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    This endpoint returns statistics about users, invitations, affidavits, commissioners, courts, and revenue in the system.
    """
    # Get courts under jurisdiction
    total_courts = head_of_unit_repo.get_courts_under_jurisdiction(
        db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
    )

    total_affidavits = []
    total_revenue = 0
    total_commissioners = head_of_unit_repo.get_commissioners_under_jurisdiction(
        db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
    )

    # Loop through each court and get affidavits and revenue
    for court in total_courts:
        pipeline = [
            {
                "$match": {
                    "court_id": court.id,
                    "$or": [{"status": "PAID"}, {"is_attested": True}],
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_amount": {"$sum": "$price"},
                    "documents": {"$push": "$$ROOT"},
                }
            },
        ]
        results = await document_collection.aggregate(pipeline).to_list(length=1)
        if results and results[0]:
            total_revenue += results[0]["total_amount"]
            documents = [
                SlimDocumentInResponse(
                    id=str(document["_id"]),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=document.get("attest", None),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in results[0].get("documents", [])
            ]
            total_affidavits.append(documents)

    # Create and return response
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Dashboard Stats fetched successfully.",
        data=HeadOfUnitDashboardStat(
            total_courts=len(total_courts),
            total_commissioners=len(total_commissioners),
            total_affidavits=sum(len(docs) for docs in total_affidavits),
            total_revenue=total_revenue,
        ),
    )


@router.get(
    "/courts",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(head_of_unit_permission_dependency)],
)
async def get_all_courts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """Return a list of all courts in the jurisdiction of the head of unit."""
    try:
        courts_data = []

        courts = head_of_unit_repo.get_courts_under_jurisdiction(
            db=db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
        )

        for court in courts:
            db_documents = await document_collection.find(
                {"court_id": court.id}
            ).to_list(length=1000)
            documents = [
                SlimDocumentInResponse(
                    id=str(document["_id"]),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=(
                        document.get("attest") if document.get("attest", "") else None
                    ),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in db_documents
            ]

            courts_data.append(
                {
                    "id": court.id,
                    "date_created": court.CreatedAt,
                    "name": court.name,
                    "Jurisdiction": CourtSystemInDB(
                        id=court.jurisdiction.id, name=court.jurisdiction.name
                    ),
                    "commissioners": [
                        SlimUserInResponse(
                            id=commissioner.user.id,
                            first_name=commissioner.user.first_name,
                            last_name=commissioner.user.last_name,
                            email=commissioner.user.email,
                        )
                        for commissioner in court.commissioner_profile
                    ],
                    "documents": documents,  # Now directly using the list of documents
                }
            )

        return create_response(
            status_code=status.HTTP_200_OK,
            message="Courts Retrieved Successfully",
            data=courts_data,
        )

    except Exception as e:
        # Consider adding logging or more specific error handling here
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")


@router.get(
    "/get_court/{court_id}",
    dependencies=[Depends(head_of_unit_permission_dependency)],
)
def get__court(
    court_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """Get information about one specific court, You can access this rout as an Admin or Head of Unit,
    as an admin you can view any court, if you are a head of unit you can only view court in your jurisdictions
    """

    court = court_repo.get(db, id=court_id)

    if not court:
        raise DoesNotExistException(detail=f"Court with id {court_id} deos not exists")
    if current_user.head_of_unit.jurisdiction_id != court.jurisdiction_id:
        raise UnauthorizedEndpointException(
            detail="This court is not in your jurisdiction"
        )

    return create_response(
        message=f"{court.name} retrieved successfully",
        status_code=status.HTTP_200_OK,
        data=CourtBase(
            id=court.id,
            date_created=court.CreatedAt,
            name=court.name,
            state=CourtSystemInDB(
                id=court.jurisdiction.state.id, name=court.jurisdiction.state.name
            ),
            Jurisdiction=CourtSystemInDB(
                id=court.jurisdiction.id, name=court.jurisdiction.name
            ),
            head_of_unit=SlimUserInResponse(
                id=court.jurisdiction.head_of_unit.id,
                first_name=court.jurisdiction.head_of_unit.user.first_name,
                last_name=court.jurisdiction.head_of_unit.user.last_name,
                email=court.jurisdiction.head_of_unit.user.email,
            ),
            commissioners=[
                SlimUserInResponse(
                    id=commissioner.user.id,
                    first_name=commissioner.user.first_name,
                    last_name=commissioner.user.last_name,
                    email=commissioner.user.email,
                )
                for commissioner in court.commissioner_profile
            ],
        ),
    )


@router.get(
    "/commissioners/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CommissionerInResponse]],
    dependencies=[Depends(head_of_unit_permission_dependency)],
)
async def get_commissioners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    results = []

    commissioner_profiles = head_of_unit_repo.get_commissioners_under_jurisdiction(
        db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
    )
    commissioners = [commissioner.user for commissioner in commissioner_profiles]
    for commissioner in commissioners:
        attested_documents = await document_collection.find(
            {"commissioner_id": commissioner.id}
        ).to_list(length=1000)
        documents_serialized = [
            SlimDocumentInResponse(
                id=str(document["_id"]),
                name=document.get("name", ""),
                price=document.get("price", 0),
                attestation_date=(
                    document.get("attest") if document.get("attest", "") else None
                ),
                created_at=document.get("created_at", ""),
                status=document.get("status", ""),
            )
            for document in attested_documents
        ]
        fullcommissioner = CommissionerInResponse(
            id=commissioner.id,
            first_name=commissioner.first_name,
            user_type=UserTypeInDB(
                id=commissioner.user_type.id, name=commissioner.user_type.name
            ),
            verify_token="some_verify_token",
            last_name=commissioner.last_name,
            email=commissioner.email,
            court=CourtSystemInDB(
                id=commissioner.commissioner_profile.court.id,
                name=commissioner.commissioner_profile.court.name,
            ),
            is_active=commissioner.is_active,
            attested_documents=documents_serialized,
            date_created=commissioner.CreatedAt,
        )
        results.append(fullcommissioner)
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Commissioners retireved successfully",
        data=results,
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponse[UserInResponse],
)
async def create_head_of_unit(
    head_of_unit_in: OperationsCreateForm,
    db: Session = Depends(get_db),
):
    # Validate the invitation
    db_invite = user_invite_repo.get(db=db, id=head_of_unit_in.invite_id)
    if not db_invite:
        raise DoesNotExistException(detail="Invitation does not exist or is invalid.")
    if not db_invite.is_accepted:
        raise HTTPException(
            status_code=403,
            detail="Cannot use un-accepted invites for creating new accounts.",
        )

    # Ensure the invite is for a Head of unit
    if db_invite.user_type.name != settings.HEAD_OF_UNIT_USER_TYPE:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this endpoint.",
        )

    # Check if the email is already used
    if user_repo.get_by_email(db=db, email=db_invite.email):
        raise HTTPException(
            status_code=409,
            detail=f"User with email {db_invite.email} already exists.",
        )

    # Create the Head of unit
    head_of_unit_obj = UserCreate(
        first_name=db_invite.first_name,
        last_name=db_invite.last_name,
        user_type_id=db_invite.user_type_id,
        password=head_of_unit_in.password,
        email=db_invite.email,
    )
    try:
        db_head_of_unit = user_repo.create(db=db, obj_in=head_of_unit_obj)
        if db_head_of_unit:
            head_of_unit_in = HeadOfUnitBase(
                head_of_unit_id=db_head_of_unit.id,
                jurisdiction_id=db_invite.jurisdiction_id,
                created_by_id=db_invite.invited_by_id,
            )
            head_of_unit_repo.create(db=db, obj_in=head_of_unit_in)
        verify_token = user_repo.create_verification_token(
            email=db_head_of_unit.email, db=db
        )
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message="Account created successfully",
            data=UserInResponse(
                id=db_head_of_unit.id,
                first_name=db_head_of_unit.first_name,
                last_name=db_head_of_unit.last_name,
                email=db_head_of_unit.email,
                verify_token=verify_token,
                user_type=UserTypeInDB(
                    name=db_head_of_unit.user_type.name, id=db_head_of_unit.user_type.id
                ),
                is_active=db_head_of_unit.is_active,
            ),
        )
    except Exception as e:
        logger.error(e)


@router.get("/me", dependencies=[Depends(head_of_unit_permission_dependency)])
def retrieve_current_unit_head(
    db: Session = Depends(get_db), user=Depends(get_currently_authenticated_user)
):
    return user_repo.get(db, id=user.id)


@router.get("/{head_of_unit_id}", dependencies=[Depends(admin_permission_dependency)])
def get_unit_head(head_of_unit_id: str, db: Session = Depends(get_db)):
    db_head_of_unit = user_repo.get(db=db, id=head_of_unit_id)
    if (
        db_head_of_unit is None
        or db_head_of_unit.user_type.name != settings.HEAD_OF_UNIT_USER_TYPE
    ):
        raise HTTPException(status_code=404, detail="Head Of Unit not found.")
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Profile retrieved successfully",
        data=FullHeadOfUniteInResponse(
            first_name=db_head_of_unit.first_name,
            last_name=db_head_of_unit.last_name,
            email=db_head_of_unit.email,
            is_active=db_head_of_unit.is_active,
            jurisdiction=CourtSystemInDB(
                id=db_head_of_unit.jurisdiction.id,
                name=db_head_of_unit.jurisdiction.name,
            ),
            user_type=UserTypeInDB(
                id=db_head_of_unit.user_type.id, name=db_head_of_unit.user_type.name
            ),
        ),
    )


@router.get(
    "/get_commissioner/{commissioner_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(head_of_unit_permission_dependency)],
    response_model=GenericResponse[FullCommissionerInResponse],
)
def get_commissioner(
    commissioner_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    db_commissioner = user_repo.get(db=db, id=commissioner_id)
    if (
        db_commissioner is None
        or db_commissioner.user_type.name != settings.COMMISSIONER_USER_TYPE
    ):
        raise HTTPException(status_code=404, detail="Commissioner not found.")
    if (
        db_commissioner.commissioner_profile.court.jurisdiction_id
        != current_user.head_of_unit.jurisdiction_id
    ):
        raise UnauthorizedEndpointException(
            detail="You cannot view this commissioner's report"
        )

    return create_response(
        status_code=status.HTTP_200_OK,
        message="Profile retrieved successfully",
        data=FullCommissionerInResponse(
            id=db_commissioner.id,
            first_name=db_commissioner.first_name,
            last_name=db_commissioner.last_name,
            email=db_commissioner.email,
            is_active=db_commissioner.is_active,
            court=CourtSystemInDB(
                id=db_commissioner.commissioner_profile.court.id,
                name=db_commissioner.commissioner_profile.court.name,
            ),
        ),
    )


@router.post(
    "/get_all_commissioners_report",
    # response_model=GenericResponse[CommissionersReport],
    dependencies=[Depends(head_of_unit_permission_dependency)],
)
async def get_all_commissioners_report(
    date_range: DateRange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    commissioner_profiles = head_of_unit_repo.get_commissioners_under_jurisdiction(
        db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
    )
    results = []
    if date_range.from_date:
        date_range.from_date = datetime.datetime.strptime(
            date_range.from_date, "%Y-%m-%d"
        )
    if date_range.to_date:
        date_range.to_date = datetime.datetime.strptime(
            date_range.to_date, "%Y-%m-%d"
        ) + datetime.timedelta(days=1)

    commissioners = [commissioner.user for commissioner in commissioner_profiles]

    return commissioners
    for commissioner in commissioners:

        query = {
            "is_attested": True,
            "commissioner_id": commissioner.id,
            "attestation_date": {},
        }
        if date_range.from_date:
            query["attestation_date"]["$gte"] = date_range.from_date
        if date_range.to_date:
            query["attestation_date"]["$lt"] = date_range.to_date
        if not query["attestation_date"]:
            del query["attestation_date"]
        attested_documents = await document_collection.find(query).to_list(length=1000)

        commissioner_report = CommissionersReport(
            attested_documents=[
                SlimDocumentInResponse(
                    id=str(document["_id"]),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=(
                        document.get("attest") if document.get("attest", "") else None
                    ),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in attested_documents
            ],
            commissioner=FullCommissionerInResponse(
                id=commissioner.id,
                first_name=commissioner.first_name,
                last_name=commissioner.last_name,
                email=commissioner.email,
                court=CourtSystemInDB(
                    id=commissioner.commissioner_profile.court.id,
                    name=commissioner.commissioner_profile.court.name,
                ),
                is_active=commissioner.is_active,
                date_created=commissioner.CreatedAt,
            ),
        )

        results.append(commissioner_report)
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Commissioners retireved successfully",
        data=results,
    )


@router.post(
    "/get_commissioner_report/{commissioner_id}",
    # response_model=GenericResponse[CommissionerReport],
    dependencies=[Depends(head_of_unit_permission_dependency)],
)
async def get_commissioner_report(
    commissioner_id: str,
    date_range: DateRange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    print(commissioner_id)
    commissioner = user_repo.get(db, id=commissioner_id)

    if not commissioner:
        raise DoesNotExistException(detail="This commissioner does not exist")
    if (
        commissioner.commissioner_profile.court.jurisdiction_id
        != current_user.head_of_unit.jurisdiction_id
    ):
        raise UnauthorizedEndpointException(
            detail="You cannot view this commissioner's report"
        )

    if date_range.from_date:
        date_range.from_date = d = datetime.datetime.strptime(date_range.from_date, "%m/%d/%Y")
    else:
        date_range.from_date = None

    if date_range.to_date:
        date_range.to_date = d = datetime.datetime.strptime(date_range.to_date, "%m/%d/%Y")
    else:
        date_range.to_date = None
    query = {
        "is_attested": True,
        "commissioner_id": commissioner.id,
        "attestation_date": {},
    }
    if date_range.from_date:
        query["attestation_date"]["$gte"] = date_range.from_date
    if date_range.to_date:
        query["attestation_date"]["$lt"] = date_range.to_date
    if not query["attestation_date"]:
        del query["attestation_date"]
    attested_documents = await document_collection.find(query).to_list(length=1000)

    commissioner_report = CommissionersReport(
        attested_documents=[
            DocumentReports(
                name=document.get("name", ""),
                attestation_date=(
                    document.get("attest") if document.get("attest", "") else None
                ),
                date_created=document.get("created_at", ""),
            )
            for document in attested_documents
        ],
        commissioner=FullCommissionerInResponse(
            id=commissioner.id,
            first_name=commissioner.first_name,
            last_name=commissioner.last_name,
            email=commissioner.email,
            court=CourtSystemInDB(
                id=commissioner.commissioner_profile.court.id,
                name=commissioner.commissioner_profile.court.name,
            ),
            is_active=commissioner.is_active,
            date_created=commissioner.CreatedAt,
        ),
    )
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{commissioner.first_name} {commissioner.last_name} report retireved successfully",
        data=commissioner_report,
    )
