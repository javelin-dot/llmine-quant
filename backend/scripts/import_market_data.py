"""Import research daily market bars from CSV or AKShare."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.session import AsyncSessionLocal
from app.services.market_data_import import MarketDataImportService


async def _run(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as session:
        service = MarketDataImportService(session)
        if args.source == "csv":
            result = await service.import_csv_file(
                Path(args.path),
                default_symbol=args.default_symbol,
                source_name="csv",
            )
        else:
            result = await service.import_akshare(
                symbols=args.symbols,
                start_date=args.start_date,
                end_date=args.end_date,
                adjust=args.adjust,
            )

    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="source", required=True)

    csv_parser = subparsers.add_parser("csv", help="Import a local CSV file")
    csv_parser.add_argument("path", help="CSV file path")
    csv_parser.add_argument("--default-symbol", help="Symbol to use when CSV has no symbol column")

    akshare_parser = subparsers.add_parser("akshare", help="Import via AKShare")
    akshare_parser.add_argument("--symbols", nargs="+", required=True, help="A-share symbols, e.g. 000001.SZ")
    akshare_parser.add_argument("--start-date", required=True, help="Start date, YYYY-MM-DD")
    akshare_parser.add_argument("--end-date", required=True, help="End date, YYYY-MM-DD")
    akshare_parser.add_argument("--adjust", default="qfq", help="AKShare adjust flag: qfq, hfq or empty")

    return parser


if __name__ == "__main__":
    asyncio.run(_run(_build_parser().parse_args()))
