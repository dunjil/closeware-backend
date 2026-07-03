from fastapi import APIRouter
from app.api.v1.endpoints import auth, deals, correspondence, documents, contract_drafts, comparison, organizations, contract_generation, contract_fixes, signatures, internal_reviews, external_invites, subscriptions, signup, signature_requests, audit_trail

api_router = APIRouter()

api_router.include_router(signup.router, prefix="/auth", tags=["auth"])  # New unified signup
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])  # Keep old login for now
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(deals.router, prefix="/deals", tags=["deals"])
api_router.include_router(correspondence.router, prefix="/correspondence", tags=["correspondence"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(contract_drafts.router, prefix="/contract-drafts", tags=["contract-drafts"])
api_router.include_router(comparison.router, prefix="/comparison", tags=["comparison"])
api_router.include_router(contract_generation.router, prefix="/contracts", tags=["contract-generation"])
api_router.include_router(contract_fixes.router, prefix="/fixes", tags=["contract-fixes"])
api_router.include_router(signatures.router, prefix="/signatures", tags=["signatures"])
api_router.include_router(signature_requests.router, prefix="/signature-requests", tags=["signature-requests"])
api_router.include_router(internal_reviews.router, prefix="/internal-reviews", tags=["internal-reviews"])
api_router.include_router(external_invites.router, prefix="/external", tags=["external-invites"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(audit_trail.router, prefix="/audit-trail", tags=["audit-trail"])
