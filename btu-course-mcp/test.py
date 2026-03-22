import asyncio

from scrapers.lsf import get_module_info, get_schedule, search_courses


async def main() -> None:
    try:
        results = await search_courses("machine learning", "SoSe2025")
        print(f"Search results: {len(results)}")
        if results:
            print(results[0])
            if results[0].id:
                schedule = await get_schedule(results[0].id)
                print(f"Schedule: {schedule}")
            else:
                print("First course has no parsed ID; skipping schedule test.")

        module = await get_module_info("11255")
        print(f"Module: {module}")
    except Exception as exc:
        print(f"Test run failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
