

# # @router.post(
# #     "/create_template",
# #     # dependencies=[Depends(admin_permission_dependency)],
# #     status_code=status.HTTP_201_CREATED,
# #     response_model=GenericResponse[TemplateBase],
# # )
# # async def create_template(
# #     template_in: TemplateCreateForm,
# #     # current_user: User = Depends(get_currently_authenticated_user),
# # ):
# #     template_dict = template_in.dict()
# #     existing_template = await template_collection.find_one(
# #         {"name": template_dict["name"]}
# #     )
# #     if existing_template:

# #         raise HTTPException(
# #             status_code=400, detail="Template with the given name already exists"
# #         )
# #     template_dict = TemplateCreate(
# #         **template_dict, created_by_id="1"
# #     ).dict()

# #     result = await template_collection.insert_one(template_dict)
# #     if not result.acknowledged:
# #         logger.error("Failed to insert template")
# #         raise HTTPException(status_code=500, detail="Failed to create template")

# #     new_template = await template_collection.find_one({"_id": result.inserted_id})
# #     return create_response(
# #         status_code=status.HTTP_201_CREATED,
# #         message=f"{new_template['name']} template Created Successfully",
# #         data=template_individual_serializer(new_template),
# #     )







# # @router.get(
# #     "/get_templates",
# #     # dependencies=[Depends(admin_permission_dependency)],
# #     response_model=GenericResponse[List[TemplateBase]],
# # )
# # async def get_templates():
# #     try:
# #         templates = await template_collection.find().to_list(length=100)
# #         if not templates:
# #             logger.info("No templates found")
# #             return create_response(
# #                 status_code=status.HTTP_404_NOT_FOUND,
# #                 message="No templates found",
# #                 data=[],
# #             )

# #         return create_response(
# #             status_code=status.HTTP_200_OK,
# #             message="Templates retrieved successfully",
# #             data=template_list_serialiser(templates),
# #         )

# #     except Exception as e:
# #         logger.error(f"Error fetching templates: {str(e)}")
# #         raise HTTPException(status_code=500, detail="Error fetching templates")


# # @router.get(
# #     "/get_template/{template_id}",
# #     response_model=GenericResponse[TemplateBase],
# #     # dependencies=[Depends(admin_permission_dependency)],
# # )
# # async def get_template(template_id: str):
# #     try:
# #         # Convert the string ID to ObjectId
# #         object_id = ObjectId(template_id)
# #     except Exception as e:
# #         raise HTTPException(status_code=400, detail=f"Invalid ID format: {template_id}")

# #     # Log the ObjectId
# #     logging.info(f"Fetching template with ID: {object_id}")

# #     template_obj = await template_collection.find_one({"_id": object_id})

# #     # Log the result of the query
# #     if template_obj:
# #         logging.info(f"Found template: {template_obj}")
# #     else:
# #         logging.info("No template found")

# #     if not template_obj:
# #         raise HTTPException(
# #             status_code=404,
# #             detail=f"Template with ID {template_id} does not exist",
# #         )

# #     # Assuming individual_serialiser is a valid function
# #     template_obj = template_individual_serializer(template_obj)
# #     return create_response(
# #         status_code=status.HTTP_200_OK,
# #         message=f"{template_obj['name']} retrieved successfully",
# #         data=template_obj,
# #     )





# @router.get("/get_documents", dependencies=[Depends(admin_permission_dependency)])
# async def get_documents():
#     try:
#         documents = await document_collection.find().to_list(
#             length=100
#         )  # Set a reasonable limit
#         if not documents:
#             logger.info("No documents found")
#             return []
#         return create_response(
#             status_code=status.HTTP_200_OK,
#             data=document_list_serialiser(documents),
#             message=f"Documents retrieved successfully",
#         )
#     except Exception as e:
#         logger.error(f"Error fetching documents: {str(e)}")
#         raise HTTPException(status_code=500, detail="Error fetching documents")


# @router.get("/get_single_document/{document_id}")
# async def get_single_document(document_id: str):
#     try:
#         object_id = ObjectId(document_id)
#     except Exception as e:
#         logger.error(f"Invalid ID format for document: {document_id} - {str(e)}")
#         raise HTTPException(status_code=400, detail="Invalid document ID format")

#     document_obj = await document_collection.find_one({"_id": object_id})
#     if not document_obj:
#         logger.info(f"No document found with ID: {object_id}")
#         raise HTTPException(status_code=404, detail="Document not found")

#     template = await get_single_template(
#         document_obj["templateId"]
#     )  # Ensure this is correctly handled
#     return {
#         "name": document_obj["name"],
#         "template": {"content": template["content"], "id": document_obj["templateId"]},
#         "documentFields": document_obj["documentFields"],
#     }



