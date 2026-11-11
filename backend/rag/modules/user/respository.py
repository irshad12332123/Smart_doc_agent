from typing import Any, cast
from supabase import Client
def _get_single_row_from_supabase_where(
    select: list[str],
    where: list[Any],
    table: str,
    client: Client
):
    try:
        if not isinstance(select, list) or not isinstance(where, list):
            raise ValueError(
                "This helper expects lists for select and where."
            )

        if len(where) != 2:
            raise ValueError(
                "where must contain exactly [column, value]."
            )

        record = (
            client
            .table(table)
            .select(*select)
            .eq(*where)
            .single()
            .execute()
        )

        if record.data is None:
            raise ValueError("Could not get record from Supabase")

        return cast(dict[str, Any], record.data)

    except Exception as e:
        raise ValueError(
            f"Failed to fetch record from Supabase: {str(e)}"
        ) from e
