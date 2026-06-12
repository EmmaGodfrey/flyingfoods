"""Run Week 3 index checks and EXPLAIN ANALYZE for stock movement queries."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from textwrap import indent

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import engine


INDEX_CHECK_SQL = text(
    """
    SELECT indexname
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename = 'stock_movements'
      AND indexname IN (
          'ix_stock_movements_product_id',
          'ix_stock_movements_branch_id',
          'ix_stock_movements_product_branch'
      )
    ORDER BY indexname
    """
)

EXPLAIN_SQL = text(
    """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
    SELECT product_id, SUM(qty)
    FROM stock_movements
    WHERE branch_id = :branch_id
    GROUP BY product_id
    """
)


async def main() -> None:
    async with engine.begin() as conn:
        print("=== Week 3 Index Presence Check ===")
        index_rows = (await conn.execute(INDEX_CHECK_SQL)).scalars().all()
        for index_name in index_rows:
            print(f"- {index_name}")

        missing = {
            "ix_stock_movements_product_id",
            "ix_stock_movements_branch_id",
            "ix_stock_movements_product_branch",
        } - set(index_rows)
        if missing:
            print("Missing indexes:")
            for index_name in sorted(missing):
                print(f"- {index_name}")

        print("\n=== EXPLAIN ANALYZE (stock by branch) ===")
        plan_rows = (await conn.execute(EXPLAIN_SQL, {"branch_id": 1})).scalars().all()
        print(indent("\n".join(plan_rows), "  "))


if __name__ == "__main__":
    asyncio.run(main())
