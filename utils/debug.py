import pocketbase


class Debug:
    def __init__(self, client: pocketbase.PocketBase | None):
        self.client = client

    def send_error(self, error_message, school, page):
        if self.client is None:
            return

        try:
            self.client.collection("debug").create(
                {"error": error_message, "school": school, "page": page}
            )
        except Exception:
            return
