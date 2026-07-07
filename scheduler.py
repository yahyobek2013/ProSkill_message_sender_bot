import asyncio
from datetime import datetime

from database.db import (
    add_sent_message,
    get_due_schedules,
    get_group_names,
    save_message,
    update_schedule_status,
)


async def send_payload_to_targets(bot, payload: dict, targets: list[str], group_names: list[str], user_id: int) -> tuple[int, int]:
    message_id = save_message(
        user_id=user_id,
        message_type=payload.get("type", "copy"),
        content=payload.get("content", ""),
        meta=payload.get("meta", ""),
        caption=payload.get("caption", ""),
        targets=", ".join(targets),
        group_names=", ".join(group_names),
        source_chat_id=payload.get("source_chat_id", ""),
        source_message_id=int(payload.get("source_message_id") or 0),
    )

    success = 0
    for target, target_name in zip(targets, group_names):
        try:
            sent = await bot.copy_message(
                chat_id=target,
                from_chat_id=payload["source_chat_id"],
                message_id=payload["source_message_id"],
            )
            add_sent_message(message_id, target, sent.message_id, target_name)
            success += 1
        except Exception:
            continue
    return success, message_id


async def scheduler_loop(bot):
    while True:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in get_due_schedules(now_iso):
            payload = {
                "type": row["type"],
                "content": row["content"],
                "meta": row["meta"],
                "caption": row["caption"],
                "source_chat_id": row["source_chat_id"],
                "source_message_id": row["source_message_id"],
            }
            targets = [target.strip() for target in (row["targets"] or "").split(",") if target.strip()]
            group_names = [name.strip() for name in (row["group_names"] or "").split(",") if name.strip()]
            if len(group_names) != len(targets):
                group_names = get_group_names(targets)

            try:
                success, _ = await send_payload_to_targets(bot, payload, targets, group_names, int(row["user_id"]))
                status = "sent" if success else "failed"
                update_schedule_status(row["id"], status, f"{success}/{len(targets)} yuborildi")
            except Exception as exc:
                update_schedule_status(row["id"], "failed", str(exc)[:200])

        await asyncio.sleep(30)
