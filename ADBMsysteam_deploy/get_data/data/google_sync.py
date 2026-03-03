from typing import List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class GoogleSheetSync:
    def __init__(
        self,
        sheet_id: str,
        sheet_range: str,
        credentials_path: str,
        overwrite: bool,
    ) -> None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self.service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        self.sheet_id = sheet_id
        self.range = sheet_range
        self.overwrite = overwrite

    def push_row(self, row: List[str]) -> None:
        body = {"values": [row]}
        if self.overwrite:
            # Update fixed range (e.g., overwrite header row + first data row)
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=self.range,
                valueInputOption="RAW",
                body=body,
            ).execute()
        else:
            # Append as new row
            self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=self.range,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()


def build_syncer(
    sheet_id: Optional[str],
    sheet_range: str,
    credentials_path: Optional[str],
    overwrite: bool,
) -> Optional[GoogleSheetSync]:
    if not (sheet_id and credentials_path):
        return None
    return GoogleSheetSync(sheet_id, sheet_range, credentials_path, overwrite)

