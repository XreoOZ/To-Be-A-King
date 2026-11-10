"""
Modular, Generic Strategic AI System for Any Feudal Realm / Faction Ruler
Scalable to multiple AI factions without hardcoded names or flavor strings.
"""
import random
from game.data.provinces import PROVINCES, ADJACENCY, find_shortest_path
from game.data.characters import CHARACTERS
from game.data.buildings import BUILDING_SPECS
from game.core.map import CELL_TO_PROV, PROV_TO_TILES, get_province_capital_tile
from game.systems.economy import get_vassal_landed_status, sync_province_holdings_stats
from game.systems.military import get_siegeable_holdings

def standardize_realm_laws(state, ruler_id):
    """
    Uniformly standardizes an AI ruler's vassals' feudal obligations (Tax & Levies).
    Ensures AI forces maintain uniform 20% levies, 20% tax across their feudal subjects (matching physical holdings).
    """
    realm_provs = [pid for pid, p in PROVINCES.items() if p.get("owner") == ruler_id]
    for pid in realm_provs:
        for v in state.vassals.get(pid, []):
            v["tax_rate"] = 20
            v["levy_rate"] = 20
            v["tax_locked"] = True
            v["levy_locked"] = True
            st = get_vassal_landed_status(state, v, pid)
            v["tax_contribution"] = st["tax_paid"]
            v["levy_contribution"] = st["levy_contribution"]
        sync_province_holdings_stats(state, pid)

def standardize_enemy_ai_laws(state):
    """Backwards-compatible wrapper for enemy ruler."""
    standardize_realm_laws(state, state.enemy_id)

