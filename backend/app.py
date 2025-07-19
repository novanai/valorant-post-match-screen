from fastapi import FastAPI, Depends
from backend import data
import os


app = FastAPI()

async def get_loader():
    loader = data.DataLoader(os.environ["HENRIK_API_KEY"])
    try:
        yield loader
    finally:
        await loader.client.close()

@app.get("/screen/{screen_type}/{region}/{match_uuid}")
async def root(screen_type: data.ScreenType, region: data.Region, match_uuid: str, loader: data.DataLoader = Depends(get_loader)):
    scoreboard_data = await loader.gather_data(screen_type=screen_type, region=region, match_uuid=match_uuid)
    return scoreboard_data
