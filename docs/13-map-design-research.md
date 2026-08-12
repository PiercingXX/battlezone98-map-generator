# 13 — Map design research: what makes a BZ98R multiplayer map *good*

Research pass for teaching a map-generation agent to generate maps the BZ98R community will actually praise.
Companion to `docs/04-map-design-rules.md`, which holds the rules measured from the corpus.
This doc holds the *external evidence* for those rules and proposes new ones.

## How to read the confidence labels

Every substantive claim below carries one of:

- **[CONSENSUS]** — multiple independent community/official sources agree, or it is
  encoded in a competitive ruleset (tournament map pool, official manual).
- **[OPINION]** — one named person's stated view. Useful, not authoritative.
- **[OFFICIAL]** — from Rebellion/Activision shipped documentation.
- **[MEASURED]** — computed here from a snapshot of the reference corpus of community Workshop maps.
- **[INFERRED]** — my extrapolation. Not sourced. Treat as a hypothesis to playtest.

## Honest note on source thinness

**The BZ98R-specific map-design literature is thin.** There is no equivalent of
StarCraft's mapmaking manuals. What exists is: one official map-editor manual (mechanics,
almost no design advice), two or three community Steam guides (a few paragraphs of design
advice each), scattered forum threads, and — most usefully — *map reviews written by
players*, which state preferences in players' own words.

Two significant sources were unreachable during this pass:
- `bzforum.matesfamily.org` — **the domain no longer resolves.** The Wayback Machine has
  thousands of captured URLs under it but the availability API returned no snapshot for the
  specific map-making threads that still appear in search results (`t=1188`, `t=2305`, `t=96`).
  Its successor community forum, `battlezone1.org`, is live and was mined instead.
- `bzmaps.com` (The Battlezone Map Room) — returned HTTP 522 (origin down) on every attempt
  across the session. It is indexed by search engines and appears to host per-map metadata;
  **worth retrying later**, as it likely contains a large `Geysers:`/`Scrap:` dataset.

Because thread 1 is thin, this doc leans harder on threads 2 (what players praise, which is
well-evidenced) and 3/4 (transferable theory, clearly labelled as such).

---

# Thread 1 — Battlezone-specific map making

## 1.1 Hard engine constraints [OFFICIAL]

