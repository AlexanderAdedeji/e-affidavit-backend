import datetime
from typing import List, Optional
from app.repositories.user_repo import user_repo
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import (
    get_currently_authenticated_user,
    head_of_unit_permission_dependency,
    admin_permission_dependency,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    DoesNotExistException,
    UnauthorizedEndpointException,
    ServerException,
)
from app.core.settings.configurations import settings
from app.database.sessions.mongo_client import document_collection
from app.models.user_model import User
from app.repositories.head_of_unit_repo import head_of_unit_repo
from app.repositories.court_system_repo import court_repo
from app.schemas.affidavit_schema import SlimDocumentInResponse, serialize_mongo_document
from app.schemas.court_system_schema import (
    CourtBase,
    CourtInResponse,
    CourtSystemInDB,
)
from app.schemas.shared_schema import DateRange, SlimUserInResponse
from app.schemas.stats_schema import HeadOfUnitDashboardStat
from app.schemas.user_schema import (
    CommissionerInResponse,
    FullCommissionerInResponse,
    FullHeadOfUniteInResponse,
    HeadOfUnitBase,
    HeadOfUnitCreate,
    OperationsCreateForm,
    UserInResponse,
)
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response
from commonLib.utils.logger_config import logger

router = APIRouter()


# ========= Helper Functions =========
def parse_date_range(date_range: DateRange) -> DateRange:
    """
    Parse the from_date and to_date strings into datetime objects.
    If a date is empty or invalid, it will be set to None.
    The to_date is adjusted to be exclusive (end of day).
    """
    try:
        if date_range.from_date:
            date_range.from_date = datetime.datetime.strptime(date_range.from_date, "%Y-%m-%d")
        else:
            date_range.from_date = None
    except ValueError as e:
        logger.error(f"Invalid from_date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be in YYYY-MM-DD format",
        )

    try:
        if date_range.to_date:
            # add one day so that the filter becomes inclusive of the day provided
            dt = datetime.datetime.strptime(date_range.to_date, "%Y-%m-%d")
            date_range.to_date = dt + datetime.timedelta(days=1)
        else:
            date_range.to_date = None
    except ValueError as e:
        logger.error(f"Invalid to_date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_date must be in YYYY-MM-DD format",
        )

    return date_range


# ========= Endpoints =========

@router.get("/get_dashboard_stats", status_code=status.HTTP_200_OK)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse[HeadOfUnitDashboardStat]:
    """
    Return dashboard statistics including total courts, commissioners,
    number of affidavits, and total revenue for the head of unit's jurisdiction.
    """
    try:
        # Get courts under the head of unit's jurisdiction.
        courts = head_of_unit_repo.get_courts_under_jurisdiction(
            db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
        )
        total_commissioners = head_of_unit_repo.get_commissioners_under_jurisdiction(
            db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
        )

        total_affidavits = 0
        total_revenue = 0

        for court in courts:
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
                total_revenue += results[0].get("total_amount", 0)
                documents = results[0].get("documents", [])
                total_affidavits += len(documents)

        stat = HeadOfUnitDashboardStat(
            total_courts=len(courts),
            total_commissioners=len(total_commissioners),
            total_affidavits=total_affidavits,
            total_revenue=total_revenue,
        )
        logger.info("Dashboard stats retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Dashboard Stats fetched successfully.",
            data=stat,
        )
    except Exception as e:
        logger.error(f"Error in get_dashboard_stats: {e}", exc_info=True)
        raise ServerException(detail="Failed to fetch dashboard stats")


@router.get("/courts", status_code=status.HTTP_200_OK, dependencies=[Depends(head_of_unit_permission_dependency)])
async def get_all_courts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse[List[dict]]:
    """
    Return a list of all courts within the head of unit's jurisdiction.
    Each court includes its details and associated documents.
    """
    try:
        courts = head_of_unit_repo.get_courts_under_jurisdiction(
            db=db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
        )
        courts_data = []
        for court in courts:
            db_documents = await document_collection.find({"court_id": court.id}).to_list(length=1000)
            documents = [
                SlimDocumentInResponse(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    price=doc.get("price", 0),
                    attestation_date=doc.get("attest"),
                    created_at=doc.get("created_at", ""),
                    status=doc.get("status", ""),
                )
                for doc in db_documents
            ]
            court_info = {
                "id": court.id,
                "date_created": court.CreatedAt,
                "name": court.name,
                "Jurisdiction": CourtSystemInDB(id=court.jurisdiction.id, name=court.jurisdiction.name),
                "commissioners": [
                    SlimUserInResponse(
                        id=commissioner.user.id,
                        first_name=commissioner.user.first_name,
                        last_name=commissioner.user.last_name,
                        email=commissioner.user.email,
                    )
                    for commissioner in court.commissioner_profiles
                ],
                "documents": documents,
            }
            courts_data.append(court_info)
        logger.info(f"Retrieved {len(courts_data)} courts")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Courts Retrieved Successfully",
            data=courts_data,
        )
    except Exception as e:
        logger.error(f"Error in get_all_courts: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")


