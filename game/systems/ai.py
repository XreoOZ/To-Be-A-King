"""
Danelaw Viking AI Systems - Intelligent Border Awareness, Strategic Invasions & Dynamic Demobilization
"""
import random
from game.data.provinces import PROVINCES, ADJACENCY, find_shortest_path
from game.data.buildings import BUILDING_SPECS
from game.core.map import CELL_TO_PROV, PROV_TO_TILES, get_province_capital_tile
from game.systems.economy import get_vassal_landed_status, sync_province_holdings_stats
from game.systems.military import get_siegeable_holdings

def standardize_enemy_ai_laws(state):
    """
    Uniformly standardizes all Danelaw / Viking AI vassals' feudal obligations (Tax & Levies).
    Ensures enemy AI forces maintain uniform 80% levies, 20% tax across all Norse Jarls.
    """
    danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == state.enemy_id]
    for pid in danelaw_provs:
        for v in state.vassals.get(pid, []):
            v["tax_rate"] = 20    # Uniform standard 20% tax
            v["levy_rate"] = 80   # Uniform standard 80% levy obligation
            v["tax_locked"] = True
            v["levy_locked"] = True
            st = get_vassal_landed_status(state, v, pid)
            v["tax_contribution"] = st["tax_paid"]
            v["levy_contribution"] = st["levy_contribution"]
        sync_province_holdings_stats(state, pid)

