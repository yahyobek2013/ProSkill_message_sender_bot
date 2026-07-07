state = {
    "mode": None,
    "draft": None,
    "targets": [],
    "group_names": [],
    "selected_targets": set(),
    "edit_id": None,
    "edit_group_id": None,
    "edit_admin_id": None,
    "new_group_id": None,
    "new_group_type": None,
    "new_admin_id": None,
    "pending_group_name": None,
    "pending_admin_name": None,
    "pending_admin_message_id": None,
    "schedule_message_id": None,
    "schedule_year": None,
    "schedule_month": None,
    "schedule_day": None,
    "schedule_hour": None,
    "schedule_minute": None,
}


def reset_state():
    state["mode"] = None
    state["draft"] = None
    state["targets"] = []
    state["group_names"] = []
    state["selected_targets"] = set()
    state["edit_id"] = None
    state["edit_group_id"] = None
    state["edit_admin_id"] = None
    state["new_group_id"] = None
    state["new_group_type"] = None
    state["new_admin_id"] = None
    state["pending_group_name"] = None
    state["pending_admin_name"] = None
    state["pending_admin_message_id"] = None
    state["schedule_message_id"] = None
    state["schedule_year"] = None
    state["schedule_month"] = None
    state["schedule_day"] = None
    state["schedule_hour"] = None
    state["schedule_minute"] = None