@router.get("/get_court/{court_id}", dependencies=[Depends(head_of_unit_permission_dependency)])
async def get_court(
    court_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse[CourtInResponse]:
    """
    Get details of a specific court.
    The head of unit can only view courts within their jurisdiction.
    """
    try:
        court = court_repo.get(db, id=court_id)
        if not court:
            raise DoesNotExistException(detail=f"Court with id {court_id} does not exist")
        if current_user.head_of_unit.jurisdiction_id != court.jurisdiction_id:
            raise UnauthorizedEndpointException(detail="This court is not in your jurisdiction")

        db_documents = await document_collection.find(
            {"court_id": court.id, "status": {"$in": ["PAID", "ATTESTED"]}}
        ).to_list(length=1000)
        court_docs = serialize_mongo_document(db_documents)

        response_data = CourtInResponse(
            id=court.id,
            name=court.name,
            date_created=court.CreatedAt,
            jurisdiction=CourtSystemInDB(id=court.jurisdiction.id, name=court.jurisdiction.name),
            commissioners=[
                SlimUserInResponse(
                    id=commissioner.user.id,
                    first_name=commissioner.user.first_name,
                    last_name=commissioner.user.last_name,
                    email=commissioner.user.email,
                    is_active=commissioner.user.is_active,
                )
                for commissioner in court.commissioner_profiles
            ],
            documents=[
                SlimDocumentInResponse(
                    id=str(doc.get("id", "")),
                    name=doc.get("name", ""),
                    price=doc.get("price", 0),
                    attestation_date=doc.get("attest", ""),
                    created_at=doc.get("created_at", ""),
                    status=doc.get("status", ""),
                )
                for doc in court_docs
            ],
        )
        logger.info(f"Court {court.name} details retrieved")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{court.name} Retrieved successfully",
            data=response_data,
        )
    except Exception as e:
        logger.error(f"Error in get_court: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving court details")