def evaluate_target_province(state, target_pid, friendly_provs, hostile_armies, ruler_id):
    """
    Calculates strategic value of invading a target enemy province for ruler_id:
    - High priority for adjacent border provinces (shorter march, safer supply lines).
    - High priority for undefended provinces (opportunistic strike where enemy is weak).
    - Bonus for enemy capital (prestige blow and command disruption).
    - Heavy penalty if defended by superior hostile forces.
    """
    prov = PROVINCES.get(target_pid)
    if not prov:
        return 0
    score = 100

    # 1. Proximity bonus (adjacent to our realm frontier)
    is_border = any(target_pid in ADJACENCY.get(fp, []) for fp in friendly_provs)
    if is_border:
        score += 50
    else:
        score -= 20

    # 2. Defenseless target evaluation (Opportunistic: attack where hostile armies are NOT!)
    armies_in_target = [ha for ha in hostile_armies if ha.province == target_pid]
    if not armies_in_target:
        score += 60
    else:
        defending_men = sum(ha.troops for ha in armies_in_target)
        score -= min(120, defending_men // 10)

    # 3. Enemy capital bonus
    t_owner = prov.get("owner")
    if t_owner:
        t_cap = state.get_realm_capital(t_owner)
        if target_pid == t_cap:
            score += 45

    # 4. Target richness (number of unconquered holdings to flip province)
    holdings = get_siegeable_holdings(state, target_pid, ruler_id)
    score += len(holdings) * 15

    return score

def evaluate_saxon_target(state, target_pid, danelaw_provs, player_armies):
    """Backwards-compatible wrapper."""
    return evaluate_target_province(state, target_pid, danelaw_provs, player_armies, state.enemy_id)

def run_realm_ai(state, ruler_id):
    """
    Master Tactical & Strategic AI for any AI Ruler (parameterized by ruler_id).
    Scalable, flexible feudal doctrine:
    1. Raise Army: Mobilize fyrds when threatened or when an offensive window opens.
    2. Safe Staging Point: All contingents assemble at a safe fortress before advancing.
    3. Grand Strategic Maneuvers:
       - Force ratio awareness: Crush equal/weaker threats; avoid suicidal head-on attacks.
       - Flank maneuvers & counter-invasions when outnumbered (diversionary pressure).
       - Smart target selection: Prioritizes undefended, high-value border shires.
       - Pounce on isolated enemy detachments before they can unite.
       - Demobilization during peacetime to preserve treasury.
    """
    ruler = CHARACTERS.get(ruler_id)
    if not ruler or not ruler.get("alive", True):
        return

    # Check if this realm is a vassal of the player or another liege in peace
    if ruler.get("liege") == state.player_id:
        return

    # Check if the player is a peaceful vassal of this liege
    if getattr(state, "player_liege", None) == ruler_id and getattr(state, "war_status", "war") == "vassalage":
        # AI does not wage war against its own vassal in peacetime!
        for a in list(state.armies):
            if a.owner == ruler_id and not getattr(a, "is_demobilizing", False) and not a.in_battle:
                state.disband_army(a)
        return

    # Check if this liege is a peaceful vassal of the player
    if getattr(state, "enemy_liege", None) == state.player_id and getattr(state, "war_status", "war") == "vassalage":
        for a in list(state.armies):
            if a.owner == ruler_id and not getattr(a, "is_demobilizing", False) and not a.in_battle:
                state.disband_army(a)
        return

    realm_provs = [pid for pid, p in PROVINCES.items() if p.get("owner") == ruler_id]
    if not realm_provs:
        return

    r_name = ruler["name"].split()[0]
    realm_name = ruler.get("realm", "the realm")

    # 1. Standardize AI realm feudal laws
    standardize_realm_laws(state, ruler_id)

    # 2. Tactical Reconnaissance: Hostile and Realm Armies
    hostile_armies = [a for a in state.armies if getattr(state, "are_hostile", lambda o1, o2: o1 != o2)(ruler_id, a.owner) and a.troops > 0]
    my_armies = [a for a in state.armies if a.owner == ruler_id and a.troops > 0]
    hostile_provs = [pid for pid, p in PROVINCES.items() if getattr(state, "are_hostile", lambda o1, o2: o1 != o2)(ruler_id, p.get("owner"))]

    invading_threats = {}    # realm pid -> list of invading hostile armies
    threatened_borders = {}  # realm pid -> list of bordering hostile armies
    all_threat_armies = []

    for ha in hostile_armies:
        ha_locations = [ha.province]
        if ha.is_moving and ha.path:
            ha_locations.append(ha.path[-1])

        for loc in ha_locations:
            if loc in realm_provs:
                invading_threats.setdefault(loc, []).append(ha)
                if ha not in all_threat_armies:
                    all_threat_armies.append(ha)
            else:
                for rp in realm_provs:
                    if loc in ADJACENCY.get(rp, []):
                        threatened_borders.setdefault(rp, []).append(ha)
                        if ha not in all_threat_armies:
                            all_threat_armies.append(ha)

    total_my_field = sum(a.troops for a in my_armies)
    total_threat_troops = sum(ha.troops for ha in all_threat_armies)
    unraised_my_levies = sum(state.get_available_province_levies(pid, ruler_id)[0] for pid in realm_provs)
    has_invasion = len(invading_threats) > 0
    has_border_threat = len(threatened_borders) > 0
    is_at_peace = (not hostile_armies and not hostile_provs and not has_invasion and not has_border_threat)

    # 3. Peacetime Frontier Vigilance & SIAGA (With 20-Day Mutual De-escalation Protocol)
    is_official_peace = (getattr(state, "war_status", "war") == "peace")
    if is_official_peace:
        # Actual invaders trespassing inside domestic territory: full emergency!
        actual_invaders = [a for a in state.armies if a.owner != ruler_id and a.province in realm_provs and a.troops > 0]
        if not actual_invaders:
            # Detect neutral foreign forces near realm borders
            foreign_armies = [a for a in state.armies if a.owner != ruler_id and a.troops > 0 and not a.is_demobilizing]
            border_standoff_provs = set()
            total_neutral_border_troops = 0

            for fa in foreign_armies:
                pair_key = frozenset({ruler_id, fa.owner})
                # If currently in mutual de-escalation cooldown, ignore
                if pair_key in getattr(state, "ai_standoff_cooldown", {}):
                    continue
                fa_loc = fa.province
                for rp in realm_provs:
                    if fa_loc in ADJACENCY.get(rp, []):
                        border_standoff_provs.add(rp)
                        total_neutral_border_troops += fa.troops

            if not border_standoff_provs:
                # Stand Down: Frontier quiet, no standoff active. Demobilize!
                if my_armies:
                    for a in list(my_armies):
                        if not getattr(a, "is_demobilizing", False) and not a.in_battle:
                            state.disband_army(a)
                    state.logs.append(f"🕊 Stand Down: Frontier peaceful. {r_name} demobilizes border guards.")
                return

            # SIAGA Alert: Foreign hosts sighted near border. Mobilize and hold border line ("diam membeku")
            cooldown = getattr(state, "enemy_raise_cooldown", 0) if ruler_id == state.enemy_id else 0
            if cooldown <= 0 and (len(my_armies) == 0 or total_my_field < total_neutral_border_troops * 0.8) and unraised_my_levies >= 40:
                count, men = state.raise_all_realm_levies(ruler_id)
                if count > 0:
                    state.logs.append(f"🛡 Border Alert (SIAGA): Foreign hosts sighted near border! {r_name} summons {count} hosts (+{men:,} men) to secure the frontier!")
                    my_armies = [a for a in state.armies if a.owner == ruler_id and a.troops > 0]

            target_prov_list = list(border_standoff_provs)
            for a in my_armies:
                if a.in_battle or a.is_mustering or a.courier_en_route:
                    continue

                # If already stationed in a border province, freeze and hold position ("diam membeku")
                if a.province in target_prov_list:
                    if a.is_moving:
                        dest_p = CELL_TO_PROV.get(a.tile_path[-1]) if a.tile_path else a.province
                        if dest_p not in realm_provs:
                            a.tile_path = []
                            a.is_moving = False
                            a.move_progress = 0.0
                    continue

                # March towards the nearest border standoff province
                if not a.is_moving:
                    nearest_bp = min(target_prov_list, key=lambda bp: len(find_shortest_path(a.province, bp) or [999]))
                    target_tile = get_province_capital_tile(nearest_bp)
                    if a.tile != target_tile:
                        state.order_army_march_to_tile(a, target_tile)
            return

    # Dynamic Demobilization & Peacetime Economy for Unofficial Peace
    if is_at_peace:
        # Complete Peacetime: Disband all mobilized warbands to save gold and replenish garrisons!
        if my_armies:
            for a in list(my_armies):
                if not getattr(a, "is_demobilizing", False) and not a.in_battle:
                    state.disband_army(a)
            state.logs.append(f"⚔ Stand Down: Peace in the realm. {r_name} demobilizes all field hosts.")
        return

    # Partial Demobilization: If idle at home without threats or targets, demobilize
    if not has_invasion and not has_border_threat and not hostile_armies:
        if not hostile_provs and my_armies:
            for a in list(my_armies):
                if not getattr(a, "is_demobilizing", False) and not a.in_battle:
                    state.disband_army(a)
            state.logs.append(f"⚔ Stand Down: {r_name} demobilizes idle warbands to replenish garrisons.")
            return

    # 4. Smart Mobilization Logic
    cooldown = getattr(state, "enemy_raise_cooldown", 0) if ruler_id == state.enemy_id else 0
    should_mobilize = False
    has_active_threat_or_target = bool(hostile_armies or hostile_provs or has_invasion or has_border_threat)
    if cooldown <= 0 and has_active_threat_or_target:
        if (has_invasion or has_border_threat) and unraised_my_levies >= 40:
            should_mobilize = True
        elif len(my_armies) == 0 and len(hostile_armies) > 0 and unraised_my_levies >= 50:
            should_mobilize = True
        elif len(my_armies) == 0 and len(hostile_provs) > 0 and ruler.get("gold", 100) >= 40 and unraised_my_levies >= 150:
            should_mobilize = True
        elif total_my_field < total_threat_troops * 0.85 and unraised_my_levies >= 50:
            should_mobilize = True

    if should_mobilize:
        is_emerg = (has_invasion or has_border_threat)
        if hasattr(state, "raise_all_realm_levies"):
            count, men = state.raise_all_realm_levies(ruler_id, is_emergency=is_emerg)
        else:
            count, men = state.raise_all_enemy_levies(is_emergency=is_emerg)
        if count > 0:
            if has_invasion:
                inv_names = ", ".join([PROVINCES[rp]['name'].split()[0] for rp in invading_threats.keys()])
                state.logs.append(f"⚔ Frontier Breach! Hostile forces entered {inv_names}! {r_name} sounds the call to arms (+{men:,} men)!")
            elif has_border_threat:
                t_names = ", ".join([PROVINCES[rp]['name'].split()[0] for rp in threatened_borders.keys()])
                state.logs.append(f"⚔ Border Warning: Troops gathering near {t_names}! {r_name} mobilizes {count} hosts (+{men:,} men)!")
            else:
                state.logs.append(f"⚔ Campaign Mobilization: {r_name} summons {count} provincial hosts (+{men:,} men) for military maneuvers!")

    # 5. Determine Safe Staging Point
    cap_pid = state.get_realm_capital(ruler_id)
    if cap_pid in realm_provs and cap_pid not in invading_threats:
        rally_prov = cap_pid
    else:
        unthreatened = [p for p in realm_provs if p not in invading_threats]
        if unthreatened:
            rally_prov = max(unthreatened, key=lambda p: PROVINCES[p].get("levies_max", 0))
        else:
            rally_prov = realm_provs[0]

    safe_rally_tile = get_province_capital_tile(rally_prov)

    # 6. Merge Any Contingents on Same Tile
    all_my_tiles = set(getattr(a, "tile", None) for a in my_armies if getattr(a, "tile", None) is not None)
    for t in all_my_tiles:
        state.merge_armies_on_tile(t, ruler_id)

    # Re-evaluate armies after tile merging
    my_armies = [a for a in state.armies if a.owner == ruler_id and a.troops > 0]
    if not my_armies:
        return

    ready_hosts = [a for a in my_armies if not a.is_mustering and not a.courier_en_route and not a.in_battle]
    if not ready_hosts:
        return

    ready_hosts.sort(key=lambda x: x.troops, reverse=True)
    main_host = ready_hosts[0]
    total_field_troops = sum(a.troops for a in my_armies)

    # 7. Safe Rally & Concentration Phase
    hosts_away_from_rally = [a for a in ready_hosts if getattr(a, "tile", None) != safe_rally_tile and not a.is_sieging]
    
    is_assembled = (len(my_armies) == 1) or (
        main_host.troops >= total_field_troops * 0.80 and not hosts_away_from_rally
    )

    has_urgent_siege = any(ha.is_sieging for ha in all_threat_armies)
    can_sally_emergency = has_invasion and (main_host.troops >= total_threat_troops * 0.85 or has_urgent_siege)

    if not is_assembled and not can_sally_emergency:
        # Mandatory Rally: All warbands converge on safe_rally_tile before launching maneuvers
        for a in ready_hosts:
            a_tile = getattr(a, "tile", None)
            if a_tile != safe_rally_tile and not a.is_moving and not a.is_sieging:
                state.order_army_march_to_tile(a, safe_rally_tile)
                p_from = PROVINCES.get(a.province, {}).get("name", "Province").split()[0]
                p_to = PROVINCES[rally_prov]["name"].split()[0]
                state.logs.append(f"⚔ Feudal Muster: {a.name} ({a.troops:,} men) marching from {p_from} to safe staging point in {p_to}.")
        return

    # If assembled, any detached minor reinforcements continue marching towards main_host
    target_follow_tile = getattr(main_host, "tile", safe_rally_tile)
    for sub_a in ready_hosts[1:]:
        if getattr(sub_a, "tile", None) != target_follow_tile and not sub_a.is_moving and not sub_a.is_sieging:
            state.order_army_march_to_tile(sub_a, target_follow_tile)

    # 8. Grand Strategic Maneuvers

    # TACTICAL CHECK 1: AMBUSH ISOLATED ENEMY DETACHMENTS
    isolated_targets = [ha for ha in hostile_armies if ha.troops < 250 and main_host.troops >= ha.troops * 1.3]
    if isolated_targets and not main_host.is_sieging and not has_invasion:
        chosen_prey = min(isolated_targets, key=lambda ha: (getattr(ha, "tile", (0, 0))[0] - getattr(main_host, "tile", (0, 0))[0])**2 + (getattr(ha, "tile", (0, 0))[1] - getattr(main_host, "tile", (0, 0))[1])**2)
        prey_tile = getattr(chosen_prey, "tile", get_province_capital_tile(chosen_prey.province))
        if getattr(main_host, "tile", None) != prey_tile and not main_host.is_moving:
            state.order_army_march_to_tile(main_host, prey_tile)
            state.logs.append(f"⚔ Ambush Stratagem: {r_name} moves {main_host.troops:,} warriors to intercept isolated enemy detachment ({chosen_prey.troops:,} men) in {PROVINCES[chosen_prey.province]['name']}!")
            return

    # TACTICAL CHECK 2: INVASION DEFENSE & FLANKING COUNTER-ATTACK
    if has_invasion:
        target_inv_prov = list(invading_threats.keys())[0]
        invading_armies = invading_threats[target_inv_prov]
        inv_troops = sum(ia.troops for ia in invading_armies)

        if main_host.troops >= inv_troops * 0.75:
            # Favorable or equal battle: march to confront invaders!
            target_tile = getattr(invading_armies[0], "tile", get_province_capital_tile(target_inv_prov))
            if not main_host.is_moving and getattr(main_host, "tile", None) != target_tile:
                state.order_army_march_to_tile(main_host, target_tile)
                state.logs.append(f"⚔ Counter-Attack: {r_name} leads {main_host.troops:,} men to confront enemy forces in {PROVINCES[target_inv_prov]['name']}!")
        else:
            # Severely Outnumbered: Diversionary Flank
            hostile_provs = [pid for pid, p in PROVINCES.items() if getattr(state, "are_hostile", lambda o1, o2: o1 != o2)(ruler_id, p.get("owner"))]
            undefended_enemy = [pid for pid in hostile_provs if not any(ha.province == pid for ha in hostile_armies)]
            if undefended_enemy and not main_host.is_moving:
                flank_target = undefended_enemy[0]
                flank_tile = get_province_capital_tile(flank_target)
                state.order_army_march_to_tile(main_host, flank_tile)
                state.logs.append(f"⚔ Diversionary Maneuver: Outnumbered at home, {r_name} flanks the hostile host to strike undefended {PROVINCES[flank_target]['name']}!")
            else:
                cap_tile = get_province_capital_tile(rally_prov)
                if getattr(main_host, "tile", None) != cap_tile and not main_host.is_moving:
                    state.order_army_march_to_tile(main_host, cap_tile)
                    state.logs.append(f"⚔ Defensive Stand: {r_name} falls back to fortified {PROVINCES[rally_prov]['name']} to hold the stronghold.")

    # TACTICAL CHECK 3: BORDER MANEUVERS
    elif has_border_threat:
        target_border = list(threatened_borders.keys())[0]
        opposing_armies = threatened_borders.get(target_border, [])
        opp_troops = sum(oa.troops for oa in opposing_armies)

        border_tiles = PROV_TO_TILES.get(target_border, [])
        if opposing_armies and border_tiles:
            opp_tile = getattr(opposing_armies[0], "tile", get_province_capital_tile(opposing_armies[0].province))
            closest_border_tile = min(border_tiles, key=lambda t: (t[0]-opp_tile[0])**2 + (t[1]-opp_tile[1])**2)
        else:
            closest_border_tile = get_province_capital_tile(target_border)

        if getattr(main_host, "tile", None) != closest_border_tile and not main_host.is_moving:
            state.order_army_march_to_tile(main_host, closest_border_tile)
            state.logs.append(f"⚔ Border Patrol: {r_name} moves {main_host.troops:,} warriors to border outpost in {PROVINCES[target_border]['name']}.")
        elif getattr(main_host, "tile", None) == closest_border_tile and not main_host.is_moving:
            if opposing_armies and (main_host.troops >= opp_troops * 0.75 or main_host.troops >= 350):
                target_enemy_tile = getattr(opposing_armies[0], "tile", get_province_capital_tile(opposing_armies[0].province))
                target_enemy_prov = opposing_armies[0].province
                state.order_army_march_to_tile(main_host, target_enemy_tile)
                state.logs.append(f"⚔ Strategic Sally: {r_name} advances across the border into {PROVINCES[target_enemy_prov]['name']} to engage the enemy host!")

    # TACTICAL CHECK 4: STRATEGIC OFFENSIVE CAMPAIGN
    else:
        if main_host.troops >= 200 and not main_host.is_moving:
            if main_host.province not in realm_provs:
                cur_unconquered = get_siegeable_holdings(state, main_host.province, ruler_id)
                matching_tiles = [h[1][0] for h in cur_unconquered]
                if getattr(main_host, "tile", None) in matching_tiles:
                    if not getattr(main_host, "siege_intent", False) and getattr(main_host, "siege_prep_days", 0) <= 0 and not main_host.is_sieging and getattr(main_host, "siege_packup_days", 0) <= 0:
                        state.order_army_siege_holding(main_host, main_host.tile)
                    return
                elif cur_unconquered:
                    next_holding_tile = cur_unconquered[0][1][0]
                    state.order_army_march_to_tile(main_host, next_holding_tile)
                    state.logs.append(f"⚔ Siege Advance: {r_name} moves to besiege {cur_unconquered[0][0]} in {PROVINCES[main_host.province]['name']}!")
                    return

            # Cunning Target Selection: Evaluate all hostile provinces by strategic score!
            hostile_provs = [pid for pid, p in PROVINCES.items() if getattr(state, "are_hostile", lambda o1, o2: o1 != o2)(ruler_id, p.get("owner"))]
            if hostile_provs:
                scored_targets = [(pid, evaluate_target_province(state, pid, realm_provs, hostile_armies, ruler_id)) for pid in hostile_provs]
                scored_targets.sort(key=lambda x: x[1], reverse=True)
                chosen_target = scored_targets[0][0]

                holdings = get_siegeable_holdings(state, chosen_target, ruler_id)
                if holdings:
                    target_tile = holdings[0][1][0]
                    h_name = holdings[0][0]
                else:
                    target_tile = get_province_capital_tile(chosen_target)
                    h_name = f"{PROVINCES[chosen_target]['name']} Capital"

                state.order_army_march_to_tile(main_host, target_tile)
                state.logs.append(f"⚔ Strategic Advance: {r_name} leads {main_host.troops:,} warriors into {PROVINCES[chosen_target]['name']} to capture {h_name}!")
            else:
                # No remaining hostile provinces to conquer: Demobilize the main host!
                if not getattr(main_host, "is_demobilizing", False) and not main_host.in_battle:
                    state.disband_army(main_host)
                    state.logs.append(f"⚔ Stand Down: All objectives completed. {r_name} demobilizes the army to garrison.")

def run_viking_ai(state):
    """Backwards-compatible wrapper calling run_realm_ai for the enemy faction."""
    run_realm_ai(state, state.enemy_id)
