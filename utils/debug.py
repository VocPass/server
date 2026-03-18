import pocketbase


class Debug:
    def __init__(self, client: pocketbase.PocketBase | None):
        self.client = client

    def send_error(self, error_message, school, page, status):
        if self.client is None:
            return

        try:
            r = self.client.collection("debug").create(
                {
                    "error_message": error_message,
                    "school": school,
                    "page": page,
                    "status": status,
                }
            )
            return r.id
        except Exception:
            return