@router.get("/commissioners/", status_code=status.HTTP_200_OK, dependencies=[Depends(head_of_unit_permission_dependency)])
async def get_commissioners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse[List[FullCommissionerInResponse]]:
    """
    Return a list of commissioners under the head of unit's jurisdiction,
    including their attested document summaries.
    """
    try:
        commissioner_profiles = head_of_unit_repo.get_commissioners_under_jurisdiction(
            db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
        )
        commissioners = [cp.user for cp in commissioner_profiles]
        results = []
        for commissioner in commissioners:
            attested_docs = await document_collection.find(
                {"commissioner_id": commissioner.id}
            ).to_list(length=1000)
            docs_serialized = [
                SlimDocumentInResponse(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    price=doc.get("price", 0),
                    attestation_date=doc.get("attest"),
                    created_at=doc.get("created_at", ""),
                    status=doc.get("status", ""),
                )
                for doc in attested_docs
            ]
            full_commissioner = FullCommissionerInResponse(
                id=commissioner.id,
                first_name=commissioner.first_name,
                last_name=commissioner.last_name,
                email=commissioner.email,
                is_active=commissioner.is_active,
                court=CourtSystemInDB(
                    id=commissioner.commissioner_profile.court.id,
                    name=commissioner.commissioner_profile.court.name,
                ),
                attested_documents=docs_serialized,
            )
            results.append(full_commissioner)
        logger.info(f"Retrieved {len(results)} commissioners")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Commissioners retrieved successfully",
            data=results,
        )
    except Exception as e:
        logger.error(f"Error in get_commissioners: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving commissioners")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_head_of_unit(
    head_of_unit_in: OperationsCreateForm,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> GenericResponse[UserInResponse]:
    """
    Create a new Head of Unit account using a valid invitation.
    """
    try:
        db_invite = user_invite_repo.get(db=db, id=head_of_unit_in.invite_id)
        if not db_invite:
            raise DoesNotExistException(detail="Invitation does not exist or is invalid.")
        if not db_invite.is_accepted:
            raise HTTPException(
                status_code=403,
                detail="Cannot use un-accepted invites for creating new accounts.",
            )
        if db_invite.user_type.name != settings.HEAD_OF_UNIT_USER_TYPE:
            raise UnauthorizedEndpointException(
                detail="You do not have permission to access this endpoint."
            )
        if user_repo.get_by_email(db=db, email=db_invite.email):
            raise HTTPException(
                status_code=409,
                detail=f"User with email {db_invite.email} already exists.",
            )

        head_of_unit_obj = UserCreate(
            first_name=db_invite.first_name,
            last_name=db_invite.last_name,
            user_type_id=db_invite.user_type_id,
            password=head_of_unit_in.password,
            email=db_invite.email,
        )
        db_head_of_unit = user_repo.create(db=db, obj_in=head_of_unit_obj)
        if db_head_of_unit:
            unit_data = HeadOfUnitBase(
                head_of_unit_id=db_head_of_unit.id,
                jurisdiction_id=db_invite.jurisdiction_id,
                created_by_id=db_invite.invited_by_id,
            )
            head_of_unit_repo.create(db=db, obj_in=unit_data)
        verify_token = user_repo.create_verification_token(email=db_head_of_unit.email, db=db)
        verification_link = f"{settings.COURT_SYSTEM_FRONTEND_BASE_URL}{settings.VERIFY_EMAIL_LINK}{verify_token}"
        template_dict = UserCreationTemplateVariables(
            name=f"{db_head_of_unit.first_name} {db_head_of_unit.last_name}",
            action_url=verification_link,
        ).dict()
        logger.info(f"Verification link for Head of Unit: {verification_link}")
        email_service.send_email_with_template(
            db=db,
            template_id=settings.CREATE_ACCOUNT_TEMPLATE_ID,
            template_dict=template_dict,
            recipient=db_head_of_unit.email,
            background_tasks=background_tasks,
        )
        logger.info("Head of Unit account created successfully")
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
                    name=db_head_of_unit.user_type.name,
                    id=db_head_of_unit.user_type.id,
                ),
                is_active=db_head_of_unit.is_active,
            ),
        )
    except Exception as e:
        logger.error(f"Error in create_head_of_unit: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating the Head of Unit account",
        )


@router.get("/me", dependencies=[Depends(head_of_unit_permission_dependency)])
def retrieve_current_unit_head(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse[UserInResponse]:
    """
    Retrieve the currently logged-in Head of Unit's profile.
    """
    try:
        user_obj = user_repo.get(db, id=current_user.id)
        if not user_obj:
            raise DoesNotExistException(detail="User not found")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Profile retrieved successfully",
            data=UserInResponse(
                id=user_obj.id,
                first_name=user_obj.first_name,
                last_name=user_obj.last_name,
                email=user_obj.email,
                is_active=user_obj.is_active,
                user_type=UserTypeInDB(id=user_obj.user_type.id, name=user_obj.user_type.name),
                verify_token="",
            ),
        )
    except Exception as e:
        logger.error(f"Error in retrieve_current_unit_head: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving profile")


@router.get("/{head_of_unit_id}", dependencies=[Depends(admin_permission_dependency)])
def get_unit_head(
    head_of_unit_id: str, db: Session = Depends(get_db)
) -> GenericResponse[FullHeadOfUniteInResponse]:
    """
    Retrieve the profile of a Head of Unit by ID.
    Admin only.
    """
    try:
        db_head = user_repo.get(db=db, id=head_of_unit_id)
        if not db_head or db_head.user_type.name != settings.HEAD_OF_UNIT_USER_TYPE:
            raise DoesNotExistException(detail="Head Of Unit not found.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Profile retrieved successfully",
            data=FullHeadOfUniteInResponse(
                first_name=db_head.first_name,
                last_name=db_head.last_name,
                email=db_head.email,
                is_active=db_head.is_active,
                jurisdiction=CourtSystemInDB(
                    id=db_head.jurisdiction.id, name=db_head.jurisdiction.name
                ),
                user_type=UserTypeInDB(id=db_head.user_type.id, name=db_head.user_type.name),
            ),
        )
    except Exception as e:
        logger.error(f"Error in get_unit_head: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving Head of Unit")