From the shipped map editor manual,
[BZ98Redux_MapEditorManual.pdf](https://cdn.akamai.steamstatic.com/steam/apps/301650/manuals/BZ98Redux_MapEditorManual.pdf?t=1579791137):

- Map dimensions "MUST be either 1280, 2560, 3840 or 5120" metres. "A battlezone zone is
  1280 meters by 1280 meters, so your map can be any multiple of 1280 in either direction.
  The max size of a battlezone map is 5x5 zones."
- "you must place at least 2 spawn-points or the maps won't load."
- `multdm` prefix = deathmatch, `multst` = strategy, `usrmsn` = single-player. The
  [Multi-Player Map Editor for Beginners](https://steamcommunity.com/sharedfiles/filedetails/?id=665881032)
  guide adds that "Once you create it, it can't be changed from one type to another."
- "For strategy maps you will also want to place Geysers and scrap, which are also found
  under the neutral map."
- Respawning powerups are placed as *paths* named e.g. `apammo_30_1`, where "The first
  number, 30, is the time between respawning, and the second number is sequential."
  **A respawn interval is therefore an explicit, tunable design parameter in DM maps.**
- The `.ini` carries `minPlayers` / `maxPlayers` / `gameType` (`D`/`K`/`S`).

**The `.des` description template is itself a statement of what matters.** The manual tells
map authors to fill in:

```
World:
Size:
Powerups
Geysers:
Scrap:
```

**[INFERRED]** Rebellion's own convention is that a strategy map is *summarised to players*
by its geyser count and scrap total. Those two numbers are the headline balance knobs, and a
generator should treat them as first-class outputs, not incidental side effects of placement.

### Terrain grid scale — a discrepancy worth resolving

The manual's `[Size]` appendix says terrain is "described in terms of 128x128 uniformly
spaced grids, called ZONES. Each grid covers 10m. Thus each zone covers 1280m x 1280m area."
The independent format documentation at
[battlezone.videoventure.org/format_terrain.html](https://battlezone.videoventure.org/format_terrain.html)
agrees: "128 by 128 zones of 10 by 10 meter grid cells."

`docs/04` works on a **5 m** grid. Both can be true if the `.hg2` heightmap is at double the
`.trn` zone resolution (256×256 per zone). **[INFERRED]** — flagging it because every
slope-based rule in `docs/04` depends on which cell size is real. Worth confirming against
`docs/01` before trusting absolute slope numbers.

## 1.2 The single best piece of BZ map-design advice found

From the community Steam guide
[Basic Mapmaking](https://steamcommunity.com/sharedfiles/filedetails?id=647966056).
**These quotes were verified verbatim against the raw page HTML**, not taken from a
summariser — an early automated read of this page returned a truncated version that omitted
the Map Layout section, so the text below was re-checked directly.

> "areas designed for base-building (geysers, flat ground) and areas designed for
> combat-only (rough terrain in the middle of two spawns)."

and

> "You want every player to have the same amount of scrap nearby when the game begins."

and

> "fair placement of scrap and geysers, access to certain parts of the map, and areas where
> you want there to be a lot of fighting."

The same section adds two more design statements:

> "Also keep in mind that **the center of the map is typically where most fights occur**."
> (deathmatch)

> "Also consider **the middle of the game and the end of it**, and where you want strategic
> vantage points, if at all." (strategy)

and, on map edges — corroborating `docs/04` Rule T4 from a different direction:

> "A common oversight in many maps is the terrain outside your map's playing field. On the
> radar, you'll see an ugly dropoff at the edge of the map, and players close enough can see it
> themselves. **Quality maps will remove this dropoff and blend it in with the playable map.**"

The two mechanisms given are `maketrn mapname.trn /e=nnnn` to set a background terrain height,
and `edge_path`, "the manually-set edge of your map … a diagonal line setting the boundaries of
your map, in a rectangular/square form." **[OFFICIAL-ish / CONSENSUS]** — the playable area is
explicitly expected to be *smaller than* the terrain extent, with blended surroundings.

**[CONSENSUS]** — the same base-vs-combat-zone split is echoed by the official manual's
build/economy separation and by the tournament map pool's character (§2.1). This is the
closest thing BZ98R has to a stated design doctrine: **a strategy map is a set of buildable
economic pockets connected by deliberately unbuildable combat terrain.**

Same guide, on traversability:

> "AI units will have a difficult time climbing up very steep terrain."
> "If you want terrain that players can build on, make sure to have your terrain be flat in those areas."

The [Complete Modding Reference Guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3538294667)
adds that the terrain editor's slope visualisation is "Blue=flat, White=steep" and warns of
"Terrain too steep for AI navigation (>45° slopes)". **[CONSENSUS]** on the 45° figure being
the practical AI-pathing ceiling.

The official manual also implicitly warns about micro-roughness — the Smoother tool exists to
"fix all the dips and spikes that may get the player stuck." **[OFFICIAL]** Spiky terrain
traps units; this is a named failure mode, not a cosmetic concern.

## 1.3 Hovercraft physics — what terrain the vehicles enjoy

**Everything in BZ98R hovers**, which is why terrain design here is unlike a wheeled RTS.
Per the official game manual
([BZ98R_Manual_GB.pdf](http://cdn.akamai.steamstatic.com/steam/apps/301650/manuals/BZ98R_Manual_GB.pdf?t=1461330226)):

> "When travelling around the worlds you will often encounter obstacles such as craters or
> hills that your vehicle will have difficulty traversing. Use the E key to use your
> vehicle's turbo thrusters to Jump. This capability works best when a forward motion key is
> also in use. **The greater your vehicle's forward momentum, the higher it will jump.**"

**[OFFICIAL]** — jump height is a function of forward speed. **[INFERRED, high confidence]**
this means a *run-up* is a terrain feature: a slope with clear approach length is a
qualitatively different object from the same slope in a confined space. Ramps and launch
lines are real BZ level-design vocabulary, not decoration.

Community descriptions of the movement model, from
[Combat Driving (Battlezone Wiki)](https://battlezone.fandom.com/wiki/Combat_Driving) and
contemporary discussion — "All vehicles in this game hover, allowing you to traverse even the
strangest of terrains"; players "jump-jet across gullies, exploiting momentum and natural
rock ramps"; high-jumping off a hill to shoot down at an opponent then flipping backwards to
keep aim. **[OPINION]/[CONSENSUS-ish]** — multiple players describe the same techniques.

**[INFERRED]** Design consequence: *vertical* separation is cheaper than horizontal
separation in BZ. A 30 m rise is not a wall — a fast vehicle with a run-up will clear a lot
of it. Terrain intended to actually block must be steep *and* wide, or it will be jumped.

## 1.4 Vehicle speeds and costs — the numbers travel-time rules need

From the official manual's vehicle stat blocks **[OFFICIAL]** and cross-checked against the
actual ODFs in the corpus snapshot **[MEASURED]**:

| Unit | `velocForward` (ODF) | Manual fwd | Turn |
|---|---|---|---|
| Scavenger | 15.0 | 15 m/s | 90°/s |
| Tank | 20.0 | 20 m/s | 90°/s |
| Rocket Tank | 25.0 (NSDF/CCA) | 25 m/s | 60°/s |
| Light Tank | 27.5 | — | — |
| Razor / Fighter | 30.0 | — | 120–150°/s |
| Walker | — | 8 m/s | 90°/s |
| Turret (deployed mobile) | — | 5.5 m/s | 90°/s |

**Important correction to a plausible assumption:** the brief in this project mentioned
"scout speed 60 m/s". The manual's 60 m/s is *flavour text* for the Razor —
"granting it speed bursts of up to 60 meters per second" — not a sustained speed. **No ODF in
the map corpus has `velocForward` above 45** (and 45 is `vvltnk`, a special unit; the
2000.0 entries are editor camera objects). **Travel-time rules should use 20–30 m/s, not 60.**

Build costs, from the corpus ODF snapshot **[MEASURED]**:

| Thing | `scrapCost` |
|---|---|
| Scavenger | 4 |
| Supply depot | 5 |
| Turret / Armory / Comm Tower / W-Power | 6 |
| Light Tank | 6 |
| Tank / Rocket Tank / Constructor / Barracks | 8 |

**[INFERRED]** A map's total scrap therefore converts almost directly into army size:
**~8 scrap ≈ one tank.** A 260-scrap map split 4 ways gives each player ~65 scrap ≈ 8 tanks
of *raw ground scrap* — everything beyond that must come from geyser income and from
recycling wreckage. That is why geyser count, not scrap count, sets the long-game ceiling.

## 1.5 Economy mechanics that constrain placement

- Recyclers must be deployed on a geyser to draw power; the
  [Beginner's Strategy Guide](https://battlezone.report/article/guide/beginners-strat-guide)
  describes the opening as Recycler → Constructor → Scavengers → Factory, recommends "at
  least five or six" Scavengers, and notes that scrap "about half a kilometer from our
  starting geyser" already imposes meaningful travel cost. **[OPINION]**, but it is the most
  cited modern beginner guide.
- Same guide: **"Height gives you an advantage while defending your base."** **[CONSENSUS]** —
  repeated across the beginner guide, forum strategy posts, and Battle Grounds map reviews
  (§2.3, "central high ground").
- Same guide: keep units "within 200 meters" of the Recycler for efficiency during a base
  move. **[OPINION]** — but it gives a concrete scale for what "a base pocket" means.
- [Tips & Strategies (Orlando C. Fernando, battlezone1.org)](https://battlezone1.org/viewtopic.php?f=29&t=147):
  "Recyclers, factories, and armory units require geysers. Constructors do not." and
  "Gun towers and comm towers require s-powers. Supply units, Hangars, barracks, and silos do
  not." **[OPINION]** — if accurate, *a base pocket needs more than one geyser to reach full
  tech*, which raises the floor on geysers-per-base considerably.
- Same source, on a real map: on **Corner Pocket**, "I highly recommend placing gun towers or
  turrets near your base since there is such a narrow chokepoint entrance." On **Purgatory**,
  "The vast areas of scrap are toward the middle ends of the map. So it will take quite a
  while for scavengers to retrieve considerable scrap." **[OPINION]** — but note both
  comments are about *map geometry driving strategy*, which is exactly the effect we want.
- Scrap is radar-limited: "There may only no scrap visible to your radar" — scrap outside
  radar range is effectively invisible until scouted. **[OPINION]** **[INFERRED]** consequence:
  scrap placed far from any base is discovered late and rewards scouting; scrap placed at the
  edge of a base's radar bubble is contested early.
- Respawning scrap is technically possible but,
  per [a Steam discussion](https://steamcommunity.com/app/301650/discussions/0/135512931350237822/),
  "respawning scrap is rarely done because most players don't like it." **[OPINION]** — one
  claim, but it points the same way as the tournament pool's finite economies. **The generator should
  not generate respawning scrap.**

---

# Thread 2 — What the community actually praises

This is the strongest evidence available, because it is players stating preferences directly.

## 2.1 The competitive map pool — the hardest consensus signal there is

The [Battlezone 98 2024 Strategy Tournament](https://steamcommunity.com/app/301650/discussions/0/4699035743124766488/)
ran on a pool of **11 community-voted maps**:

> "Bio-Metal Run, Blast Chamber, Canyon Madness, Channels, Decimation Valley, Felix Ganymede,
> Grizzly Gulch, Hills of War, Oasis, Nitrogen, Par 3"

with standardised settings: **"3 lives, barracks on, sat on, sniper on, splinter off"**,
map picks and vetoes per game, Bo3 escalating to Bo7 in finals. The
[2021 tournament](https://steamcommunity.com/app/301650/discussions/0/3011186219287886085/)
used a dedicated `BZT 18` tournament map pack with SYNC ON, 3 lives, comm sat on, barracks on,
sniper on, splinter off, and up to three vetoes.

**[CONSENSUS — the strongest in this document.]** Nine of the eleven 2024 pool maps are in the
map corpus, so I computed what a competitively-endorsed map looks like versus the rest of the
corpus. **[MEASURED]**:

| Statistic | 2024 tournament pool (n=9) | Rest of corpus (n=26) |
|---|---|---|
| Map size (median) | **3840 m** | 2560 m |
| Map size (range) | 2560 – 5120 m | **1280** – 5120 m |
| Geysers (median) | 17 | 16 |
| Scrap total (median) | **260** | 280 |
| Strategy player slots (median) | 4 | 3 |
| **Geysers per player** (median) | **5.0** (range 4.0 – 10.0) | 6.0 (range 3.0 – 12.0) |
| **Scrap per player** (median) | **70** (range 59 – 140) | 100 (range 31 – 200) |
| Geysers / km² (median) | **1.22** | 1.53 |
| Scrap / km² (median) | **19.0** | 32.0 |

Per-map detail for the pool:

| Map | Size | S slots | Geysers | Scrap | gey/pl | scrap/pl |
|---|---|---|---|---|---|---|
| Oasis | 2560 | 4 | 19 | 260 | 4.8 | 65 |
| Grizzly Gulch | 2560 | 2 | 8 | 280 | 4.0 | 140 |
| Channels | 5120 | 2 | 12 | 200 | 6.0 | 100 |
| Hills of War | 3840 | 4 | 16 | 280 | 4.0 | 70 |
| Blast Chamber | 5120 | 4 | 24 | 260 | 6.0 | 65 |
| Canyon Madness | 5120 | 4 | 40 | 280 | 10.0 | 70 |
| Nitrogen | 2560 | 4 | 17 | 235 | 4.2 | 59 |
| Bio-Metal Run | 3840 | 4 | 20 | 400 | 5.0 | 100 |
| Par 3 | 5120 | 3 | 16 | 250 | 5.3 | 83 |

Three readings, all **[INFERRED]** from the measured split but well-supported:

1. **Competitive maps are economically tighter than the corpus average.** Median scrap per
   player 70 vs 100; scrap density 19/km² vs 32/km². Scarcity produces contest. The two
   corpus maps with the most extreme scrap-per-player (Sidewinder at 200, Grizzly Gulch at
   140) — only the second made the pool, and it is a 2-player map where 140 each is the whole
   economy.
2. **No 1280 m map is in the pool, and the median is 3840 m.** The single 1280 m corpus map
   (Moon War) is absent. Competitive play wants room.
3. **Geysers per player clusters tightly at 4–6.** Eight of nine pool maps sit in 4.0–6.0;
   Canyon Madness at 10.0 is the outlier and it is also the largest map with the most geysers
   (40). **This is a much tighter band than `docs/04` Rule E1's density-based framing**, and
   per-player is arguably the more meaningful unit.

## 2.2 What players praise, in their own words — strategy maps

The [Battle Grounds strategy map collection](https://steamcommunity.com/sharedfiles/filedetails/?id=663094672)
carries per-map reviews by the Battle Grounds review team (Toni Chaffin, Jason L'Hirondelle)
and the Heracles Brigade. Recurring praise:

- **The Third Force** — design focused on **"central high ground"** control; "Lots of scrap
  and enough geysers to keep a good intense battle."
- **Bunker Hill** — "ridge with defensive positions"; notes that the high ground "prevents
  gun tower placement at bases" — i.e. terrain that *denies* a defensive option is
  interesting, not broken.
- **Highland Siege** — praised specifically for its **"base layouts"**; "balanced for multiple
  playthroughs."
- **Mimas** — "Long strategic battles" with hill/mountain ranges.
- **Frozen Dead** — mountainous terrain "suitable for ambushes and long engagements",
  "designed for strategy minded players".
- **Canyon Lands** — requires "planning" and hit-and-run tactics.
- **Passages** — 4-player corner starts, "winding AI paths" with "player-accessible shortcuts
  between bases" — **asymmetric route quality between AI and human is treated as a feature.**

Recurring *criticism*, which is more useful:

- **Clash of Titans** — "Shortage of scrap with more than two players."
- **Canyon Lands** — "Potentially insufficient scrap for large multiplayer battles."
- **PAC-MAN!** — evenly distributed scrap but "possibly undersized for 4 players."
- **Fortress Io** — "Complex layout with lava features causes AI pathfinding issues."
- **The Final Hope** — "AI performs poorly; player-versus-player focused."

**[CONSENSUS]** Two failure modes dominate the criticism: **economy that does not scale with
player count**, and **layouts the AI cannot path through.** Both are directly checkable by a
generator.

## 2.3 What players praise — a modern, well-documented example

[Cothonian's map topic on battlezone1.org](https://battlezone1.org/cothonian-s-map-topic-t3225.html)
is the single most useful thread found, because it pairs stated map statistics with player
reactions.

**Rockslide** — "a medium-large sized map that is fairly open with an abundance of scrap
(26 Geysers, 295 scrap)". Reactions:

> Rosario, 5/5: "I really liked the idea of it having a **huge hill to capture and form a base
> on, with attackers from lower down**. It created a very different and unique strategy experience."

> Faner: "u run out of scrap for few seconds only not much its...just.... perfect"

> nolbp: "We tried a recycle war on it and it was above amazing"

The author's own criticism of his map:

> "Do to an error on my part it may be a bit **too easy to base camp**, so have a bunch of
> howitzers at the ready to break enemy lines."

**Mercy Hills** — "a very large map with plenty of scrap and many remote geysers (400 scrap,
29 geysers)". Author's own advice: "take your base with you, or it will take forever to get
reinforcements to where you need them." Reaction:

> Sporkinator: "Tried this map, it's HUGE. Cothonian said he might decide to make it smaller."

**[OPINION]** individually, but the pattern is coherent and matches §2.1: a *praised* map has
one legible dominant landform to fight over, an economy that runs *nearly* dry (Faner's "run
out of scrap for few seconds only ... perfect" is a precise description of correct scarcity),
and a size where reinforcements arrive in time. A *criticised* map is too big to reinforce, or
lets one player camp the other's base.

## 2.4 What players praise — deathmatch maps

The [Battle Grounds deathmatch collection](https://steamcommunity.com/workshop/filedetails/?id=668324314)
has 36 reviewed maps. This is the richest vocabulary sample in the whole research pass.
The recurring positive vocabulary:

- **Several distinct fight areas, not one blob.** "Four distinct playing areas surrounding a
  central hub" (Q4RaceTZ); "Several main fight areas" (Dream Land); "Four main play areas"
  (Ridge of Doom); "number of small battle areas and some elevated areas" (Rampage!);
  "Play not confined to single spot" (Aftermath).
- **Powerups placed at risk, not scattered.** "Powerups are in hard to get places so some
  planning will be required" (Ancients); "**Harder-to-reach power-ups offer better quality**"
  (Q4RaceTZ); "Extremely well designed. Few play areas but **power-ups are not scattered
  everywhere**" (Deadly Ground). This is arena-FPS item-control doctrine, arrived at
  independently by BZ players — see Thread 3.
- **Cover and hiding places.** "Lots of places to hide" (Eight Corners); "Enough powerups and
  hiding places for a good struggle" (Carnival).
- **Terrain that reads as a place.** "Map resembles old castles. ... Good attention to terrain
  detail" (Ancients); "Custom textures make the level look like an old dark complex. Great
  attention to art and detail" (Complex); "Very original design full of terrain features.
  Actual volcano in middle with power-up inside" (Volcanos).
- **Verticality with cost.** "Elevated areas can be tricky to get to in certain ship types.
  Reduces boredom" (Rampage!); "Each player starts at bottom of hill and works up to central
  peak" (Walker Arena).

The recurring *negative* vocabulary is the more valuable half:

- **"Based on flat surface with few natural obstructions for cover"** (Rave Zone).
- **"Landscape a little flat in places"** (Ridge of Doom).
- **"Has 'average' written all over it. Nothing special ... Lacks a final punch aside from the
  gigantic mountain in middle"** (The Hills).
- **"Symmetrically based map focusing around a center spike ... Very few hiding places. Not a
  map for the amateur against the pro"** (King Flanker) — symmetry plus no cover is called out
  as making the map *skill-punishing rather than interesting*.
- **"Plenty of powerups and weapons but hard to find because of confusing terrain"** (Call of
  the Wild) — legibility failure named explicitly.
- **"Textures are a little bland"** (Strike at the Heart); "though variety could be better in
  areas" (Drive-In).
- **"Map is a bit on the large side for a DM map"** (Carnival); "Very big and should be played
  with maximum number of players" (Battlefield) — size/player-count mismatch again.

**[CONSENSUS]** across 36 reviews: flatness, blandness, poor cover, and illegible terrain are
the named failure modes. Multiple distinct arenas, risk-placed items, and memorable landmarks
are the named virtues.

## 2.4b Named "best map" opinions, and one that corroborates the pool

A long-standing community strategy write-up reposted in
[the 2003 Strategy Guide thread](https://steamcommunity.com/app/301650/discussions/0/360671583803223925/)
covers three stock strategy maps and says of one:

> **Canyon Madness** — "probably the best strategy map that I have seen and definitely the best
> to learn on."

**[OPINION]**, but noteworthy: Canyon Madness is *also* in the 2024 community-voted tournament
pool (§2.1). Two independent signals, ~20 years apart, agree. **[CONSENSUS]** by convergence.

The same guide yields two design lessons that are unusually concrete:

- **Central geysers are deliberately scrap-poor.** On **Corners**: "Never set Recycler in the
  center set of geysers at the beginning of the game. **The lack of scrap collection will
  automatically set you behind.**" **[INFERRED, and this is a genuinely good idea]** — the
  contested centre offers *power* (geysers) but not *income* (scrap), so it cannot simply be
  squatted in the opening. It becomes a mid-game objective rather than an opening one. This
  decouples "where the geysers are" from "where the scrap is", which is a lever `docs/04`
  does not currently use.
- **Total map lockdown is achievable and is a real risk.** "On 'Corners,' I have literally kept
  people in their fort by taking all surrounding grounds. If you take the corners to the left
  and right of your opponent's side, winning is probability, not a certainty." Same family of
  failure as Rockslide's base-camp problem (§2.3). **[OPINION]**
- **The community invented a social anti-rush rule because maps did not enforce one.** The same
  guide's etiquette section: "**No Rec-rush first 5 min in game** when opponent's Recycler is
  deployed at nearest geyser(s) from spawn… (**3 minutes is generally acceptable.** -DREDD-)".
  **[OPINION]** **[INFERRED]** — this is direct evidence that BZ maps historically had *too
  short* an effective rush distance, and it is the strongest argument in the whole document for
  treating base-to-base travel time as a first-class generator parameter (G3).
- **Spawn-camping is named as a reason not to build at your spawn:** "if you set up where you
  spawn and your fort is attacked, and also you are killed in that area, when you re-spawn it
  is fairly certain that you will be killed again by the battling Tanks."
- On **Ice-Ice**: "Most players don't realize that they do not normally get all the scrap from
  their side" — scrap at the far end of a home gully goes uncollected. **[INFERRED]** economy
  placed beyond a base's natural working radius is *effectively not economy* unless the player
  actively extends to it; it should be counted as contested or expansion economy, not home
  economy, in fairness calculations.

## 2.5 Which map packs are considered best

- [battlezone.report's workshop round-up](https://battlezone.report/article/news/workshop-rundown-new-year)
  on the Omega Squadron map packs: **"These are some of the most organic and well-designed
  maps Battlezone has ever seen."** **[OPINION]**, but note the operative praise word is
  ***organic*** — which is precisely the quality Thread 4 is about.
- In the Steam thread
  [Multiplayer, recommended maps](https://steamcommunity.com/app/301650/discussions/0/135507548128104450/):
  Stinger calls Battlegrounds "almost essential for your continued online survival"; Jowsense
  names Omega Squadron and "the World/Planet maps" as favourites; DustRider values terrains
  "that are not in the original game" and says "Ceres looks the best!". Players in that thread
  favour maps with distinctive visual identity — while noting aesthetics must not cost
  playability. **[OPINION]**, consistent across several posters.

## 2.6 Asymmetry is acceptable if it is compensated

[Mr. Spock's tutorial for Theater o' Pain](https://battlezone1.org/map-tutorial-theater-o-pain-t44.html)
describes a deliberately asymmetric map: four scrap fields of 40/60/100/160 plus two
geyser-plus-scrap clusters of 20 each.

> "player on the north has initial scrap closer to him ... but in general, he has less scrap
> in his vicinity."
> "player on the north has to be more aggressive (offensive) cause he has less scrap in his vicinity."

**[OPINION]** — but a valuable one. Asymmetry here is not a bug; it *assigns a role*. The map
is described as "a 4 player map, but mostly played with just 2, because even then it is a
quick map which lasts up to 30 mins" — **a stated target match length of ≤30 minutes.**

(Note: the corpus `.des` for Theater O' Pain reports 200 scrap / 24 geysers, whereas
Mr. Spock's tutorial describes 400 scrap. Different version, or `.des` scrap is a different
quantity from summed field values. **Flagging as an open question** — it matters for whether
the corpus `scrap` column is comparable to the numbers map authors quote.)

---

# Thread 3 — Transferable theory from adjacent genres

Two bodies of theory transfer. **StarCraft** theory governs the *commander* half of BZ
(expansion pacing, chokes, rush distance). **Arena-FPS item theory** governs the *pilot* half
(control loops over contested resources, risk/reward placement, recovery zones). BZ is
genuinely both, so both apply — and where they conflict, that conflict is real and has to be
resolved deliberately (§3.4).

## 3.1 StarCraft — rush distance, size, and expansion pacing

### Rush distance is a *binned* design parameter, stated in seconds

The [Team Liquid Map Contest #18 ruleset](https://tl.net/forum/starcraft-2/610110-team-liquid-map-contest-18-presented-by-monster-energy)
gives explicit targets per archetype — measured main-ramp to main-ramp:

| Archetype | Rush distance | Playable area (editor units²) |
|---|---|---|
| **Rush** (favours early aggression) | **≤ 33 s** | 14,000–16,000 |
| **Standard** | **33–38 s** | 15,000–17,000 |
| **Macro** (favours defence/late game) | **38–43 s** | 16,000–18,000 |

Explicitly "a recommendation, not a hard restriction" — "large maps that play out aggressively
or small maps that promote long games will still be considered." **[CONSENSUS]** in the SC2
mapmaking community. The transferable idea is not the numbers but the *practice*: **rush
distance is a named, binned, up-front design parameter, not an emergent property.**

Actual 1v1 SC2 map dimensions cluster at 124–144 cells square (~140² typical), with 4-player
and team maps at ~160² — e.g. [Ley Lines](https://liquipedia.net/starcraft2/Ley_Lines) 146×126
rush 36 s; [Amphion LE](https://liquipedia.net/starcraft2/Amphion_LE) 140×140 rush 36 s;
[Whirlwind](https://liquipedia.net/starcraft2/Whirlwind) 160×160 4-player;
[High Ground](https://liquipedia.net/starcraft2/High_Ground) 164×156 8-player.
**[MEASURED, external]** — 4-player maps are ~1.3× the *area* of 1v1 maps, not 2×.

**Playable-area fraction:** Shattered Temple is "160 x 160, with playable map size of
132x134" — **~69% playable**, the rest border ([SC2Mapster Melee Mapping Survival
Guide](https://www.sc2mapster.com/forums/development/melee-development/165747-the-melee-mapping-survival-guide)).
This corroborates `docs/04` Rule T4 (ring the basin with impassable terrain) and puts a number
on it.

**Measurement methodology worth copying** from
[Rush Distance Comparisons](https://tl.net/forum/starcraft-2/124510-rush-distance-comparisons):
spawn a worker, order it to the opposing start, subtract timestamps. The author notes his
map-analysis approximation "only considers 16 possible directions" and is "within a few
percent." He measures asymmetric spawn pairs **clockwise and counter-clockwise separately**
and reports the disparity as a percentage of the longer distance. Desert Oasis is criticised
for "a whopping 36% further rush distance than the 2nd longest" — **[INFERRED]** the community
treats a >~35% spawn-pair disparity as pathological.

He also warns that **air distance and ground distance diverge** on some maps. **[INFERRED]**
Highly relevant to BZ: hover vehicles can jump terrain that a pathfinder routes around, so
the generator should check straight-line *and* path distance and flag large ratios.

### The safe→contested expansion gradient

From [SC2 map templates — ground rules](https://tl.net/forum/starcraft-2/297518-sc2-map-templates-ground-rules),
the canonical ordering of a playable map:

> 1. Safe, one-entrance, FFE-able natural. Untankable.
> 2. Relatively safe, nearby thirds
> 3. **Fourth is contested and difficult to consistently reinforce**
> 4. Good balance of chokes and open spaces — generally we want to see open spaces in the middle.
> 5. Not obnoxiously small/large and sinuous

So roughly **3 safe expansions (main, natural, third) then contested**. Modern 1v1 maps carry
**12–16 total bases, i.e. 6–8 per player** (TLMC #18 submissions). The same author suggests
"Out of a pool of 9 maps, it would be good to have 5 maps that adhere to this standard" —
**[INFERRED]** ~55% of a *map pack* should be the standard archetype and the rest outliers,
which is directly applicable to shipping ten maps as a set.

**High-value expansions must carry risk.** TLMC #18: "When deciding to utilize a gold base,
make sure there is some sort of risk associated with them." The SC2Mapster guide puts rich
minerals "towards the center of the map, making the rich veins harder to defend."
**[CONSENSUS]** — and identical to the arena-FPS rule in §3.2.

**The turtling trap** — the sharpest single idea found in thread 3, from an OmniSkeptic map
description in TLMC #18:

> "Any base layout which wants many possible thirds must have all those bases close to the
> player's natural so that they are all INDIVIDUALLY safe to take. When taken COLLECTIVELY
> however, **turtling becomes strong since you have a cluster of close bases.** In order to
> discourage camping on such a cluster, the most central base to the cluster … contains 8 900
> mineral fields (**−33% minerals** compared to normal) without adjustment to the income,
> keeping it a solid option … but prevents it from becoming a prolonged point of attention."

**[OPINION]** but mechanically elegant: **devalue the anchor of a defensible cluster rather
than moving it.** Directly portable to scrap-field sizing.

### Chokepoints — width, length, and count

[Liquipedia](https://liquipedia.net/starcraft2/Choke_Point): controlling a choke "gives you a
strategic advantage since you can get a better concave… a smaller army can hold off a much
larger army that has to move through a choke."

Concrete widths from
[Map Design: Understanding Choke Points](https://tl.net/forum/sc2-maps/319776-map-design-understanding-choke-points),
measured in 3×3-cell building widths: natural choke "3 or 4 gates"; choke to third "4–6 gates
wide"; "**3 is a pretty good minimum for choke width**"; two-wide chokes are criticised as
"too skinny."

**Three distinct "too chokey" failure modes** (RumbleBadger), ranked by how common they are:
1. Too many chokes,
2. Chokes too skinny (~2 buildings),
3. **Chokes too long** — "The chokes may be an acceptable width (3 gateways) but they are too
   long and thus a zerg player is very underpowered moving through that region."

with #3 and #1 tied as most common. **[OPINION]**, but **choke *length* being as important as
width is the most under-appreciated point in the thread**, and it maps straight onto BZ
canyons, which are naturally long.

Why chokes must not be ubiquitous: "If chokes are too frequent, it's too easy to stop an enemy
army moving through… players can always kite the [enemy] army to the choke." And the framing
that unifies this with the FPS literature: "I would actually rather use the term **'paths being
not connected enough'** to describe this matter."

**Open space belongs immediately behind a choke**, as the defender's fighting room: "Open area
should be right after the choke to bases." And "The middle should be open enough for a 200
[supply] deathball to cross without losing the shape of a circle."

### Ramps, high ground, and defender's advantage

Ramps beat flat chokes because they add a *vision* asymmetry
([Liquipedia](https://liquipedia.net/starcraft2/High_Ground_and_Low_Ground)): units on high
ground see low ground; units on low ground do not see high ground, and have reduced vision up
a ramp. "Elevated ramps make defending early game aggression easier in almost every match up…
Because ramps increase the defender's advantage which leads to longer games… Longer games
require more skill, so the better player will win more often."

The counter-example is instructive: Tal'darim Altar's *flat* main choke meant "you can't block
the choke with 1 force field… if you have an inferior force," collapsing the metagame.

**The most important transfer** comes from the Brood War comparison in the ground-rules thread:
BW had "a real high ground advantage in the form of a punishing miss chance… defending
territory was considerably easier in BW than in SC2." Conclusion: **a game with weaker inherent
defender's advantage needs more defensive terrain baked into the map.**

**[INFERRED, and important]** BZ98R has **no fog of war on high ground, no miss chance, and
direct first-person fire** — its inherent defender's advantage is weak, and it is further
weakened by hover vehicles' ability to jump terrain. **Therefore BZ maps need *more*
terrain-based defensibility around Recycler pockets than an SC2 map would.** This independently
agrees with the BZ community's own "height gives you an advantage while defending your base"
(§1.5).

### Symmetry and "creative vs balanced"

SC2's position is pro-symmetry: a symmetric map "offers the same advantages and disadvantages
… to both or all players," and rotational balance "goes without saying"
(SC2Mapster guide; TL ground rules). **[CONSENSUS]** within RTS.

MorroW's essay
[How to create the perfect map in StarCraft 2](https://tl.net/forum/starcraft-2/507315-how-to-create-the-perfect-map-in-starcraft-2)
names both failure modes precisely:

> "Creating a balanced map that's not new in any way is very simple… this kind of map is 'good'
> but not great."
> "To create a map that's new-thinking or 'creative' is also very simple… and disregard any
> imbalance it might have. A map like this doesn't qualify as 'good'."

His Expedition Lost case study is a warning against over-constraining: "The map itself was
creative but it encouraged the players themselves to be the opposite… When the game was in the
countdown I already knew as an observer what both players would do." The target: **"a creative
map is a map that encourages unorthodox strategies but not to such a degree that everybody
would be forced to do them."** **[OPINION]**, but it is the best articulation found of the bar
the generator's output has to clear: *balanced is table stakes; the map must also leave options open.*

### Blizzard's own auto-checkable defect list

From [Mastering Mapmaking: Part Two](https://news.blizzard.com/en-us/article/20521249/mastering-mapmaking-part-two)
(mirrored at [SC2Mapster/blizzard-tutorials](https://github.com/SC2Mapster/blizzard-tutorials/blob/master/docs/Classic_Tutorials/04_Misc/mastering-mapmaking.md)):

- **No free-safety pockets** — no spot where a unit "cannot be attacked by melee units."
- **No cheap total wall-off** — "Two Pylons should never yield a complete wall."
- **Resource-line pathing** — "Mineral lines should always have some pathing behind them, as
  well as spaces between any Vespene geysers." **[INFERRED]** direct BZ translation: **leave
  navigable space behind and inside every scrap field and around every geyser**, or scavengers
  and raiders both jam.
- **No unit traps** — "air pathing blockers… placed next to each other, creating an area where
  air units get stuck." Same family as `docs/04` C2.
- Elevation must be *readable*: cliff textures should have varied colour values because "this
  helps players know they are approaching high or low levels of terrain." **[OFFICIAL, SC2]** —
  and it agrees with thread 4's legibility material (§4.4).

Framing quote, [Liquipedia Maps](https://liquipedia.net/starcraft2/Maps): "Brood War was not
balanced by Blizzard's changing any unit statistics, but rather primarily by map design."

## 3.2 Arena FPS — item control loops

This is the richer half for BZ, because BZ's economy is *renewable throughput on the ground*
that pilots physically drive to — structurally closer to Quake armor than to SC2 minerals.

The two canonical documents are
[Pat Howard's Q3A Item Placement Guide](https://www.quake3world.com/forum/viewtopic.php?t=50729)
and
[wviperw's Competitive Level Design Guide (CPMA)](http://cpma-news.org/guides/content/leveldesign).

### Timers vs travel time

Verified against id's own source
([g_items.c](https://github.com/id-Software/Quake-III-Arena/blob/master/code/game/g_items.c)):
armor **25 s**, health **35 s**, ammo **40 s**, Mega Health **35 s**, powerups **120 s**.

The design consequence of *desynchronised* timers is the key idea:

> "due to its longer timer the MH will occasionally spawn around the same time as the RA.
> Since the up player can't be in two places at the same time, this makes the MH more of a
> toss-up item and creates chances for the down player to steal an advantage."

and, designed in deliberately on Furious Heights: an MH and a YA placed very close together
"looks imbalanced at first, but due to the **fifteen second delay between their timers**,
players don't usually pick them up together and the down player can still get at least one
armor."

**[INFERRED]** **Two resources that are physically adjacent but temporally offset are not the
same as one resource.** BZ has this primitive already — DM powerup paths carry an explicit
per-item respawn interval (§1.1). For strategy maps the analogue is geyser *income rate* and
scrap-field *depletion time*: staggering when clusters become worth revisiting does the same
work as spacing them apart.

### Number of contestable sites is the anti-snowball dial

Howard's central law:

> "The general trend is this: **the more armors you have in a map, the harder it will be for
> one player to dominate all of them.**"
> "Remember that **complexity and domination have an inverse relationship.**"

Concretely, for a duel map:

| Majors | Verdict |
|---|---|
| **3** | "generally looked down upon … due to their lack of complexity and ease of domination"; leads to games "where the down player is forced to prematurely 'gg'." |
| **4** | "**the most popular choice** … isn't overly complex and still allows for some domination, but the fourth armor gives the down player something to recover with." |
| **5** | "even easier … for the down player to recover." Practical ceiling. |

Tuning rule: "if your map is too easy to dominate … add more armors … If your map has
domination issues regardless of the armor loadout, I would suggest **making the heavier armors
harder to get to**." **[CONSENSUS]** in competitive Quake mapping.

**[INFERRED — and this is the single most valuable transfer in the document]** For BZ, the
number of *independently contestable economic sites* — not the total scrap — is the
anti-snowball dial. **Two contested sites means whoever wins the first fight snowballs; four to
five means the losing commander always has one he can still hold.** This is a different and
more useful framing than "contested fraction" (`docs/04` E5, §G6a), and it should be measured
as a *count*, not a percentage.

### Risk/reward, and the recovery zone

wviperw, stated as a law:

> "The danger in grabbing an armor should match its respective armor… Note: 'dangerous' doesn't
> necessarily include world dangers like lava or the void. **The danger can also be in relation
> to the other player.** For example, if an armor is out in the open on a bottom floor, the
> player must expose himself to possible attacks from a number of angles."

Supporting rules: "Spread the armor out as much as possible"; "There should be interesting
architecture and sufficient verticality surrounding most armor locations… players need
different angles and levels to attack from."

But — crucially — **items should not be spread *evenly***:

> "'Lost World' seems to be a bit lopsided at first since there is a whole region at the top of
> the diagram that is absent of armor. **This turns out to be an important area for the down
> player to escape from the action**… **some of the best maps don't place the armors for maximal
> coverage, instead they distribute armor in an uneven way to further specialize certain areas.**"

wviperw agrees for health: "place smaller amounts of health in 'down' areas. Just don't make it
a kamikaze run for the down player to heal up."

**[CONSENSUS]** across both guides, and it has a direct SC2 analogue (the safe natural/third).
**Every map needs a low-value region where a losing player can rebuild unmolested.** `docs/04`
currently has no such rule, and a generator optimising for "fair, contested, evenly
distributed" will actively destroy it.

There is also a deliberate exception worth noting — a *defensible* major item as a comeback
anchor: "put an armor (specifically the RA) in an easily camp-able/defendable spot… give the
down player a chance to control the armor even with limited weaponry due to the chokepoints."

### Denial granularity

> "2x25h vs. 50h — With a 50h in there, players can deny their opponents health easier. With
> 2x25h, if the player has >75h, he can only take one of the 25h's, therefore leaving the other
> one for his opponent."

Howard: "The reason you don't want to overuse the 50-health bubble is because they are easy to
control. When a player scoops one up, he denies about a third of the map's normal health."

**[INFERRED]** **Many small scrap pieces are harder to deny than one large pool of equal total
value.** BZ already has `npscr1/2/3` and `sfield8`/`sfieldC` (values 1, 8, 10 — §1.4), so
granularity is an existing, free knob. Contested areas should use *many small* pieces; safe home
areas can use larger fields.

### Connectivity, loops, and the shortest-path rule

wviperw's fundamentals:

- **Flow:** "a map needs to have a **circular flow on the macro level**… a flow in which the
  player doesn't have to turn around and do a 180 all the time but instead can just run around
  the map in loops."
- **Dead ends:** "Generally, dead ends are a very, very bad thing."
- **Connectivity, both bounds:** "The more paths/openings a level has, the more connective it
  will probably be… **Just be careful not to make too many passages from one area to another,
  otherwise it turns into Swiss Cheese and loses the effectiveness of the layout.**"
- **Room-hall-room syndrome:** strict distinct passages between areas create "poor chokepoints
  and bad gameplay"; instead "create a continuously flowing map where rooms flow into other
  rooms." His fix replaces one stairway between two levels with **three** distinct routes.

And **the shortest-path rule**, which I would port most literally of anything in this document:

> "compare all the different paths between the RA and MH. You want to make sure there isn't one
> path which is the clear best choice. **The shortest path should be the most vulnerable**,
> otherwise players will take it all the time and nothing interesting will happen."

**[CONSENSUS by convergence]** — SC2 reaches the identical conclusion independently
(three paths, the direct central one passing the golds and the watchtower sightline;
§3.1). Two separate competitive communities, same rule.

### Spawns

Howard treats spawn placement as more important than health placement, because "the first
thirty seconds of the duel heavily influences who is in control … for the next several
minutes." The failure modes: "**put a spawn right next to the most important armor or
weapon**", or "**two spawns near each other with one at a clear advantage.**"

Concrete: "**around eight spawn points is a good ballpark number for any tourney map.** It's
not so high as to be confusing, but it's not so low that it's predictable," placed "in less
vulnerable areas … hallways and small rooms with minimal traffic."

**[INFERRED]** This corroborates `docs/04` B3's 14 DM spawns as reasonable for a larger,
higher-player-count map, and B4's no-line-of-sight-at-spawn rule.

### Sightlines determine item accessibility

> "consider that its effectiveness varies greatly based on how long the map's lines of sight
> are. In more confined maps, it's safe to make the RG a little more accessible. In more open
> maps, you'll want to make the RG less accessible to keep the map from becoming a rail arena."

Placement patterns: put a long-range weapon "where they are not immediately useful so that
players can't camp on them"; and "place key weapons **off the beaten path, but make sure they
can still be picked up at high speeds**" — cornering items "breaks up the flow of their
movement."

**[INFERRED]** Direct BZ translation: on an open map, put the contested economy where holding
it is *exposed*; on a canyon map you can afford to make it more accessible. **Sightline length
and economy accessibility are coupled parameters, not independent ones.** This is also the
answer to `docs/04` §6's worry that validators cannot tell "good sniping map" from "featureless
plain": a long sightline is good *if the map's valuable objects are placed to account for it*.

### Verticality: offset, don't stack

> "In the first design, the mapper has foolishly decided to put all three levels directly on
> top of each other… The second picture shows a better way… the mapper **offsets** the different
> levels so players can have much more contact with players on other levels than their own."

Why height is powerful — his taxonomy reads as a checklist of what a ridge grants a hover tank:
higher weapon utility (longer LOS, floor as splash backstop); more freedom of movement (can
always drop down); and cover (step back from the edge).

### Powerups don't belong in competitive maps

wviperw is categorical: quad/regen/invis/haste etc. "absolutely have NO place in a competitive
tourney map… whenever a player has a powerup, his opponent simply can run and hide until the
powerup is gone, therefore slowing up the game immensely." Howard agrees they are "too powerful
to be included in tourney maps." **[CONSENSUS]** in competitive Quake — relevant if BZ98R
strategy maps are ever tempted toward bonus-scrap events.

### Scale metrics (Quake units, for calibration method only)

wviperw's observed figures: walkways **128 units** wide (192 common), floor separation **~256
units**, atrium **1024 units**, wall thickness **64 units**. Howard's go-to chokepoint is a
**256 L × 128 W** hallway. The
[Level Design Book metrics chapter](https://book.leveldesignbook.com/process/blockout/metrics)
gives the general rule "The minimum hallway width should be **at least double the player
width**. Even then, it will feel a bit narrow" — and the necessary warning that "metrics may
give the illusion of infallible design laws… **You cannot measure your way to a good game
experience.**"

The genuinely transferable part is wviperw's *method*, not his numbers: he decompiled an
existing map he wanted to match in scale and measured floor separations, walkway widths and
jump distances.

## 3.3 Battlezone 2 / Combat Commander — thin, but two real data points

**[Honest assessment: this thread is thin.]** BZ2/BZCC mapping writing is overwhelmingly
*technical* (editor mechanics) rather than *theoretical*. The BZCC
[Basic Map Making Guide](https://steamcommunity.com/sharedfiles/filedetails/?id=1266690542)
covers height brushes, texture layers and team values, with the one composition rule "Never put
two textures next to each other on the same layer – you will end with sharp edges and corners"
and the advice to "Create a boundary wall around the map." No layout theory.

The exception is Horigan's
[BZ2 Level Editor FAQ v1.5](https://www.neoseeker.com/battlezone2/faqs/64241-battlezone-ii-level-editor.html),
which contains **the only quantitative scrap-placement recommendation found anywhere in the
Battlezone corpus**:

> "RECOMMENDATION: **always place some loose scrap on the map.** … **Place four to six pieces of
> scrap at five to nine locations around the map. No more than two or three of these scrap
> fields should be located near the human team base area.**"

**[OPINION — single source, and it is about AI behaviour (keeping scavengers from blocking the
Recycler) as much as balance.]** But **5–9 fields × 4–6 pieces, ≤2–3 near any one base** is a
usable, testable shape, and it is notably *fewer, chunkier* fields than a naive generator would
scatter.

Other structurally useful facts from the same document:

- **Building footprints:** large base buildings occupy **four grid squares**, mid-size two,
  small one. This is what "a base pocket must fit a production line" actually means
  dimensionally.
- **Exit clearance matters:** "Avoid locating the computer team base on the south side of the
  map. Computer team buildings are always oriented facing south… units emerging from the
  recycler and factory will have less difficulty moving out of the base. Otherwise, the
  recycler and factory can be an obstacle." **[INFERRED]** a base pocket needs *clearance in
  the direction buildings face*, not merely total area.
- **The engine's AI-authoring vocabulary treats scrap pools and chokepoints as the two
  categories of defensible terrain:** hold points are best placed at "locations near critical
  scrap pools or choke points"; turrets belong at "the computer team base area, scrap pools and
  choke points." **[INFERRED]** the game's own designers considered "scrap pool" and "choke" to
  be the same kind of object — a place worth standing on.
- **Blocked attack paths break the AI outright:** "Attacking units that get blocked by the
  terrain may cause the computer team to 'freeze'." Corroborates §2.2's AI-pathing complaints.
- **Elevated overlook positions are authored explicitly** — artillery points "should be placed
  on an elevated area near the computer team base," within mortar range of the target.
- **A concrete aggro radius:** "The safe distance for stock DLL maps is **300m**" — the range at
  which approaching an enemy Recycler flips the AI to siege. **[INFERRED]** a usable minimum
  separation between a base pocket and a neutral route.
- **Hovercraft ignore some terrain:** an attack path "may run over terrain that might not be
  accessible to non-hovercraft vehicles. Water for example is not an obstacle." Same lesson as
  §1.3 — hover mobility ≠ pathfinder mobility.

## 3.4 Cross-cutting synthesis, and the one real conflict

Six principles appear **independently in both** the RTS and arena-FPS literatures, which is the
strongest evidence available that they are real rather than genre folklore. **[CONSENSUS by
convergence]**:

1. **The shortest path between the two most valuable sites must be the most dangerous.**
   (Howard, §3.2 / SC2's exposed central route, §3.1.)
2. **The number of independently contestable resource sites is the anti-snowball dial.**
   (Howard's 3/4/5 armors / TLMC's 12–16 bases with a safe third and contested fourth.)
3. **Value must scale with exposure.** (wviperw's danger-matches-armor / TLMC's "risk
   associated with gold bases.")
4. **Reserve a low-value recovery zone.** (Lost World's armor-free region / the safe natural
   and third.)
5. **Chokes are good locally and bad globally.** Both reject the extremes — "paths being not
   connected enough" (SC2) vs "Swiss Cheese" and "room-hall-room syndrome" (Quake). Both land
   on **~3 routes between major areas, differentiated in length and safety.**
6. **Denial granularity beats total value.** (2×25h vs 50h / cutting an anchor base to −33%
   minerals rather than moving it.)

**The one genuine conflict — symmetry.** RTS theory wants it (equal starts are the definition
of fairness); arena-FPS theory forbids it. wviperw:

> "**Symmetry — Please, do not make your levels completely symmetric.** This effectively halves
> the gameplay of the level since there is now only half of the level which is unique. The only
> reason q3tourney2 can get away with being symmetrical is because it has an **asymmetric item
> placement**."

and on balance generally:

> "A perfectly balanced map would ultimately be pretty boring to play… On the other hand, a
> completely unbalanced map can also make for boring play in that the first player to gain
> control will keep control easily. **The ideal is a map in which there is enough unbalance to
> make it interesting yet not so much as to make it overwhelmingly controllable.**"

**[INFERRED — my proposed resolution]** The two are reconcilable because they are talking about
different parts of the map. **Mirror the base pockets and their start conditions exactly; let
the contested middle be feature-asymmetric.** This is q3tourney2's trick inverted, and it also
matches what the BZ corpus actually does — `docs/04` §5 already observes the corpus is "not
strictly mirror-symmetric … asymmetric terrain and balanced economy." It also matches
Theater o' Pain's compensated asymmetry (§2.6). **This resolves `docs/04` Rule S1's open choice
between the two options: do both, in different regions.**

---

# Thread 4 — Terrain that reads as designed, not as noise

This thread is well-sourced and has the most *numerically actionable* content in the document.

## 4.1 Why fractal/Perlin terrain reads as fake

The core failure is **statistical, not aesthetic: fBm is self-similar everywhere and real
terrain is not.** Per
[terrain-erosion-3-ways](https://github.com/dandrino/terrain-erosion-3-ways/blob/master/README.md),
real terrain's fractal structure is *emergent* from streams merging downhill; with fBm,
"once you've seen one patch of land, you've basically seen it all." That is exactly the
absence of landmark hierarchy.

[Génevaux et al., *Terrain Generation Using Procedural Models Based on Hydrology*](https://www.cs.purdue.edu/cgvlab/www/resources/papers/Genevaux-ACM_Trans_Graph-2013-Terrain_Generation_Using_Procedural_Models_Based_on_Hydrology.pdf)
(SIGGRAPH 2013) states it directly: "A key observation when looking at real terrains is that
their morphologies are structured around river networks. Those networks subdivide the terrain
into visual and clearly defined areas." Fractal methods "provide terrains that look
geologically fresh, whereas real terrains are usually affected by erosion and weathering" and
"often lack control over the placement of terrain features."

Cheap mitigations with sources:

- **Derivative-damped fBm.** [Inigo Quilez, *Advanced Value Noise*](https://iquilezles.org/articles/morenoise/)
  weights each octave by accumulated derivative — `a += b*n.x/(1.0+dot(d,d))` — damping
  high-frequency contribution where the surface is already steep, yielding "flat areas as well
  as more rough areas." One-line change to an fBm loop, and it produces *buildable flats for
  free*, which BZ specifically needs.
- **Spectral slope.** [Quilez, *fBm*](https://iquilezles.org/articles/fbm/) measured
  photographed mountain silhouettes at roughly **−9 dB/octave** (H=1, gain 0.5, lacunarity 2),
  arguing gain 0.5 is isotropic ("a mountain that is higher is also wider at its base by the
  same amount"). Empirical hobbyist measurement, not peer-reviewed. Geomorphology reports DEM
  spectra as 1/f^β with β up to ~2.8, and — importantly — **deviations from fractal scaling at
  fine scales because of real ridge–valley structure**
  ([arXiv 1607.03040](https://arxiv.org/pdf/1607.03040)). BZ's 5–10 m grid sits squarely in
  that non-fractal regime.
- **The oatmeal problem.** [Kate Compton, *So you want to build a generator*](https://galaxykate0.tumblr.com/post/139774965871/so-you-want-to-build-a-generator)
  distinguishes *perceptual differentiation* from *perceptual uniqueness*, and observes that
  "humans seem to like perceiving evidence of process and forces." Eroded terrain reads as
  designed largely because it visibly encodes a process. Cf. the standard cautionary example,
  [No Man's Sky as "18 Quintillion Bowls of Oatmeal"](https://www.vice.com/en/article/nz7d8q/no-mans-sky-review).

## 4.2 PTRM — a fitted human-perception metric with real numbers

[Rajasekaran et al., *PTRM: Perceived Terrain Realism Metrics*](https://arxiv.org/abs/1909.04610)
classified DEMs into the 10
[geomorphons](https://ui.adsabs.harvard.edu/abs/2013Geomo.182..147J/abstract) of Jasiewicz &
Stepinski (flat, summit, ridge, shoulder, spur, slope, hollow, footslope, valley, depression),
ran two Mechanical Turk 2AFC studies (3,750 pairwise observations / 70 subjects, then 22,500
views / 128 subjects) and regressed perceived realism on geomorphon frequencies (R² = 0.72,
all 10 coefficients p<0.01).

Correlation of each geomorphon's coverage with perceived realism:

| Geomorphon | r | | Geomorphon | r |
|---|---|---|---|---|
| Valley | **+0.66** | | Hollow | +0.22 |
| Ridge | **+0.64** | | Flat | −0.10 |
| Summit | +0.44 | | Footslope | −0.15 |
| Depression | +0.42 | | Shoulder | −0.17 |
| Spur | +0.33 | | Slope | **−0.65** |

Measured scores (0 = poor, 1 = realistic):

| Terrain | PTRM | | Terrain | PTRM |
|---|---|---|---|---|
| Real fluvial (Chichiltepec) | 0.86 | | **Synthetic fBm** | **0.27** |
| Real coastal (Gobi) | 0.77 | | **Synthetic Perlin** | **0.24** |
| Real aeolian (Moab) | 0.75 | | Synthetic thermal erosion | 0.22 |
| Real slope (Death Valley) | 0.66 | | **Synthetic ridged noise** | **0.18** |

**Plain noise scores 0.18–0.27 against real terrain's 0.66–0.86 (p<0.01, t=17.91).** The
mechanism: synthetic terrain is overwhelmingly classified as undifferentiated *slope* and
*shoulder* — the two most negatively-weighted classes — with almost no *valley*, *ridge*,
*summit* or *depression*. CycleGAN feature transfer confirmed causality both ways: synthetic
given real features rose 0.51 → 0.69; real given synthetic features fell 0.76 → 0.33. They
also report that real terrains' geomorphon distributions are broad and roughly normal while
synthetic ones are narrow and multi-modal — **"high variability in geomorphological features
is beneficial for perceived realism."**

**Critical caveat:** PTRM was computed on 512×512 patches at ~200 m/pixel (~100 km across).
A whole BZ map is roughly *one geomorphon* at that scale, so **the regression coefficients do
not transfer numerically.** What transfers is the qualitative target: compute geomorphons at a
support radius suited to our scale (say 50–150 m) and drive the mix away from
"slope/shoulder everywhere". GRASS GIS ships `r.geomorphon`.

## 4.3 Orometry — landmark hierarchy made measurable

[Argudo et al., *Orometry-based Terrain Analysis and Synthesis*](https://dl.acm.org/doi/10.1145/3355089.3356535)
(SIGGRAPH Asia 2019; [code](https://github.com/oargudo/orometry-terrains)) notes that existing
synthesis "produce[s] locally plausible results [but] often fail[s] to respect global
structure," and there is "a dearth of automated metrics for assessing terrain properties at a
macro level." Their descriptor is built on the peak/saddle graph ("Divide Tree") and the joint
distribution of:

- **Prominence** — how far you must descend from a peak before you can ascend a higher one.
  This is the rigorous quantitative version of "is this a landmark or just a bump."
- **Isolation** — distance to the nearest higher terrain.
- **Dominance** — prominence / elevation.

They show the *same* Divide Tree with a real vs uniform prominence distribution produces
visibly different mountain character.

**This is the most actionable metric in the document for BZ.** A 2560 m map with forty 20 m
bumps and no dominant peak is noise; the same map with one 150 m-prominence massif, three or
four 40–60 m secondaries, and everything else under 15 m has a hierarchy. That is the
primary/secondary/tertiary composition rule made numeric and testable.

## 4.4 Legibility, landmarks, composition

Kevin Lynch's five elements — paths, edges, districts, nodes, landmarks — are used essentially
verbatim in level design. The
[Level Design Book's Wayfinding chapter](https://book.leveldesignbook.com/process/blockout/wayfinding)
lists them plus **dead reckoning** (estimating position from heading, speed and elapsed time)
as the fallback when landmarks are absent. **[INFERRED, strong]** — a BZ player crossing 5 km
in a hover tank is doing exactly dead reckoning plus landmark bearing, and dead reckoning fails
badly on featureless noise. It also grades wayfinding aids by certainty; the band terrain
generation can actually buy is the "coarse" one (35–60%): **composition/sightlines, ground
composition, repetition** — which is the band that makes a map navigable without hand-holding.

[LEVEL-DESIGN.org's Landmarks article](https://level-design.org/?page_id=2261) gives the most
implementable rules found:

- A landmark is "a unique element of level architecture that stands out from the composition,"
  distinguished by form, colour and scale.
- **Don't cluster landmarks.** Small environments want *one* central landmark visible from most
  locations.
- Large open worlds use **landmark-to-landmark navigation**: on reaching a landmark, the player
  should be able to see *several new ones* ahead.
- Landmarks must be recognisable from multiple angles.

The [Composition chapter](https://book.leveldesignbook.com/process/blockout/massing/composition)
supplies the governing one-liner:

> "A tall thing only seems special if it is surrounded by short things."

Hierarchy is entirely a function of local contrast — which is precisely why homogeneous fBm
cannot produce it. The corollary answers "everything is interesting = nothing is interesting":
if every element uses strong contrast, nothing stands out. Contrast axes available are
**height, density/spread, orientation, shape**. It also warns that a landmark "has to feel
relevant and useful, otherwise it doesn't function as a landmark," and that "if the player has
no reason to look along a sightline, then there is a high probability that they won't use the
sightline at all."

**Large areas of deliberately boring, low-relief ground are not wasted space; they are the
negative space that lets landmarks read** — and in BZ they double as the buildable pockets.
That is a happy coincidence worth exploiting.

The [Landscape chapter](https://book.leveldesignbook.com/process/blockout/massing/landscape)
is the most terrain-specific source found: its catalogue of readable landforms (plateaus,
terraces, craters, bowls, hollows) and readable path types (**ledge paths** open on one side,
**cuttings** enclosed both sides, **ridge paths** raised and open both sides with sweeping
views, **switchbacks**) is effectively a generator vocabulary. It also advises that
rivers/roads should curve significantly, since dead-straight lines read as industrial.

## 4.5 Author the skeleton, noise the flesh

The industry answer is unanimous: procedural fills in; an authoring layer places structure.

- **Ghost Recon Wildlands** ([80.lv](https://80.lv/articles/procedural-world-building-in-ghost-recon-wildlands),
  [GDC](https://www.gdcvault.com/play/1024029/-Ghost-Recon-Wildlands-Terrain)): designers
  authored road/river/rail **networks first**, then a Houdini tool converted those networks
  into heightmaps — terrain conformed to the authored graph, not the reverse. The procedural
  layer's value was cheap re-rolls, not authorship (one city "has probably been completely
  rebuilt more than 5 times").
- **Horizon Zero Dawn** ([Guerrilla](https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn)):
  artists author *rules*; placement is procedural, intent is authored.
- **Hydrology-first generation** (Génevaux et al., above) is the most directly stealable
  algorithm: domain contour + river mouths → grow a river network by node expansion →
  Voronoi watersheds → per-patch terrain. Control is via a painted **river slope map** and
  **terrain slope map**. Branching uses
  [Horton–Strahler](https://en.wikipedia.org/wiki/Strahler_number) ordering with three
  probabilities summing to 1. A single parameter ζ controls network character: ζ≈0 gives many
  similar-sized basins with heavy ramification; ζ=20 gives one large drainage network plus
  several small ones. **ζ is essentially a landmark-hierarchy dial** — the difference between
  ten equal hills and one massif with foothills.
- **Local-constraint methods have the same disease.**
  [Boris the Brave on WFC](https://www.boristhebrave.com/2020/04/13/wave-function-collapse-explained/):
  "because WFC only constrains nearby tiles, it rarely generates large scale structures, which
  can give large levels a homogenous, unplanned look."

Survey-level: [Galin et al., *A Review of Digital Terrain Modeling*](https://onlinelibrary.wiley.com/doi/10.1111/cgf.13657)
(CGF 2019) and [Argudo et al., *Terrain descriptors*](https://onlinelibrary.wiley.com/doi/10.1111/cgf.70080)
(CGF 2025) — both **paywalled during this pass; cited from abstracts only.**

## 4.6 Other measurable proxies

- **Slope distribution has a hard right shoulder in reality.** In steep landscapes worldwide,
  modal hillslope angles cluster at **30–35°** regardless of climate or erosion rate, because
  landsliding caps gradients; landslide initiation spans ~25° (saturated angle of repose) to
  ~45° (dry) — [Montgomery, *Slope Distributions, Threshold Hillslopes, and Steady-State
  Topography*](https://gis.ess.washington.edu/grg/publications/pdfs/AJS2001_copy.pdf) (Am. J.
  Sci. 2001). Raw fBm instead has a smooth tail running past 60°. **[INFERRED]** — this
  aligns beautifully with BZ's own ~45° AI-pathing ceiling (§1.2).
- **Drainage density** (channel length / basin area,
  [ref](https://en.wikipedia.org/wiki/Drainage_density)) — one number saying whether the
  terrain has a dissection network at all.
- **Interior local-minima count** — real terrain has near zero; fBm has thousands. Cheapest
  possible "is this eroded" test. **[INFERRED]**, falls out of the drainage argument.

## 4.7 Where thread 4 is genuinely thin

- No numeric rule for landmark **counts or spacing** exists in any source found; all guidance
  is qualitative. Any number the generator uses is our own calibration.
- No defensible numeric ratio for primary:secondary:tertiary shapes. The canonical
  [Blevins article](http://www.neilblevins.com/art_lessons/composition_primary_secondary_and_tertiary_shapes/composition_primary_secondary_and_tertiary_shapes.htm)
  could not be loaded; treat any "1:3:12"-style rule as invented.
- **Nothing in this literature covers alien terrain.** PTRM explicitly used "only structures
  commonly found on Earth." For Achilles/Io/Venus skins we can knowingly violate Earth
  geology — but the *legibility and hierarchy* findings are about human perception, not
  geology, and still apply.

---

# Translating to generator rules

Proposed measurable rules. Each is tagged with its basis. These are proposals to add to or
amend `docs/04`; they are **not** yet validated by playtest.

**Index.** G1 economy per player · G2 size · G3 travel time · G4 build vs combat terrain ·
G5 base-pocket geysers · G6 contested economy · G7 landmark hierarchy · G8 terrain statistics ·
G9 skeleton first · G10 route topology · G11 hover terrain · G13 contestable-site count ·
G14 recovery zone · G15 scrap granularity · G16 short route is dangerous · G17 choke length ·
G18 playable fraction and spawns · G19 symmetry · G20 do not generate.
*(G12 was folded into G20; the numbering is left as-is so cross-references stay stable.)*

**Which rules would change generator output the most, if you only implement a few:**
**G13** (count contestable sites), **G14** (recovery zone), **G7** (prominence hierarchy),
**G3** (travel time at real speeds), **G1** (per-player economy). The first two are entirely
absent from `docs/04` today; the third is the difference between "eroded noise" and "a place".

## G1 — Economy budget is per player, not per km²

**Basis: [MEASURED] tournament-pool split (§2.1).**

> **G1a.** Target **4.5–6.5 geysers per strategy player** (tournament-pool median 5.0; 8 of 9
> pool maps inside 4.0–6.0). Hard-fail outside **3.0–10.0**.
>
> **G1b.** Target **60–100 scrap per strategy player** (pool median 70, range 59–140). Hard-fail
> below 50 or above 150. For 2-player maps allow the upper half of the band; for 4-player maps
> the lower half.
>
> **G1c.** Keep total scrap in **200–400** and geysers in **8–40**, matching the whole corpus
> envelope.

This **supersedes `docs/04` Rule E1's** geysers/km² framing as the primary constraint —
density should be a *derived* check, not the target. Retain 0.46–2.9 geysers/km² as a sanity
bound (that is the tournament pool's observed range).

## G2 — Size is chosen by player count, and 1280 m is banned for strategy

**Basis: [MEASURED] (§2.1) + [CONSENSUS] criticism of size/player mismatch (§2.2, §2.4).**

> **G2a.** 2 players → 2560 m. 3–4 players → 3840 m (tournament median). 5+ → 5120 m.
> **Never generate a 1280 m strategy map** — none is in the tournament pool, and the only
> 1280 m corpus map is absent from it.
>
> **G2b.** Cross-check against travel time (G3). If G2a and G3 disagree, G3 wins.

## G3 — Travel time, computed at real vehicle speeds

**Basis: [OFFICIAL] speeds (§1.4) + [OPINION] target match length (§2.6) + [INFERRED].**

Use **20 m/s** (Tank) as the reference combat-unit speed and **15 m/s** (Scavenger) for
economy hauls. **Do not use 60 m/s** — that is Razor flavour text, not a sustained speed.

> **G3a.** Base-to-base *path* distance should give **90–210 s** one-way at 20 m/s
> (1800–4200 m of path). Below 90 s the map is a rush-fest; above 210 s reinforcement stops
> working — the Mercy Hills failure ("take your base with you, or it will take forever to get
> reinforcements", §2.3).
>
> **G3b.** Every scrap field assigned to a base should be within **35 s at 15 m/s (≈525 m)**
> of that base's buildable pocket. The beginner guide flags scrap "about half a kilometer
> from our starting geyser" as already a meaningful cost (§1.5), so 525 m is the outer edge
> of comfortable.
>
> **G3c.** Sanity target for match length: **≤30 minutes** for a 2-player map (§2.6).
> Not directly checkable, but G3a and G1 are its proxies.
>
> **G3d. Bin it, and declare the bin up front.** Follow TLMC practice (§3.1) and treat travel
> time as a named archetype chosen *before* generation, not measured after:
> **Rush ≤ 110 s · Standard 110–160 s · Macro 160–210 s** (at 20 m/s). A ten-map pack should be
> roughly **5 Standard, 3 Macro, 2 Rush** — the SC2 community's own guidance is that about half
> a pool should be the standard archetype and the rest outliers. **[INFERRED]** from §3.1.
>
> **G3e.** The BZ community had to invent a *social* rule to compensate for maps not enforcing
> rush distance — the "no Rec-rush in the first 3–5 minutes" convention (§2.4b).
> **[INFERRED]** A generated map should make that convention unnecessary by construction.

## G4 — Separate build terrain from combat terrain

**Basis: [CONSENSUS] — the Basic Mapmaking doctrine (§1.2).**

> **G4a.** Classify every cell as **buildable** (slope <5° over ≥20 m radius) or **combat**
> (everything else). Target **20–35%** buildable by area, concentrated in discrete pockets
> rather than spread thin.
>
> **G4b.** The straight line between any two base pockets must pass through **≥60% combat-class
> terrain**. If a corridor of buildable ground connects two bases, players will build forward
> along it and the map degenerates into a base-creep war.
>
> **G4c.** Geysers must be inside buildable pockets (already `docs/04` E3). Additionally,
> **contested geysers should sit at pocket *edges*** — buildable enough to hold, exposed
> enough to lose.

## G5 — Give each base pocket enough geysers to reach full tech

**Basis: [OPINION] Fernando's building/geyser dependencies (§1.5) + [INFERRED].**

> **G5.** Each base's home pocket should contain **≥2 geysers within 200 m of each other**
> (the beginner guide's stated unit-efficiency radius, §1.5), so a player can site Recycler
> and Factory together without a second expedition. Remaining per-player geysers go outside
> the home pocket, as expansion targets.

## G6 — Contested economy, with a stated fraction

**Basis: amends `docs/04` E5; supported by [CONSENSUS] on "areas where you want there to be a
lot of fighting" (§1.2) and by the tournament pool's tight economies (§2.1).**

> **G6a.** **40–55%** of geysers should be *contested* — within 15% path distance of two or
> more bases. Below 30% there is nothing to fight over; above ~60% nobody can hold an economy
> and the game never develops. (`docs/04` says 30–50%; the tournament pool's tighter economy
> argues for shifting the band up. **[INFERRED]** — the exact number is a calibration guess.)
>
> **G6b.** The **largest single scrap field on the map must be contested**, not inside anyone's
> home pocket. Rockslide's praised "huge hill to capture" (§2.3) and Battle Grounds' repeated
> "central high ground" (§2.2) are the same idea: one prize everyone wants.
>
> **G6c. Decouple geyser placement from scrap placement.** The most contested geyser cluster
> (typically the map centre) should have **< 15% of the map's scrap within 300 m of it**, so
> that taking it early costs income rather than granting it. Corners is explicitly designed
> this way — "Never set Recycler in the center set of geysers ... The lack of scrap collection
> will automatically set you behind" (§2.4b). **[INFERRED from a single strong source]** —
> high-value idea, needs playtest.
>
> **G6d.** When computing per-base economy fairness (`docs/04` E4), **discount scrap beyond
> ~525 m path from the base pocket** (G3b) — players demonstrably fail to collect it (§2.4b,
> Ice-Ice). Counting it as home economy overstates a base's real income.
>
> **G6e.** Aim for the economy to run *nearly* dry — Faner's "u run out of scrap for few
> seconds only ... perfect" (§2.3). **[INFERRED]** proxy: total map scrap should be
> **8–15× the cost of a full first army** (~8 scrap/tank × ~10 tanks × N players).

## G7 — Landmark hierarchy, enforced by prominence

**Basis: [Argudo et al.] (§4.3) + [Level Design Book] (§4.4). Numbers are [INFERRED] calibration.**

> **G7a.** Compute topographic **prominence** for every local peak. A 2560–3840 m map should
> have: **exactly 1** peak with prominence ≥ 60% of the map's total relief; **3–5** peaks
> between 20% and 50%; and everything else below 12%. A flat prominence spectrum is the
> numeric signature of noise.
>
> **G7b.** The dominant landmark should be visible (unoccluded ray-march) from **≥50% of
> buildable ground**. "A tall thing only seems special if it is surrounded by short things."
>
> **G7c.** Landmarks must not cluster: no two peaks in the ≥20%-prominence set within
> **15% of the map diagonal** of each other.
>
> **G7d.** The dominant landmark should be **useful, not decorative** — put economy or high
> ground on it (§4.4: a landmark "has to feel relevant and useful"). Ideally it *is* the
> contested prize of G6b.

## G8 — Terrain statistics that distinguish designed from noise

**Basis: [PTRM] (§4.2), [Montgomery] (§4.6), [Génevaux] (§4.1). All cheap to compute.**

> **G8a. Slope histogram must have a shoulder.** Modal slope in the steep-terrain class should
> fall in **30–35°**, with a sharp fall-off above ~45°. Reject maps whose slope histogram has a
> long smooth tail past 60° — that is the fBm signature, and 45° is also BZ's AI-pathing
> ceiling (§1.2).
>
> **G8b. Interior local minima ≈ 0.** Count cells that are strictly lower than all 8
> neighbours and are not on the map edge. Real terrain has near zero; fBm has thousands.
> Target **< 1 per km²** after erosion. Cheapest available "is this eroded" test.
>
> **G8c. Geomorphon mix.** Compute geomorphons at ~50–150 m support radius. Reject the
> "slope + shoulder monoculture" that characterises synthetic terrain; require non-trivial
> fractions of **valley, ridge, summit and depression** (the four classes PTRM found most
> positively correlated with perceived realism, r = +0.42 to +0.66). **Do not** use PTRM's
> fitted coefficients — its scale is ~40× ours (§4.2).
>
> **G8d. Prefer derivative-damped fBm** (Quilez, §4.1) over plain fBm as the base field: it
> produces flats and roughs in the same pass, which is exactly the G4a buildable/combat split.

## G9 — Author the skeleton first

**Basis: [CONSENSUS] across Wildlands, HZD, Génevaux, WFC (§4.5); already the direction of
`docs/04` §7.**

> **G9.** Place the layout graph — base pockets, geyser nodes, the contested prize, the
> ridge/valley skeleton — **before** any noise. Then synthesise terrain that realises it, and
> use noise only to fill between authored features. Reject the "generate noise, hope a layout
> falls out" loop; every source that has shipped a large procedural world says the structure
> must be authored.

## G10 — Route topology and readable paths

**Basis: amends `docs/04` C3/C4; supported by [CONSENSUS] on multiple fight areas (§2.4) and
"too easy to base camp" (§2.3).**

> **G10a.** Keep `docs/04` C3 (≥2 topologically distinct base-to-base routes) and strengthen
> it: **the two routes should differ in character**, not just position — e.g. one ridge path
> (fast, exposed, long sightlines) and one cutting (slow, covered). The DM reviews reward
> exactly this variety (§2.4).
>
> **G10b.** **Anti-base-camp check.** For each base pocket, find the minimum-width corridor
> set that isolates it. If a single position with clear line of sight covers **>70% of the
> pocket's buildable area** from outside weapons-effective range of the pocket's own centre,
> flag the map — that is the Rockslide base-camp failure (§2.3).
>
> **G10c.** Target **N+1 to N+2 distinct fight arenas** for N players — "four distinct playing
> areas surrounding a central hub" is the shape players praise (§2.4). Measure as the number
> of open basins ≥ 10,000 m² separated by terrain of ≥20° slope.

## G11 — Hover-specific terrain

**Basis: [OFFICIAL] jump mechanics (§1.3) + [INFERRED].**

> **G11a.** Terrain intended to *block* must be steep **and** wide: sustained >45° for
> **≥40 m of horizontal run**. A short steep lip is a ramp, not a wall, because jump height
> scales with forward momentum.
>
> **G11b.** Deliberately place **jump lines**: a ≥100 m straight run-up of <10° slope
> terminating in a 20–35° ramp, connecting two otherwise separated areas. This is a
> BZ-specific route type with no RTS equivalent, and it makes the map feel like Battlezone
> rather than like a generic heightmap. **[INFERRED]** — needs playtest.
>
> **G11c.** Run the equivalent of the editor's Smoother over the final heightmap: no isolated
> single-cell spikes or pits, which "get the player stuck" (§1.2).

## G13 — Count contestable sites, don't just measure a contested fraction

**Basis: [CONSENSUS] Howard's armor-count law + TLMC base counts (§3.2, §3.1). The strongest
single transfer in this document.**

> **G13a.** Define a **contestable economic site** as a cluster of ≥1 geyser and/or ≥20 scrap
> value whose members are within 150 m of each other, and which is not inside any base's home
> pocket. Target **4–5 such sites** for a 2-player map and **N+2 to N+3** for N players.
> **Hard-fail below 3** — with only two contested sites, whoever wins the first engagement
> snowballs and the loser has nowhere to rebuild ("the down player is forced to prematurely
> 'gg'", §3.2).
>
> **G13b.** If a generated map is found (in playtest) to be too easy to dominate, **add a site
> before adding scrap**; if the loser recovers too easily, **make the top site harder to reach**
> rather than removing sites. That is Howard's stated tuning order.

## G14 — Every map needs a recovery zone

**Basis: [CONSENSUS] Lost World's armor-free region + SC2's safe natural/third (§3.2, §3.1).
`docs/04` has no equivalent rule, and optimising for "evenly contested" will destroy it.**

> **G14.** Each base must have a **low-value refuge**: a region of ≥15,000 m² containing
> **≤5% of map scrap and no contested geyser**, reachable from that base's pocket without
> crossing a contested site, and not on the shortest path between any two bases. "some of the
> best maps don't place the armors for maximal coverage, instead they distribute armor in an
> uneven way to further specialize certain areas."

## G15 — Scrap granularity varies by exposure

**Basis: [CONSENSUS] denial-granularity (§3.2) + [MEASURED] corpus scrap object values (§1.4).**

> **G15a.** In **contested** areas use **many small pieces** (`npscr*`, value 1) — a raider can
> only deny what he can physically drive over, and a partially-eaten field still feeds the
> loser.
>
> **G15b.** In **home** pockets, larger fields (`sfield8`/`sfieldC`, value 8/10) are fine and
> reduce object count.
>
> **G15c.** Following the only quantitative BZ scrap-placement rule found (§3.3): aim for
> **5–9 discrete scrap fields**, each a real cluster rather than confetti, with **no more than
> 2–3 near any single base**. Prefer fewer, chunkier fields over uniform scatter.

## G16 — The short route must be the dangerous one

**Basis: [CONSENSUS by convergence] — Quake and SC2 reach this independently (§3.4 item 1).**

> **G16a.** Of the ≥2 required routes between each base pair (`docs/04` C3), the **shortest must
> have the least cover and the longest sightlines**; the longer alternative must be more
> enclosed. Measure as mean unoccluded view distance sampled along each route's centreline —
> require the short route's mean sightline to exceed the long route's by **≥40%**.
>
> **G16b.** If that test fails, the fix is to *open up* the short route, not to lengthen it.

## G17 — Chokepoint length, not just width

**Basis: [OPINION but well-argued] RumbleBadger's three failure modes (§3.1); BZ canyons are
naturally long, so this is the failure BZ is most exposed to.**

> **G17a.** Keep `docs/04` C4's ≥30 m minimum width, and add a **maximum sustained length**: no
> corridor narrower than 60 m may run for more than **250 m** without opening into a basin of
> ≥10,000 m². "The chokes may be an acceptable width … but they are too long."
>
> **G17b.** **Open space immediately behind each base choke** — ≥20,000 m² of manoeuvring room
> inside the pocket, so a defender has somewhere to fight rather than being pinned in the
> corridor. Also matches the BZ community's own tower-placement advice (§2.4b: put the guns at
> the mouth, keep the inside clear, "be careful with too much congestion").

## G18 — Playable fraction and spawn hygiene

**Basis: [MEASURED, external] SC2 ~69% playable (§3.1); [CONSENSUS] Howard's spawn rules (§3.2).**

> **G18a.** Target **60–75% of the terrain extent as playable ground**, with the remainder
> blended background terrain rather than a visible drop-off (§1.2). Quantifies `docs/04` T4.
>
> **G18b.** No spawn point within **150 m** of a contested site or the map's single most
> valuable economic cluster — "put a spawn right next to the most important armor" is the named
> failure. And where two spawns are within 150 m of each other, their distances to the nearest
> three economy objects must match within **15%**.
>
> **G18c.** Cross-spawn fairness check: for every ordered pair of start positions, compute path
> distance both ways around the map; **flag any disparity >35%** of the longer distance (§3.1).

## G19 — Symmetry: mirror the pockets, vary the middle

**Basis: [INFERRED] resolution of the RTS/FPS conflict (§3.4), consistent with the corpus and
with Theater o' Pain (§2.6). Amends `docs/04` Rule S1, which currently poses this as an
either/or.**

> **G19a.** Apply **N-fold rotational symmetry to base pockets and their immediate economy**
> (the "home" region, out to ~400 m), so start conditions are provably equal.
>
> **G19b.** **Do not** mirror the contested middle. Let terrain and site character vary there —
> that is where the map's identity lives, and mirroring it halves the map's content
> ("This effectively halves the gameplay of the level", §3.4).
>
> **G19c.** Where asymmetry does reach a base, *compensate it with a role* rather than
> eliminating it, as Theater o' Pain does — closer scrap but less of it, so that player "has to
> be more aggressive" (§2.6). **[INFERRED]** — hard to automate; likely a human-curation
> criterion rather than a generator rule.

## G20 — Do not generate

> **G20.** No respawning scrap (§1.5 — "most players don't like it"). No economy object
> unreachable by ground path (already `docs/04` C1). No map where the `.des`-advertised geyser
> and scrap counts disagree with what is actually placed — the `.des` numbers are how players
> judge a map before loading it (§1.1).

---

# What to avoid — failure modes named by players

Ordered roughly by how often they appear in the sources. Each is a *player's* complaint, not
an invented one, except where marked.

1. **Flat, featureless ground with no cover.** "Based on flat surface with few natural
   obstructions for cover" (Rave Zone); "Landscape a little flat in places" (Ridge of Doom).
   [§2.4]
2. **Economy that does not scale with player count.** "Shortage of scrap with more than two
   players" (Clash of Titans); "Potentially insufficient scrap for large multiplayer battles"
   (Canyon Lands); "possibly undersized for 4 players" (PAC-MAN!). [§2.2]
3. **Too big to reinforce.** "Tried this map, it's HUGE"; "it will take forever to get
   reinforcements to where you need them" (Mercy Hills). [§2.3]
4. **Base-campable.** "it may be a bit too easy to base camp" (Rockslide, author's own
   admission). [§2.3]
5. **Symmetric + coverless = punishing, not balanced.** "Symmetrically based map focusing
   around a center spike ... Very few hiding places. Not a map for the amateur against the
   pro" (King Flanker). Symmetry alone does not make a map fair to play, only fair on paper.
   [§2.4]
6. **Illegible terrain.** "Plenty of powerups and weapons but hard to find because of
   confusing terrain" (Call of the Wild). [§2.4]
7. **Bland — technically fine, memorable to nobody.** "Has 'average' written all over it.
   Nothing special ... Lacks a final punch" (The Hills); "Textures are a little bland"
   (Strike at the Heart). [§2.4]
8. **Layouts the AI cannot path.** "Complex layout with lava features causes AI pathfinding
   issues" (Fortress Io); "AI performs poorly" (The Final Hope); ">45° slopes" break AI
   navigation. [§2.2, §1.2]
9. **Items/economy scattered uniformly instead of placed at risk.** The inverse of the praise
   "power-ups are not scattered everywhere" (Deadly Ground) and "Harder-to-reach power-ups
   offer better quality" (Q4RaceTZ). [§2.4]
10. **Spiky micro-terrain that traps units** — the reason the editor ships a Smoother to fix
    "dips and spikes that may get the player stuck". [§1.2]
11. **Noise-terrain statistics** — uniform feature scale, no drainage, thousands of interior
    pits, slope histogram with a long smooth tail. Scores 0.18–0.27 on PTRM against real
    terrain's 0.66–0.86. [§4.1, §4.2] **[INFERRED that players would call this "not organic"** —
    but note the highest praise found in the whole pass was literally the word *organic*
    (§2.5).]
12. **Respawning scrap.** "most players don't like it". [§1.5] **[OPINION — single source.]**

Failure modes named in the adjacent-genre literature that BZ maps are equally exposed to
(**[CONSENSUS]** within those communities; **[INFERRED]** that they apply to BZ):

13. **Too few contestable sites → snowball.** With only two or three, "the down player is
    forced to prematurely 'gg'." [§3.2]
14. **No recovery zone.** A map where every region is contested gives a losing player nowhere
    to rebuild. Note this is the failure a naive fairness optimiser will *create*, because
    "evenly contested everywhere" scores well on the obvious metrics. [§3.2, §3.1]
15. **The shortest route is also the safest.** "otherwise players will take it all the time and
    nothing interesting will happen." [§3.2]
16. **Chokes too long** — acceptable width but hundreds of metres of corridor. Ranked among the
    most common map defects, and the one BZ canyon maps are most prone to. [§3.1]
17. **"Swiss cheese" / room-hall-room.** Too many passages destroys the meaning of position;
    too few and rigid produces "poor chokepoints and bad gameplay." Both extremes are named
    failures. [§3.2]
18. **Turtle clusters.** Several individually-safe expansions close together are collectively a
    fortress. The fix is to devalue the cluster's anchor, not to move it. [§3.1]
19. **Spawn adjacent to the best resource**, or two nearby spawns with unequal access. [§3.2]
20. **Balanced but featureless.** "this kind of map is 'good' but not great." Equally,
    "creative" at the cost of balance "doesn't qualify as 'good'." Both are explicit
    non-goals. [§3.1]
21. **Over-constrained maps that force one line of play.** "When the game was in the countdown
    I already knew as an observer what both players would do." [§3.1]

---

# Open questions this pass could not close

1. **`bzmaps.com` was down all session** (HTTP 522). It is the largest indexed per-map metadata
   archive. Retry — it likely yields a much bigger `Geysers:`/`Scrap:` dataset than the 35-map
   corpus, which would let G1's bands be fitted rather than estimated.
2. **`bzforum.matesfamily.org` is dead** and its map-making threads are not in the Wayback
   availability index under the URLs search engines still list. Someone with the community's
   archive may have them.
3. **The corpus `scrap` column vs authors' quoted scrap totals disagree** for Theater o' Pain
   (200 vs 400). Resolve before trusting G1b's absolute numbers. [§2.6]
4. **5 m vs 10 m grid.** The official manual and the format documentation both say 10 m cells;
   `docs/04` uses 5 m. Every slope threshold depends on this. [§1.1]
5. **Two tournament-pool maps (Decimation Valley, Felix Ganymede) are not in the corpus.**
   Adding them would improve the fit behind G1/G2.
6. **The Battlezone Strategy Discord is where the live competitive scene talks** and is not
   web-indexed. Every "why is this map good" opinion found here is second-hand relative to
   that. For real consensus, ask there. (Linked from
   [battlezonecommunity.com](https://www.battlezonecommunity.com/), which is otherwise just a
   landing page — "Focused Battlezone 98 Redux tactics hub – hybrid FPS/RTS. No drama. Just
   strategy.")
7. **Beware automated page summarisation on these sources.** During this pass one fetch of the
   [Basic Mapmaking](https://steamcommunity.com/sharedfiles/filedetails?id=647966056) guide
   returned a truncated version missing the entire Map Layout section, which nearly caused the
   most important BZ design quotes in this document to be dropped as unsourced. Steam
   Community pages rate-limit aggressively (HTTP 429) and degrade silently. **Verify key
   quotes against raw HTML.**
8. **Numbers ported from SC2 and Quake are in those games' units and tempos.** The rush-distance
   *bins* transfer; the *values* were reinterpreted here at BZ speeds and are **[INFERRED]**.
   Nothing in G13–G18 has been playtested.
