from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Import our validation API
from api.document_validation_api import DocumentValidationAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("document-validation-api")

# Initialize the validation service
validation_api = DocumentValidationAPI()

# Create the FastAPI app
app = FastAPI(
    title="Document Validation API",
    description="API for validating director, company, and TM documents (base64 or URL accepted for all files)",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Flexible input model for all services
class ValidationRequest(BaseModel):
    service_id: str = "1"
    request_id: str
    preconditions: Optional[Dict[str, Any]] = None
    directors: Optional[Dict[str, Any]] = None
    companyDocuments: Optional[Dict[str, Any]] = None
    applicant: Optional[Dict[str, Any]] = None
    Trademarks: Optional[Dict[str, Any]] = None
    nationality: Optional[str] = None
    gst_documents: Optional[Dict[str, Any]] = None
    # Accept any extra fields
    class Config:
        extra = "allow"

# Map service_id to expected document keys for GST services
GST_SERVICE_DOCS = {
    "4": ["aadhar_front", "aadhar_back", "pan", "passport_photo", "signature", "noc", "electricity_bill"],
    "5": ["aadhar_front", "aadhar_back", "pan", "passport_photo", "signature", "noc", "electricity_bill", "rental_agreement"],
    "6": ["aadhar_front", "aadhar_back", "pan", "passport_photo", "signature", "noc", "electricity_bill", "consent_letter"],
    "7": ["aadhar_front", "aadhar_back", "pan", "passport_photo", "signature", "noc", "electricity_bill", "board_resolution"],
}

# Define error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc)
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/validate", response_model=Dict[str, Any])
async def validate_documents(request: ValidationRequest):
    try:
        logger.info(f"Processing validation request: {request.request_id}")
        input_data = request.dict()

        service_id = str(input_data.get("service_id", "1"))

        # TM Service (service_id == 8)
        if service_id == "8":
            if not input_data.get("Trademarks"):
                raise HTTPException(
                    status_code=422,
                    detail="Trademarks information is required for TM service"
                )
            if not input_data.get("applicant"):
                raise HTTPException(
                    status_code=422,
                    detail="Applicant information is required for TM service"
                )
            filtered_input = {
                "service_id": service_id,
                "request_id": input_data.get("request_id"),
                "preconditions": input_data.get("preconditions"),
                "applicant": input_data.get("applicant"),
                "Trademarks": input_data.get("Trademarks")
            }
        # GST Services (service_id 4,5,6,7)
        elif service_id in GST_SERVICE_DOCS:
            # Accept both "gst_documents" and "gstDocuments" keys
            gst_docs = input_data.get("gst_documents") or input_data.get("gstDocuments") or {}
            # If the input is a mixed payload, extract only relevant docs for this service
            expected_keys = GST_SERVICE_DOCS[service_id]
            filtered_gst_docs = {k: v for k, v in gst_docs.items() if k in expected_keys} if gst_docs else {}
            # Add nationality if present
            nationality = input_data.get("nationality", "Indian")
            filtered_input = {
                "service_id": service_id,
                "request_id": input_data.get("request_id"),
                "nationality": nationality,
                "gst_documents": filtered_gst_docs
            }
        # Other services (e.g., director/company validation)
        else:
            if not input_data.get("directors"):
                raise HTTPException(
                    status_code=422,
                    detail="Directors information is required for non-TM services"
                )
            if not input_data.get("companyDocuments"):
                raise HTTPException(
                    status_code=422,
                    detail="Company documents are required for non-TM services"
                )
            filtered_input = {
                "service_id": service_id,
                "request_id": input_data.get("request_id"),
                "preconditions": input_data.get("preconditions"),
                "directors": input_data.get("directors"),
                "companyDocuments": input_data.get("companyDocuments")
            }

        # Process validation
        api_response, _ = validation_api.validate_document(filtered_input)
        logger.info(f"Validation completed for request: {request.request_id}")
        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing validation request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation processing error: {str(e)}"
        )

@app.get("/")
async def root():
    return {
        "message": "Document Validation API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "validate": "/validate"
        }
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


# from fastapi import FastAPI, HTTPException, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import uvicorn
# import logging
# from typing import Dict, Any, Optional
# from pydantic import BaseModel

# # Import our validation API
# from api.document_validation_api import DocumentValidationAPI

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('api_server.log'),
#         logging.StreamHandler()
#     ]
# )

# logger = logging.getLogger("document-validation-api")

# # Initialize the validation service
# validation_api = DocumentValidationAPI()

# # Create the FastAPI app
# app = FastAPI(
#     title="Document Validation API",
#     description="API for validating director, company, and TM documents (base64 or URL accepted for all files)",
#     version="1.0.0",
# )

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, replace with specific origins
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Flexible input model for all services
# class ValidationRequest(BaseModel):
#     service_id: str = "1"
#     request_id: str
#     preconditions: Optional[Dict[str, Any]] = None
#     directors: Optional[Dict[str, Any]] = None
#     companyDocuments: Optional[Dict[str, Any]] = None
#     applicant: Optional[Dict[str, Any]] = None
#     Trademarks: Optional[Dict[str, Any]] = None

#     class Config:
#         extra = "allow"  # Allow any extra fields

# # Define error handler
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     logger.error(f"Global exception: {str(exc)}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": "Internal server error",
#             "message": str(exc)
#         }
#     )

# # Health check endpoint
# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}

# @app.post("/validate", response_model=Dict[str, Any])
# async def validate_documents(request: ValidationRequest):
#     try:
#         logger.info(f"Processing validation request: {request.request_id}")
#         input_data = request.dict()

#         # For standard services, make sure required fields are present
#         if request.service_id not in ["8"]:  # Not a TM service
#             if not request.directors:
#                 raise HTTPException(
#                     status_code=422,
#                     detail="Directors information is required for non-TM services"
#                 )
#             if not request.companyDocuments:
#                 raise HTTPException(
#                     status_code=422,
#                     detail="Company documents are required for non-TM services"
#                 )
#             # Only keep relevant fields
#             filtered_input = {
#                 "service_id": request.service_id,
#                 "request_id": request.request_id,
#                 "preconditions": request.preconditions,
#                 "directors": request.directors,
#                 "companyDocuments": request.companyDocuments
#             }
#         else:  # TM service
#             if not request.Trademarks:
#                 raise HTTPException(
#                     status_code=422,
#                     detail="Trademarks information is required for TM service"
#                 )
#             if not request.applicant:
#                 raise HTTPException(
#                     status_code=422,
#                     detail="Applicant information is required for TM service"
#                 )
#             # Only keep relevant fields
#             filtered_input = {
#                 "service_id": request.service_id,
#                 "request_id": request.request_id,
#                 "preconditions": request.preconditions,
#                 "applicant": request.applicant,
#                 "Trademarks": request.Trademarks
#             }

#         # Process validation
#         api_response, _ = validation_api.validate_document(filtered_input)
#         logger.info(f"Validation completed for request: {request.request_id}")
#         return api_response

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error processing validation request: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail=f"Validation processing error: {str(e)}"
#         )

# @app.get("/")
# async def root():
#     return {
#         "message": "Document Validation API",
#         "version": "1.0.0",
#         "endpoints": {
#             "health": "/health",
#             "validate": "/validate"
#         }
#     }

# if __name__ == "__main__":
#     uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)