def run_viking_ai(state):
    """
    Master Tactical & Strategic AI for Halfdan Ragnarsson (The Great Heathen Host).
    Features:
    - High Reactivity: Daily/Bi-daily border checks and instant counter-maneuvers.
    - True Offensive Opportunism: Marches into Saxon England to raid, siege, and conquer holdings.
    - Economic & Upkeep Sense: Demobilizes weak remnants during peacetime to save gold.
    - Tactical Merging: Unites dispersed warbands into an overwhelming deathstack.
    - Dynamic Target Selection: Prioritizes vulnerable, high-value Saxon cities and border forts.
    """
    danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == state.enemy_id]
    if not danelaw_provs:
        return

    # 1. Standardize AI realm laws
    standardize_enemy_ai_laws(state)

    # 2. Reconnaissance: Player Armies & Threats
    player_armies = [a for a in state.armies if a.owner == state.player_id and a.troops > 0]
    danelaw_armies = [a for a in state.armies if a.owner == state.enemy_id and a.troops > 0]

    invading_threats = {}    # Danelaw pid -> list of invading player armies
    threatened_borders = {}  # Danelaw pid -> list of bordering player armies
    all_threat_armies = []

    for pa in player_armies:
        pa_locations = [pa.province]
        if pa.is_moving and pa.path:
            pa_locations.append(pa.path[-1])

        for loc in pa_locations:
            if loc in danelaw_provs:
                invading_threats.setdefault(loc, []).append(pa)
                if pa not in all_threat_armies:
                    all_threat_armies.append(pa)
            else:
                for dp in danelaw_provs:
                    if loc in ADJACENCY.get(dp, []):
                        threatened_borders.setdefault(dp, []).append(pa)
                        if pa not in all_threat_armies:
                            all_threat_armies.append(pa)

    total_viking_field = sum(a.troops for a in danelaw_armies)
    total_threat_troops = sum(pa.troops for pa in all_threat_armies)
    unraised_enemy_levies = sum(PROVINCES[pid].get("levies_current", 0) for pid in danelaw_provs)
    has_invasion = len(invading_threats) > 0
    has_border_threat = len(threatened_borders) > 0

    # 3. Dynamic Demobilization & Peacetime Sense
    # If no immediate invasion or border threats exist:
    if not has_invasion and not has_border_threat:
        # Can Halfdan mount an offensive campaign?
        can_attack = (total_viking_field >= 200 and state.enemy.get("gold", 100) >= 30)
        
        # If not strong enough or too poor to attack, and realm is peaceful: demobilize idle remnants!
        if not can_attack and not player_armies:
            active_offensive = any(a.province not in danelaw_provs or a.is_sieging for a in danelaw_armies)
            if not active_offensive and danelaw_armies:
                for a in list(danelaw_armies):
                    if not a.in_battle and not a.is_sieging and not a.is_mustering and not a.courier_en_route:
                        state.disband_army(a)
                state.logs.append("Peace in Britain: Halfdan stands down his Viking warbands to replenish garrisons and save treasury.")
                return

    # 4. Smart Mobilization Logic
    should_mobilize = False
    if state.enemy_raise_cooldown <= 0:
        if (has_invasion or has_border_threat) and unraised_enemy_levies >= 40:
            # Immediate defense mobilization
            should_mobilize = True
        elif len(danelaw_armies) == 0 and len(player_armies) > 0 and unraised_enemy_levies >= 50:
            # Player has armies in the field; assemble host to match
            should_mobilize = True
        elif len(danelaw_armies) == 0 and state.enemy.get("gold", 100) >= 60 and unraised_enemy_levies >= 150:
            # Offensive opportunity: assemble the Great Heathen Army to invade!
            should_mobilize = True
        elif total_viking_field < total_threat_troops * 0.85 and unraised_enemy_levies >= 50:
            # Reinforce existing army if outnumbered
            should_mobilize = True

    if should_mobilize:
        is_emerg = (has_invasion or has_border_threat)
        count, men = state.raise_all_enemy_levies(is_emergency=is_emerg)
        if count > 0:
            if has_invasion:
                inv_names = ", ".join([PROVINCES[dp]['name'].split()[0] for dp in invading_threats.keys()])
                state.logs.append(f"⚔ INVASION ALERT! Saxon armies inside {inv_names}! Danelaw sounds war horns (+{men:,} men)!")
            elif has_border_threat:
                t_names = ", ".join([PROVINCES[dp]['name'].split()[0] for dp in threatened_borders.keys()])
                state.logs.append(f"⚔ Raven Warning! Saxon armies massing near {t_names}! Danelaw mobilizes (+{men:,} men)!")
            else:
                state.logs.append(f"⚔ The Great Heathen Army stirs! Halfdan summons Viking warbands (+{men:,} men in {count} hosts) for an invasion!")

    # 5. Army Coordination: Merge Local Contingents
    for dp in danelaw_provs:
        state.merge_armies_in_province(dp, state.enemy_id)

    # 6. Identify Main Host & Ready Units
    ready_hosts = [a for a in state.armies if a.owner == state.enemy_id and not a.is_mustering and not a.courier_en_route and not a.in_battle]
    if not ready_hosts:
        return

    ready_hosts.sort(key=lambda x: x.troops, reverse=True)
    main_host = ready_hosts[0]

    # Smaller detached warbands (reinforcements) should march towards main_host to deathstack
    main_tile = getattr(main_host, "tile", None)
    if main_tile:
        for sub_a in ready_hosts[1:]:
            if not sub_a.is_moving and not sub_a.is_sieging and getattr(sub_a, "tile", None) != main_tile:
                state.order_army_march_to_tile(sub_a, main_tile)

    # 7. Strategic Action Execution
    # POSTURE 1: DIRECT INVASION DEFENSE (Repel invaders in Danelaw)
    if has_invasion:
        target_inv_prov = list(invading_threats.keys())[0]
        invading_army = invading_threats[target_inv_prov][0]
        target_tile = getattr(invading_army, "tile", get_province_capital_tile(target_inv_prov))
        if not main_host.is_moving and getattr(main_host, "tile", None) != target_tile:
            state.order_army_march_to_tile(main_host, target_tile)
            state.logs.append(f"⚔ Halfdan marches his Great Host ({main_host.troops:,} men) to intercept Saxon invaders in {PROVINCES[target_inv_prov]['name']}!")

    # POSTURE 2: BORDER INTERCEPTION & SALLY OUT (Active border threat)
    elif has_border_threat:
        target_border = list(threatened_borders.keys())[0]
        opposing_armies = threatened_borders.get(target_border, [])
        opp_troops = sum(oa.troops for oa in opposing_armies)

        if opposing_armies:
            opp_tile = getattr(opposing_armies[0], "tile", get_province_capital_tile(opposing_armies[0].province))
            closest_border_tile = min(PROV_TO_TILES[target_border], key=lambda t: (t[0]-opp_tile[0])**2 + (t[1]-opp_tile[1])**2)
        else:
            closest_border_tile = get_province_capital_tile(target_border)

        if getattr(main_host, "tile", None) != closest_border_tile and not main_host.is_moving:
            state.order_army_march_to_tile(main_host, closest_border_tile)
            state.logs.append(f"⚔ Halfdan advances to border tile {closest_border_tile} in {PROVINCES[target_border]['name']} to block Saxon invasion!")
        elif getattr(main_host, "tile", None) == closest_border_tile and not main_host.is_moving:
            # Sally out aggressively if confident in battle!
            if opposing_armies and (main_host.troops >= opp_troops * 0.70 or main_host.troops >= 400):
                target_enemy_tile = getattr(opposing_armies[0], "tile", get_province_capital_tile(opposing_armies[0].province))
                target_enemy_prov = opposing_armies[0].province
                state.order_army_march_to_tile(main_host, target_enemy_tile)
                state.logs.append(f"⚔ RETALIATION! Halfdan sallies out across the frontier to crush the Saxon host in {PROVINCES[target_enemy_prov]['name']}!")

    # POSTURE 3: TRUE OFFENSIVE CAMPAIGN & PLUNDER (Invasion of Saxon England)
    else:
        # If no threat and Halfdan has >= 200 warriors, launch an offensive raid!
        if main_host.troops >= 200 and not main_host.is_moving:
            # If main_host is already standing on a siegeable holding in player territory, stay and siege!
            if main_host.province not in danelaw_provs:
                cur_unconquered = get_siegeable_holdings(state, main_host.province, state.enemy_id)
                # If there are still holdings to siege in this province, target the next one
                matching_tiles = [h[1][0] for h in cur_unconquered]
                if getattr(main_host, "tile", None) in matching_tiles:
                    # Currently besieging holding, continue siege!
                    return
                elif cur_unconquered:
                    # Move to next holding in this province to finish conquest
                    next_holding_tile = cur_unconquered[0][1][0]
                    state.order_army_march_to_tile(main_host, next_holding_tile)
                    state.logs.append(f"⚔ Halfdan advances to siege {cur_unconquered[0][0]} in {PROVINCES[main_host.province]['name']}!")
                    return

            # Pick best Saxon province to invade
            player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == state.player_id]
            if player_provs:
                # Find border provinces adjacent to Danelaw first
                border_targets = [p for p in player_provs if any(p in ADJACENCY.get(dp, []) for dp in danelaw_provs)]
                if border_targets:
                    chosen_target = random.choice(border_targets)
                else:
                    chosen_target = random.choice(player_provs)

                holdings = get_siegeable_holdings(state, chosen_target, state.enemy_id)
                if holdings:
                    target_tile = holdings[0][1][0]
                    h_name = holdings[0][0]
                else:
                    target_tile = get_province_capital_tile(chosen_target)
                    h_name = f"{PROVINCES[chosen_target]['name']} Capital"

                state.order_army_march_to_tile(main_host, target_tile)
                state.logs.append(f"⚔ THE GREAT VIKING ARMY MARCHES! Halfdan invades {PROVINCES[chosen_target]['name']} to plunder {h_name} ({main_host.troops:,} warriors)!")
