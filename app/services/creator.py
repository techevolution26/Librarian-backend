from app.models.creator_account import CreatorAccount
from app.schemas.creator import CreatorDashboardRead


def build_creator_dashboard(account: CreatorAccount) -> CreatorDashboardRead:
    fields = {
        "display_name": bool(account.display_name.strip()),
        "slug": bool(account.slug.strip()),
        "bio": bool(account.bio and account.bio.strip()),
        "website_url": bool(account.website_url),
        "profile_image_url": bool(account.profile_image_url),
    }
    completed = sum(fields.values())
    percent = round((completed / len(fields)) * 100)
    missing = [name for name, present in fields.items() if not present]
    return CreatorDashboardRead(
        account=account,
        profile_completion_percent=percent,
        profile_complete=not missing,
        missing_profile_fields=missing,
    )

