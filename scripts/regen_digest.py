import asyncio, traceback
async def regen():
    try:
        from app.db.session import async_session_factory
        from app.modules.research.digest_service import DigestService
        async with async_session_factory() as db:
            svc = DigestService(db)
            digest = await svc.generate_digest()
            await db.commit()
            ms = digest.market_summary or {}
            print(f"Sentiment: {digest.market_sentiment}")
            print(f"Trend: {ms.get('overall_trend')}")
            for idx in ms.get('indices',[]):
                print(f"  {idx['symbol']}: {idx.get('change_pct',0):+.2f}%")
            print(f"Gainers: {len(digest.top_gainers or [])}")
            print(f"Losers: {len(digest.top_losers or [])}")
            print(f"Breakouts: {len(digest.breakout_candidates or [])}")
    except Exception as e:
        traceback.print_exc()
asyncio.run(regen())
