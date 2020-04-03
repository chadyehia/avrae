"""
Created on Jan 13, 2017

@author: andrew
"""
import itertools
import logging

from cogs5e.models.errors import NoActiveBrew
from cogs5e.models.homebrew import Pack, Tome
from cogs5e.models.homebrew.bestiary import Bestiary
from cogsmisc.stats import Stats
from utils.functions import search_and_select
from .compendium import compendium

HOMEBREW_EMOJI = "<:homebrew:434140566834511872>"
HOMEBREW_ICON = "https://avrae.io/assets/img/homebrew.png"

log = logging.getLogger(__name__)


# ==== entitlement search helpers ====
async def available(ctx, entities, entity_type, user_id=None):
    """
    Returns the subset of entities available to the given user in this context.

    :param ctx: The Discord Context.
    :type ctx: discord.ext.commands.Context
    :param entities: The compendium list of all available entities.
    :type entities: list[gamedata.shared.Sourced]
    :param entity_type: The entity type to get entitlements data for.
    :type entity_type: str
    :param user_id: The Discord user ID of the user (optional - if not passed, assumes ctx.author)
    :type user_id: int
    :rtype: list[gamedata.shared.Sourced]
    """
    if user_id is None:
        user_id = ctx.author.id

    available_ids = await ctx.bot.ddb.get_accessible_entities(ctx, user_id, entity_type)
    if available_ids is None:
        return [e for e in entities if e.is_free]
    return [e for e in entities if e.is_free or e.entity_id in available_ids]


# ---- helper ----
def get_homebrew_formatted_name(named):
    if named.homebrew:
        return f"{named.name} ({HOMEBREW_EMOJI})"
    return named.name


# ---- monster stuff ----
async def select_monster_full(ctx, name, cutoff=5, return_key=False, pm=False, message=None, list_filter=None,
                              return_metadata=False, extra_choices=None, selectkey=None):
    """
    Gets a Monster from the compendium and active bestiary/ies.
    """
    choices = await get_monster_choices(ctx)
    await Stats.increase_stat(ctx, "monsters_looked_up_life")

    # #881
    if extra_choices:
        choices.extend(extra_choices)
    if selectkey is None:
        selectkey = get_homebrew_formatted_name

    return await search_and_select(ctx, choices, name, lambda e: e.name, cutoff, return_key, pm, message, list_filter,
                                   selectkey=selectkey, return_metadata=return_metadata)


async def get_monster_choices(ctx, filter_by_license=True, homebrew=True):
    """
    Gets a list of monsters in the current context for the user to choose from.

    :param ctx: The context.
    :param filter_by_license: Whether to filter out entities the user cannot access.
    :param homebrew: Whether to include homebrew entities.
    """
    if filter_by_license:
        available_monsters = await available(ctx, compendium.monsters, 'monster')
    else:
        available_monsters = compendium.monsters

    if not homebrew:
        return available_monsters

    # personal bestiary
    try:
        bestiary = await Bestiary.from_ctx(ctx)
        await bestiary.load_monsters(ctx)
        custom_monsters = bestiary.monsters
        bestiary_id = bestiary.id
    except NoActiveBrew:
        custom_monsters = []
        bestiary_id = None

    # server bestiaries
    choices = list(itertools.chain(available_monsters, custom_monsters))
    if ctx.guild:
        async for servbestiary in Bestiary.server_bestiaries(ctx):
            if servbestiary.id != bestiary_id:
                await servbestiary.load_monsters(ctx)
                choices.extend(servbestiary.monsters)
    return choices


# ---- spell stuff ----
async def select_spell_full(ctx, name, *args, extra_choices=None, **kwargs):
    """
    Gets a Spell from the compendium and active tome(s).

    :rtype: :class:`~cogs5e.models.spell.Spell`
    """
    choices = await get_spell_choices(ctx)
    await Stats.increase_stat(ctx, "spells_looked_up_life")

    # #881
    if extra_choices:
        choices.extend(extra_choices)
    if 'selectkey' not in kwargs:
        kwargs['selectkey'] = get_homebrew_formatted_name

    return await search_and_select(ctx, choices, name, lambda e: e.name, *args, **kwargs)


async def get_spell_choices(ctx, filter_by_license=True, homebrew=True):
    """
    Gets a list of spells in the current context for the user to choose from.

    :param ctx: The context.
    :param filter_by_license: Whether to filter out entities the user cannot access.
    :param homebrew: Whether to include homebrew entities.
    """
    if filter_by_license:
        available_spells = await available(ctx, compendium.spells, 'spell')
    else:
        available_spells = compendium.spells

    if not homebrew:
        return available_spells

    # personal active tome
    try:
        tome = await Tome.from_ctx(ctx)
        custom_spells = tome.spells
        tome_id = tome.id
    except NoActiveBrew:
        custom_spells = []
        tome_id = None

    # server tomes
    choices = list(itertools.chain(available_spells, custom_spells))
    if ctx.guild:
        async for servtome in Tome.server_active(ctx):
            if servtome.id != tome_id:
                choices.extend(servtome.spells)
    return choices


# ---- item stuff ----
async def get_item_choices(ctx, filter_by_license=True, homebrew=True):
    """
    Gets a list of items in the current context for the user to choose from.

    :param ctx: The context.
    :param filter_by_license: Whether to filter out entities the user cannot access.
    :param homebrew: Whether to include homebrew entities.
    """
    if filter_by_license:
        available_items = await available(ctx, compendium.items, 'item')
    else:
        available_items = compendium.items

    if not homebrew:
        return available_items

    # personal pack
    try:
        pack = await Pack.from_ctx(ctx)
        custom_items = pack.get_search_formatted_items()
        pack_id = pack.id
    except NoActiveBrew:
        custom_items = []
        pack_id = None

    # server packs
    choices = list(itertools.chain(available_items, custom_items))
    if ctx.guild:
        async for servpack in Pack.server_active(ctx):
            if servpack.id != pack_id:
                choices.extend(servpack.get_search_formatted_items())
    return choices
