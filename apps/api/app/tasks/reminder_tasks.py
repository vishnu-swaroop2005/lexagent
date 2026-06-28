import asyncio
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.utils.supabase_client import get_supabase_client


@celery_app.task
def check_and_send_reminders():
    """Periodic task: Check for pending reminders and send them.

    Runs every hour via Celery Beat.
    Queries the reminders table for unsent reminders past their scheduled time.
    """
    from app.services.email_service import EmailService

    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()

    # Get pending reminders
    reminders = (
        supabase.table("reminders")
        .select("*")
        .eq("is_sent", False)
        .lte("scheduled_at", now)
        .limit(100)
        .execute()
    ).data

    if not reminders:
        return {"sent": 0}

    email_service = EmailService()
    loop = asyncio.new_event_loop()
    sent = 0

    for reminder in reminders:
        if not reminder.get("recipient_email"):
            continue

        try:
            loop.run_until_complete(
                email_service.send_reminder(
                    to=reminder["recipient_email"],
                    subject=reminder["subject"],
                    body=reminder.get("body", ""),
                )
            )

            # Mark as sent
            supabase.table("reminders").update({
                "is_sent": True,
                "sent_at": datetime.utcnow().isoformat(),
            }).eq("id", reminder["id"]).execute()

            sent += 1
        except Exception:
            pass  # Will retry next hour

    loop.close()
    return {"sent": sent}


@celery_app.task
def check_overdue_obligations():
    """Periodic task: Mark obligations as overdue.

    Runs daily at 6 AM UTC via Celery Beat.
    Updates status to 'overdue' for obligations with due_date < now.
    """
    supabase = get_supabase_client()
    today = datetime.utcnow().date().isoformat()

    result = (
        supabase.table("obligations")
        .update({"status": "overdue"})
        .in_("status", ["pending", "in_progress"])
        .lt("due_date", today)
        .execute()
    )

    return {"updated": len(result.data) if result.data else 0}
