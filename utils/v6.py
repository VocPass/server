def parse_curriculum(api_json):
    """
    將 cs.ray-tw.com /api/public/user-info 回傳轉成與其他版本一致的課表物件
    （科目名稱 -> { count, schedule }）。
    """
    if not isinstance(api_json, dict):
        return None, "Invalid response."

    if api_json.get("error"):
        return None, str(api_json["error"])

    if not api_json.get("success"):
        return None, str(api_json.get("error", "Request failed."))

    data = api_json.get("data") or {}
    week = data.get("currentWeek") or {}
    courses = week.get("courses")
    if courses is None:
        return {}, None

    return courses, None
