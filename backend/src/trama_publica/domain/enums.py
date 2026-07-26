"""Catálogos controlados del núcleo histórico."""

from enum import StrEnum


class EntityType(StrEnum):
    PERSON = "person"
    ORGANIZATION = "organization"
    PUBLIC_OFFICE = "public_office"
    MANDATE = "mandate"
    ELECTORAL_TERRITORY = "electoral_territory"
    JUDICIAL_CASE = "judicial_case"
    JUDICIAL_EVENT = "judicial_event"


class IdentityStatus(StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ReviewStatus(StrEnum):
    DISCOVERED = "discovered"
    EXTRACTED = "extracted"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CORRECTED = "corrected"
    ARCHIVED = "archived"


class OfficeLevel(StrEnum):
    NATIONAL = "national"
    REGIONAL = "regional"
    MUNICIPAL = "municipal"
    PARTY = "party"
    OTHER = "other"


class TerritoryType(StrEnum):
    DISTRICT = "district"
    SENATORIAL_CONSTITUENCY = "senatorial_constituency"
    REGION = "region"
    COMMUNE = "commune"
    NATIONAL = "national"
    OTHER = "other"


class OrganizationType(StrEnum):
    POLITICAL_PARTY = "political_party"
    COALITION = "coalition"
    COMPANY = "company"
    FOUNDATION = "foundation"
    PUBLIC_BODY = "public_body"
    ASSOCIATION = "association"
    OTHER = "other"


class MandateStatus(StrEnum):
    ELECTED = "elected"
    APPOINTED = "appointed"
    ACTING = "acting"
    COMPLETED = "completed"
    RESIGNED = "resigned"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class CaseStatus(StrEnum):
    REPORTED = "reported"
    FILED = "filed"
    INVESTIGATING = "investigating"
    CHARGED = "charged"
    TRIAL = "trial"
    DECIDED = "decided"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class FinalityStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    APPEALABLE = "appealable"
    FINAL = "final"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


class JudicialRole(StrEnum):
    ACCUSED = "accused"
    DEFENDANT = "defendant"
    CONVICTED_PERSON = "convicted_person"
    ACQUITTED_PERSON = "acquitted_person"
    COMPLAINANT = "complainant"
    PLAINTIFF = "plaintiff"
    RESPONDENT = "respondent"
    WITNESS = "witness"
    ATTORNEY = "attorney"
    AUTHORITY = "authority"
    MENTIONED = "mentioned"
    OTHER = "other"
    UNKNOWN = "unknown"


class JudicialOutcome(StrEnum):
    PENDING = "pending"
    CONVICTED = "convicted"
    ACQUITTED = "acquitted"
    DISMISSED = "dismissed"
    DEFINITIVELY_DISMISSED = "definitively_dismissed"
    PROVISIONALLY_DISMISSED = "provisionally_dismissed"
    PRESCRIBED = "prescribed"
    ARCHIVED = "archived"
    REVOKED = "revoked"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class JudicialEventType(StrEnum):
    COMPLAINT = "complaint"
    FILING = "filing"
    INVESTIGATION = "investigation"
    INDICTMENT = "indictment"
    FORMALIZATION = "formalization"
    ACCUSATION = "accusation"
    HEARING = "hearing"
    TRIAL = "trial"
    JUDGMENT = "judgment"
    APPEAL = "appeal"
    CONFIRMATION = "confirmation"
    REVOCATION = "revocation"
    DISMISSAL = "dismissal"
    CLOSURE = "closure"
    OTHER = "other"


class SourceType(StrEnum):
    OFFICIAL_DOCUMENT = "official_document"
    ADMINISTRATIVE_RESOLUTION = "administrative_resolution"
    JUDICIAL_FILING = "judicial_filing"
    JUDICIAL_DECISION = "judicial_decision"
    FINAL_JUDICIAL_DECISION = "final_judicial_decision"
    LEGISLATIVE_RECORD = "legislative_record"
    PUBLIC_REGISTRY = "public_registry"
    TRANSPARENCY_RESPONSE = "transparency_response"
    ARCHIVE_DOCUMENT = "archive_document"
    MEDIA_REFERENCE = "media_reference"
    OTHER = "other"


class AccessStatus(StrEnum):
    AVAILABLE = "available"
    RESTRICTED = "restricted"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ProcessingStatus(StrEnum):
    DOWNLOADED = "downloaded"
    PARSED = "parsed"
    PARTIALLY_PARSED = "partially_parsed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class IngestionStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class EvidenceLevel(StrEnum):
    UNVERIFIED_REFERENCE = "unverified_reference"
    MEDIA_REFERENCE = "media_reference"
    OFFICIAL_DOCUMENT = "official_document"
    ADMINISTRATIVE_RESOLUTION = "administrative_resolution"
    JUDICIAL_FILING = "judicial_filing"
    JUDICIAL_DECISION = "judicial_decision"
    FINAL_JUDICIAL_DECISION = "final_judicial_decision"


class Predicate(StrEnum):
    HELD_OFFICE = "HELD_OFFICE"
    MEMBER_OF_PARTY = "MEMBER_OF_PARTY"
    MEMBER_OF_ORGANIZATION = "MEMBER_OF_ORGANIZATION"
    SHAREHOLDER_OF = "SHAREHOLDER_OF"
    DIRECTOR_OF = "DIRECTOR_OF"
    PARTNER_OF = "PARTNER_OF"
    PARTICIPATED_IN_CASE = "PARTICIPATED_IN_CASE"
    ACCUSED_IN = "ACCUSED_IN"
    CONVICTED_IN = "CONVICTED_IN"
    ACQUITTED_IN = "ACQUITTED_IN"
    DISMISSED_FROM_CASE = "DISMISSED_FROM_CASE"
    SANCTIONED_BY = "SANCTIONED_BY"
    SERVED_WITH = "SERVED_WITH"
    CO_DEFENDANT_WITH = "CO_DEFENDANT_WITH"
    CO_OWNED_WITH = "CO_OWNED_WITH"


PROHIBITED_PREDICATES = frozenset(
    {
        "CONSPIRED_WITH",
        "CORRUPT_NETWORK",
        "CRIMINAL_ASSOCIATE",
        "IS_CORRUPT",
        "IS_CRIMINAL",
        "IS_SUSPICIOUS",
    }
)


class PublicationStatus(StrEnum):
    PRIVATE = "private"
    REVIEW_ONLY = "review_only"
    PUBLISHABLE = "publishable"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    CORRECT = "correct"
    ARCHIVE = "archive"
