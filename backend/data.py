import enum
import typing
import aiohttp
import pydantic
import collections

class ScreenType(enum.StrEnum):
    STATS = "stats"
    COMPARISON = "comparison"
    SCOREBOARD = "scoreboard"

class Region(enum.StrEnum):
    NORTH_AMERICA = "na"
    EUROPE = "eu"
    LATIN_AMERICA = "latam"
    BRAZIL = "br"
    ASIA_PACIFIC = "ap"
    KOREA = "kr"
    PUBLIC_BETA_ENVIRONMENT = "pbe"

class Player(pydantic.BaseModel):
    name: str
    agent: str
    acs: int
    kills: int
    deaths: int
    assists: int
    first_kills: int
    total_damage: int

class Team(pydantic.BaseModel):
    score: int
    players: list[Player]
    thrifties: int
    post_plants: tuple[int, int]
    clutches: int

class Scoreboard(pydantic.BaseModel):
    type: typing.Literal[ScreenType.SCOREBOARD] = ScreenType.SCOREBOARD
    map_name: str
    total_rounds: int
    team_blue: Team
    team_red: Team

class DataLoader:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: aiohttp.ClientSession | None = None

    @property
    def client(self) -> aiohttp.ClientSession:
        if not self._client:
            self._client = aiohttp.ClientSession()

        return self._client

    async def fetch_match_data(self, region: Region, match_uuid: str) -> typing.Any:
        async with self.client.request(
            "GET",
            f"https://api.henrikdev.xyz/valorant/v4/match/{region.value}/{match_uuid}",
            headers={"Authorization": "HDEV-de097c2b-bc59-4f35-a19b-f9308d212407"},
        ) as r:
            r.raise_for_status()

            return await r.json()
        
    async def gather_data(self, screen_type: ScreenType, region: Region, match_uuid: str) -> Scoreboard:
        data = await self.fetch_match_data(region=region, match_uuid=match_uuid)

        map_name: str = data["data"]["metadata"]["map"]["name"].lower()

        teams: dict[str, typing.Any] = {}
        for team in data["data"]["teams"]:
            teams[team["team_id"].lower()] = team

        team_stats: dict[str, dict[str, int]] = {
            "blue": collections.defaultdict(int), 
            "red": collections.defaultdict(int)
        }
        for round in data["data"]["rounds"]:
            team = round["winning_team"].lower()
            if round["ceremony"] == "CeremonyThrifty":
                team_stats[team]["thrifty"] += 1
            elif round["ceremony"] == "CeremonyClutch":
                team_stats[team]["clutch"] += 1
            
            if round["plant"] is not None:
                plant_team = round["plant"]["player"]["team"].lower()
                winning_team = round["winning_team"].lower()

                team_stats[plant_team]["total_plants"] += 1
                if plant_team == winning_team:
                    team_stats[plant_team]["post_plants_won"] += 1

        first_kills: dict[str, int] = collections.defaultdict(int)

        kills: dict[int, list[typing.Any]] = collections.defaultdict(list)
        for kill in data["data"]["kills"]:
            kills[kill["round"]].append(kill)

        for round_kills in kills.values():
            round_kills = sorted(round_kills, key=lambda k: k["time_in_round_in_ms"])
            first_kill = round_kills[0]

            killer = first_kill["killer"]["puuid"]
            first_kills[killer] += 1

        players: dict[str, list[Player]] = {"red": [], "blue": []}
        for player in data["data"]["players"]:
            team_id = player["team_id"].lower()
            agent_name = player["agent"]["name"].lower()

            players[team_id].append(
                Player(
                    name=player["name"],
                    agent="kayo" if agent_name == "kay/o" else agent_name,
                    acs=int(player["stats"]["score"] / len(data["data"]["rounds"])),
                    kills=player["stats"]["kills"],
                    deaths=player["stats"]["deaths"],
                    assists=player["stats"]["assists"],
                    first_kills=first_kills[player["puuid"]],
                    total_damage=player["stats"]["damage"]["dealt"],
                )
            )

        return Scoreboard(
            map_name=map_name,
            total_rounds=len(data["data"]["rounds"]),
            team_blue=Team(
                score=teams["blue"]["rounds"]["won"],
                players=players["blue"],
                thrifties=team_stats["blue"]["thrifty"],
                clutches=team_stats["blue"]["clutch"],
                post_plants=(team_stats["blue"]["post_plants_won"], team_stats["blue"]["total_plants"]),
            ),
            team_red=Team(
                score=teams["red"]["rounds"]["won"],
                players=players["red"],
                thrifties=team_stats["red"]["thrifty"],
                clutches=team_stats["red"]["clutch"],
                post_plants=(team_stats["red"]["post_plants_won"], team_stats["red"]["total_plants"]),
            ),
        )