@router.get(
    "/get_commissioner/{commissioner_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(head_of_unit_permission_dependency)],
)
def get_commissioner(
    commissioner_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse[FullCommissionerInResponse]:
    """
    Retrieve a commissioner's full profile by ID.
    The Head of Unit can only view commissioners within their jurisdiction.
    """
    try:
        db_commissioner = user_repo.get(db=db, id=commissioner_id)
        if not db_commissioner or db_commissioner.user_type.name != settings.COMMISSIONER_USER_TYPE:
            raise HTTPException(status_code=404, detail="Commissioner not found.")
        if db_commissioner.commissioner_profile.court.jurisdiction_id != current_user.head_of_unit.jurisdiction_id:
            raise UnauthorizedEndpointException(detail="You cannot view this commissioner's report")
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
    except Exception as e:
        logger.error(f"Error in get_commissioner: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving commissioner")


@router.post(
    "/get_all_commissioners_report",
    dependencies=[Depends(head_of_unit_permission_dependency)],
)
async def get_all_commissioners_report(
    date_range: DateRange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse[List]:
    """
    Retrieve a report for all commissioners under the head of unit's jurisdiction,
    optionally filtered by a date range.
    """
    try:
        # Parse the date range
        parsed_date_range = parse_date_range(date_range)
        commissioner_profiles = head_of_unit_repo.get_commissioners_under_jurisdiction(
            db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
        )
        results = []
        commissioners = [cp.user for cp in commissioner_profiles]
        for commissioner in commissioners:
            query = {
                "is_attested": True,
                "commissioner_id": commissioner.id,
            }
            if parsed_date_range.from_date:
                query.setdefault("attestation_date", {})["$gte"] = parsed_date_range.from_date
            if parsed_date_range.to_date:
                query.setdefault("attestation_date", {})["$lt"] = parsed_date_range.to_date
            if "attestation_date" in query and not query["attestation_date"]:
                del query["attestation_date"]
            attested_docs = await document_collection.find(query).to_list(length=1000)
            commissioner_report = {
                "commissioner": {
                    "id": commissioner.id,
                    "first_name": commissioner.first_name,
                    "last_name": commissioner.last_name,
                    "email": commissioner.email,
                    "court": {
                        "id": commissioner.commissioner_profile.court.id,
                        "name": commissioner.commissioner_profile.court.name,
                    },
                    "is_active": commissioner.is_active,
                    "date_created": commissioner.CreatedAt,
                },
                "attested_documents": [

                    
                    {
                        "id": str(doc["_id"]),
                        "name": doc.get("name", ""),
                        "price": doc.get("price", 0),
                        "attestation_date": doc.get("attest"),
                        "created_at": doc.get("created_at", ""),
                        "status": doc.get("status", ""),
                    }
                    for doc in attested_docs
                ],
            }
            results.append(commissioner_report)
        logger.info(f"Commissioners report retrieved for {len(results)} commissioners")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Commissioners report retrieved successfully",
            data=results,
        )
    except Exception as e:
        logger.error(f"Error in get_all_commissioners_report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating report")


@router.post(
    "/get_commissioner_report/{commissioner_id}",

    dependencies=[Depends(head_of_unit_permission_dependency)],
)
async def get_commissioner_report(
    commissioner_id: str,
    date_range: DateRange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) -> GenericResponse:
    """
    Retrieve a detailed report for a specific commissioner, filtered by an optional date range.
    """
    try:
        commissioner = user_repo.get(db, id=commissioner_id)
        if not commissioner:
            raise DoesNotExistException(detail="This commissioner does not exist")
        if commissioner.commissioner_profile.court.jurisdiction_id != current_user.head_of_unit.jurisdiction_id:
            raise UnauthorizedEndpointException(detail="You cannot view this commissioner's report")

        parsed_date_range = parse_date_range(date_range)
        query = {"is_attested": True, "commissioner_id": commissioner.id}
        if parsed_date_range.from_date:
            query.setdefault("attestation_date", {})["$gte"] = parsed_date_range.from_date
        if parsed_date_range.to_date:
            query.setdefault("attestation_date", {})["$lt"] = parsed_date_range.to_date
        if "attestation_date" in query and not query["attestation_date"]:
            del query["attestation_date"]

        attested_docs = await document_collection.find(query).to_list(length=1000)
        commissioner_report = {
            "commissioner": {
                "id": commissioner.id,
                "first_name": commissioner.first_name,
                "last_name": commissioner.last_name,
                "email": commissioner.email,
                "court": {
                    "id": commissioner.commissioner_profile.court.id,
                    "name": commissioner.commissioner_profile.court.name,
                },
                "is_active": commissioner.is_active,
                "date_created": commissioner.CreatedAt,
            },
            "attested_documents": [
                {
                    "name": doc.get("name", ""),
                    "attested_date": doc.get("attestation_date", ""),
                    "date_created": doc.get("created_at", ""),
                }
                for doc in attested_docs
            ],
        }
        logger.info(f"Report retrieved for commissioner {commissioner_id}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{commissioner.first_name} {commissioner.last_name} report retrieved successfully",
            data=commissioner_report,
        )
    except Exception as e:
        logger.error(f"Error in get_commissioner_report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating commissioner report")





####################Dashboard Information########


@router.get("/top-commissioners")
async def get_top_commissioners(month: int, year: int,     current_user: User = Depends(get_currently_authenticated_user),):
    """
    Retrieve the top performing commissioners for the specified month based on the number of attested affidavits.
    Since the documents do not include a jurisdiction_id, we perform a $lookup to join each document with the 
    commissioners collection using the commissioner_id. This allows us to filter by the HoU's jurisdiction.
    """
    try:
        # Calculate the start and end dates for the specified month
        start_date = datetime(year, month, 1, tzinfo=datetime.timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=datetime.timezone.utc)

        # Extract the HoU's jurisdiction from the current user (JWT payload)
        jurisdiction_id = current_user.jurisdiction_id

        # Define the aggregation pipeline
        pipeline = [
            # 1. Filter affidavits that have been attested within the specified month
            {
                "$match": {
                    "isAttested": True,
                    "attestation_date": {"$gte": start_date, "$lt": end_date},
                }
            },
            # 2. Join with the commissioners collection using commissioner_id
            {
                "$lookup": {
                    "from": "commissioners",         # Name of the commissioners collection
                    "localField": "commissioner_id",   # Field in documents representing who attested
                    "foreignField": "id",              # Field in commissioners collection (assumed to be 'id')
                    "as": "commissioner_info"
                }
            },
            # 3. Unwind the joined array to work with individual commissioner objects
            {"$unwind": "$commissioner_info"},
            # 4. Filter documents to only include those where the commissioner belongs to the current jurisdiction
            {
                "$match": {
                    "commissioner_info.jurisdiction_id": jurisdiction_id
                }
            },
            # 5. Group by commissioner_id and count the total affidavits per commissioner
            {
                "$group": {
                    "_id": "$commissioner_id",
                    "totalAffidavits": {"$sum": 1},
                    "commissioner_info": {"$first": "$commissioner_info"}
                }
            },
            # 6. Sort the results in descending order by the total number of affidavits
            {"$sort": {"totalAffidavits": -1}},
            # 7. Limit the output to the top 5 commissioners
            {"$limit": 5}
        ]

        # Execute the aggregation pipeline
        results = list(db.documents.aggregate(pipeline))
        if not results:
            raise HTTPException(status_code=404, detail="No attested affidavits found for the specified period.")

        return {"top_commissioners": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    





@router.get("/recent-activities")
async def get_recent_activities(current_user = Depends(get_currently_authenticated_user)):
    """
    Retrieve the top 5 most recent affidavit activities in the current HoU's jurisdiction.
    Activities include creation, payment, and attestation events. For attestation events,
    we also show which commissioner attested the affidavit.
    """
    try:
        # Build the aggregation pipeline:
        pipeline = [
            # 1. Add a field 'last_activity_date' which is the maximum of created_at, payment_date, and attestation_date.
            {
                "$addFields": {
                    "last_activity_date": {
                        "$max": [
                            "$created_at",
                            "$payment_date",
                            "$attestation_date"
                        ]
                    }
                }
            },
            # 2. Optionally, filter to include only documents with a valid last_activity_date (if needed)
            {
                "$match": {
                    "last_activity_date": {"$ne": None}
                }
            },
            # 3. Join with the commissioners collection using the commissioner_id.
            #    This is mainly useful for attested documents where commissioner details are available.
            {
                "$lookup": {
                    "from": "commissioners",         # Name of the commissioners collection
                    "localField": "commissioner_id",   # Field in the document representing the attesting commissioner
                    "foreignField": "id",              # Field in commissioners collection (adjust if needed)
                    "as": "commissioner_info"
                }
            },
            # 4. Unwind the joined commissioner array. This step ensures we work with individual commissioner objects.
            {"$unwind": "$commissioner_info"},
            # 5. Filter documents to only include those where the commissioner belongs to the current HoU's jurisdiction.
            {
                "$match": {
                    "commissioner_info.jurisdiction_id": current_user.jurisdiction_id
                }
            },
            # 6. Sort documents by last_activity_date in descending order (most recent first).
            {"$sort": {"last_activity_date": -1}},
            # 7. Limit the output to the top 5 recent activities.
            {"$limit": 5},
            # 8. Optionally, project only the required fields for clarity.
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "status": 1,
                    "created_at": 1,
                    "payment_date": 1,
                    "attestation_date": 1,
                    "last_activity_date": 1,
                    "commissioner_id": 1,
                    "commissioner_info.full_name": 1,
                    "commissioner_info.email": 1
                }
            }
        ]

        # Execute the aggregation pipeline
        results = list(db.documents.aggregate(pipeline))
        if not results:
            raise HTTPException(status_code=404, detail="No recent activities found in the specified jurisdiction.")

        return {"recent_activities": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")





from fastapi import APIRouter, Depends, HTTPException
from pymongo import MongoClient
from datetime import datetime, timezone
from app.dependencies import get_current_user  # Assumes this returns a user with a 'jurisdiction_id' attribute

router = APIRouter()

# Setup MongoDB client and database (adjust connection details and database name as needed)
client = MongoClient("mongodb://localhost:27017")
db = client.affidavit_db  # Replace with your actual database name

def get_month_date_range(year: int, month: int):
    """
    Returns a tuple of (start_date, end_date) for the given year and month in UTC.
    For example, if year=2025 and month=3, start_date = 2025-03-01T00:00:00Z
    and end_date = 2025-04-01T00:00:00Z.
    """
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start_date, end_date

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    year: int,
    month: int,
    current_user = Depends(get_current_user)
):
    """
    Returns a set of dashboard statistics for the HoU’s jurisdiction, including:
    - Total commissioners (active vs. inactive)
    - Total courts
    - Pending affidavits
    - Completed affidavits
    - Completed affidavits for the specified month
    Growth metrics are placeholders; implement your own logic to compare current data
    to a previous period if you need them.
    """
    try:
        # 1) Identify commissioners in the HoU's jurisdiction
        jurisdiction_id = current_user.jurisdiction_id
        commissioner_cursor = db.commissioners.find(
            {"jurisdiction_id": jurisdiction_id},
            {"_id": 0, "id": 1, "isActive": 1}  # Return only 'id' and 'isActive' for efficiency
        )
        commissioners_in_jurisdiction = list(commissioner_cursor)

        # Extract commissioner IDs and track active vs. inactive
        commissioner_ids = [c["id"] for c in commissioners_in_jurisdiction]
        total_commissioners = len(commissioners_in_jurisdiction)
        active_commissioners = sum(1 for c in commissioners_in_jurisdiction if c.get("isActive"))
        inactive_commissioners = total_commissioners - active_commissioners

        # 2) Total courts in this jurisdiction
        total_courts = db.courts.count_documents({"jurisdiction_id": jurisdiction_id})

        # 3) Count pending affidavits
        #    Assume "pending" means status="PENDING" (adjust if needed)
        pending_affidavits = db.documents.count_documents({
            "commissioner_id": {"$in": commissioner_ids},
            "status": "PENDING"
        })

        # 4) Count completed (attested) affidavits
        completed_affidavits = db.documents.count_documents({
            "commissioner_id": {"$in": commissioner_ids},
            "status": "ATTESTED"
        })

        # 5) Count completed (attested) affidavits for the specified month/year
        start_date, end_date = get_month_date_range(year, month)
        completed_this_month = db.documents.count_documents({
            "commissioner_id": {"$in": commissioner_ids},
            "status": "ATTESTED",
            "attestation_date": {"$gte": start_date, "$lt": end_date}
        })

        # (Optional) Growth metrics - placeholders for demonstration
        # In a real system, you'd compare current data vs. a previous period
        commissioners_growth = "+12%"
        courts_growth = "+29%"
        pending_growth = "+28%"
        # Similarly, you can calculate a growth rate for completed affidavits if desired

        return {
            "total_commissioners": {
                "count": total_commissioners,
                "active": active_commissioners,
                "inactive": inactive_commissioners,
                "growth": commissioners_growth
            },
            "total_courts": {
                "count": total_courts,
                "growth": courts_growth
            },
            "pending_affidavits": {
                "count": pending_affidavits,
                "growth": pending_growth
            },
            "completed_affidavits": {
                "count": completed_affidavits,
                "this_month": completed_this_month
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
