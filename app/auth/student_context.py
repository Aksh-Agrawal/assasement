"""Local routing preparation; cached context never grants authenticated access."""

from dataclasses import dataclass

from app.data.repo import Repository


@dataclass(frozen=True)
class StudentRoutingContext:
    cloud_account_id: str | None
    auth_state: str
    owned_profile_ids: tuple[str, ...]
    legacy_profile_ids: tuple[str, ...]
    offline_policy: str = "pending"


def load_student_routing_context(repository: Repository) -> StudentRoutingContext:
    context = repository.get_student_account_context()
    account_id = context["cloud_account_id"] if context else None
    profiles = repository.list_profiles()
    return StudentRoutingContext(
        cloud_account_id=account_id,
        auth_state="verification_required" if context else "signed_out",
        owned_profile_ids=tuple(
            p.id for p in profiles
            if p.ownership_state == "owned" and p.cloud_account_id == account_id
        ),
        legacy_profile_ids=tuple(p.id for p in profiles if p.ownership_state == "legacy_unclaimed"),
    )
