"""
Danelaw Viking AI Systems - Intelligent Border Awareness, Strategic Cunning & Dynamic Maneuvers
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

def evaluate_saxon_target(state, target_pid, danelaw_provs, player_armies):
    """
    Calculates strategic value of invading a Saxon province:
    - High priority for adjacent border shires (shorter march, safer lines).
    - High priority for undefended shires (striking where the enemy is weak!).
    - Bonus for enemy capital (prestige blow and command disruption).
    - Heavy penalty if defended by superior player forces.
    """
    prov = PROVINCES[target_pid]
    score = 100

    # 1. Proximity bonus (adjacent to Danelaw frontier)
    is_border = any(target_pid in ADJACENCY.get(dp, []) for dp in danelaw_provs)
    if is_border:
        score += 50
    else:
        # Distance penalty for interior shires
        score -= 20

    # 2. Defenseless target evaluation (Cunning: attack where enemy armies are NOT!)
    armies_in_target = [pa for pa in player_armies if pa.province == target_pid]
    if not armies_in_target:
        score += 60  # Ripe for the taking!
    else:
        # Defended: penalize based on garrison/army strength
        defending_men = sum(pa.troops for pa in armies_in_target)
        score -= min(120, defending_men // 10)

    # 3. Enemy capital bonus
    player_cap = state.get_realm_capital(state.player_id)
    if target_pid == player_cap:
        score += 45

    # 4. Target richness (number of unconquered holdings to flip province)
    holdings = get_siegeable_holdings(state, target_pid, state.enemy_id)
    score += len(holdings) * 15

    return score

def run_viking_ai(state):
    """
    Master Tactical & Strategic AI for Halfdan Ragnarsson (The Great Heathen Host).
    Feudal Doctrine:
    1. Raise Army: Mobilize fyrds when threatened or when an offensive window opens.
    2. Kumpul di Titik Aman: All contingents assemble at safe fortress staging point before moving out.
    3. Baru Mainin Siasat:
       - Force ratio awareness: Crush equal/weaker threats; avoid suicidal head-on attacks.
       - Flank maneuvers & counter-invasions when outnumbered (diversionary pressure).
       - Smart target selection: Prioritizes undefended, high-value border shires.
       - Pounce on isolated player detachments before they can unite.
       - Tactical regrouping when battered.
       - Demobilization during peacetime to preserve treasury.
    """
    danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == state.enemy_id]
    if not danelaw_provs:
        return

    # If Danelaw is currently a peaceful vassal of player, do not launch unprovoked attacks
    if getattr(state, "enemy_liege", None) == state.player_id:
        return

    # 1. Standardize AI realm laws
    standardize_enemy_ai_laws(state)

    # 2. Tactical Reconnaissance: Enemy (Player) & Danelaw Armies
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
    unraised_enemy_levies = sum(PROVINCES[pid].get("levies_current", 0) for pid in danelaw_provs if not state.is_province_levy_in_field(pid, state.enemy_id))
    has_invasion = len(invading_threats) > 0
    has_border_threat = len(threatened_borders) > 0

    # 3. Dynamic Demobilization & Peacetime Sense
    # If no immediate invasion or border threats exist:
    if not has_invasion and not has_border_threat:
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
            should_mobilize = True
        elif len(danelaw_armies) == 0 and len(player_armies) > 0 and unraised_enemy_levies >= 50:
            should_mobilize = True
        elif len(danelaw_armies) == 0 and state.enemy.get("gold", 100) >= 40 and unraised_enemy_levies >= 150:
            should_mobilize = True
        elif total_viking_field < total_threat_troops * 0.85 and unraised_enemy_levies >= 50:
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

    # 5. Determine Safe Staging Point ("Titik Aman")
    cap_pid = state.get_realm_capital(state.enemy_id)
    if cap_pid in danelaw_provs and cap_pid not in invading_threats:
        rally_prov = cap_pid
    else:
        unthreatened = [p for p in danelaw_provs if p not in invading_threats]
        if unthreatened:
            rally_prov = max(unthreatened, key=lambda p: PROVINCES[p].get("levies_max", 0))
        else:
            rally_prov = danelaw_provs[0]

    safe_rally_tile = get_province_capital_tile(rally_prov)

    # 6. Merge Any Contingents on Same Tile
    all_enemy_tiles = set(getattr(a, "tile", None) for a in danelaw_armies if getattr(a, "tile", None) is not None)
    for t in all_enemy_tiles:
        state.merge_armies_on_tile(t, state.enemy_id)

    # Re-evaluate armies after tile merging
    danelaw_armies = [a for a in state.armies if a.owner == state.enemy_id and a.troops > 0]
    if not danelaw_armies:
        return

    ready_hosts = [a for a in danelaw_armies if not a.is_mustering and not a.courier_en_route and not a.in_battle]
    if not ready_hosts:
        return

    ready_hosts.sort(key=lambda x: x.troops, reverse=True)
    main_host = ready_hosts[0]
    total_field_troops = sum(a.troops for a in danelaw_armies)

    # 7. STAGING & ASSEMBLY PHASE ("KUMPUL DI TITIK AMAN")
    # All dispersed or newly mustered warbands MUST assemble at safe_rally_tile before launching strategy.
    hosts_away_from_rally = [a for a in ready_hosts if getattr(a, "tile", None) != safe_rally_tile and not a.is_sieging]
    
    # Are we fully assembled into a unified host?
    is_assembled = (len(danelaw_armies) == 1) or (
        main_host.troops >= total_field_troops * 0.80 and not hosts_away_from_rally
    )

    # Emergency Override: Only if enemy is actively invading/sieging a Danelaw holding right now
    has_urgent_siege = any(pa.is_sieging for pa in all_threat_armies)
    can_sally_emergency = has_invasion and (main_host.troops >= total_threat_troops * 0.85 or has_urgent_siege)

    if not is_assembled and not can_sally_emergency:
        # Mandatory Rally: All warbands converge on safe_rally_tile!
        for a in ready_hosts:
            a_tile = getattr(a, "tile", None)
            if a_tile != safe_rally_tile and not a.is_moving and not a.is_sieging:
                state.order_army_march_to_tile(a, safe_rally_tile)
                p_from = PROVINCES.get(a.province, {}).get("name", "Province").split()[0]
                p_to = PROVINCES[rally_prov]["name"].split()[0]
                state.logs.append(f"⚔ Danelaw Muster: {a.name} ({a.troops:,} men) marching from {p_from} to safe assembly point in {p_to}!")
        
        # Hosts already at safe_rally_tile HOLD POSITION and wait for comrades to arrive and merge!
        return

    # If assembled, any detached minor reinforcements continue marching towards main_host
    target_follow_tile = getattr(main_host, "tile", safe_rally_tile)
    for sub_a in ready_hosts[1:]:
        if getattr(sub_a, "tile", None) != target_follow_tile and not sub_a.is_moving and not sub_a.is_sieging:
            state.order_army_march_to_tile(sub_a, target_follow_tile)

    # 8. STRATEGIC ACTION EXECUTION ("BARU MAININ SIASAT")
    # Only the unified main_host executes grand maneuvers!

    # TACTICAL CHECK 1: AMBUSH ISOLATED ENEMY DETACHMENTS
    # If the player has a small detached army (< 250 men) within reach and Halfdan has overwhelming numbers:
    isolated_targets = [pa for pa in player_armies if pa.troops < 250 and main_host.troops >= pa.troops * 1.3]
    if isolated_targets and not main_host.is_sieging and not has_invasion:
        chosen_prey = min(isolated_targets, key=lambda pa: (getattr(pa, "tile", (0, 0))[0] - getattr(main_host, "tile", (0, 0))[0])**2 + (getattr(pa, "tile", (0, 0))[1] - getattr(main_host, "tile", (0, 0))[1])**2)
        prey_tile = getattr(chosen_prey, "tile", get_province_capital_tile(chosen_prey.province))
        if getattr(main_host, "tile", None) != prey_tile and not main_host.is_moving:
            state.order_army_march_to_tile(main_host, prey_tile)
            state.logs.append(f"⚔ Ambush Stratagem! Halfdan marches {main_host.troops:,} warriors to destroy an isolated Saxon detachment ({chosen_prey.troops:,} men) in {PROVINCES[chosen_prey.province]['name']}!")
            return

    # TACTICAL CHECK 2: INVASION DEFENSE & FLANKING COUNTER-ATTACK
    if has_invasion:
        target_inv_prov = list(invading_threats.keys())[0]
        invading_armies = invading_threats[target_inv_prov]
        inv_troops = sum(ia.troops for ia in invading_armies)

        # Force Ratio Siasat:
        if main_host.troops >= inv_troops * 0.75:
            # Favorable or equal battle: march to crush invaders!
            target_tile = getattr(invading_armies[0], "tile", get_province_capital_tile(target_inv_prov))
            if not main_host.is_moving and getattr(main_host, "tile", None) != target_tile:
                state.order_army_march_to_tile(main_host, target_tile)
                state.logs.append(f"⚔ Halfdan leads the united Great Heathen Army ({main_host.troops:,} men) to crush Saxon invaders in {PROVINCES[target_inv_prov]['name']}!")
        else:
            # Severely Outnumbered!
            # Diversionary Flank: If Saxon doomstack is sieging an outer province, Halfdan slips past to counter-invade player's homeland!
            player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == state.player_id]
            undefended_saxon = [pid for pid in player_provs if not any(pa.province == pid for pa in player_armies)]
            if undefended_saxon and not main_host.is_moving:
                flank_target = undefended_saxon[0]
                flank_tile = get_province_capital_tile(flank_target)
                state.order_army_march_to_tile(main_host, flank_tile)
                state.logs.append(f"⚔ Diversionary Maneuver! Outnumbered at home, Halfdan flanks the Saxon host to strike undefended {PROVINCES[flank_target]['name']}!")
            else:
                # Dig in at fortified capital
                cap_tile = get_province_capital_tile(rally_prov)
                if getattr(main_host, "tile", None) != cap_tile and not main_host.is_moving:
                    state.order_army_march_to_tile(main_host, cap_tile)
                    state.logs.append(f"⚔ Defensive Stand: Outnumbered, Halfdan retreats to fortified {PROVINCES[rally_prov]['name']} to make his stand!")

    # TACTICAL CHECK 3: BORDER MANEUVERS
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
            state.logs.append(f"⚔ Border Maneuver: Halfdan moves his united host ({main_host.troops:,} men) to border tile {closest_border_tile} in {PROVINCES[target_border]['name']}!")
        elif getattr(main_host, "tile", None) == closest_border_tile and not main_host.is_moving:
            # Sally out aggressively if confident in battle!
            if opposing_armies and (main_host.troops >= opp_troops * 0.75 or main_host.troops >= 350):
                target_enemy_tile = getattr(opposing_armies[0], "tile", get_province_capital_tile(opposing_armies[0].province))
                target_enemy_prov = opposing_armies[0].province
                state.order_army_march_to_tile(main_host, target_enemy_tile)
                state.logs.append(f"⚔ Preemptive Strike! The Great Heathen Army ({main_host.troops:,} men) surges across the frontier to crush the Saxons in {PROVINCES[target_enemy_prov]['name']}!")

    # TACTICAL CHECK 4: STRATEGIC OFFENSIVE CAMPAIGN (Conquest of Saxon Shires)
    else:
        # If no immediate threat and Halfdan has >= 200 warriors gathered, launch strategic invasion!
        if main_host.troops >= 200 and not main_host.is_moving:
            # If main_host is already standing on a siegeable holding in player territory, stay and siege!
            if main_host.province not in danelaw_provs:
                cur_unconquered = get_siegeable_holdings(state, main_host.province, state.enemy_id)
                matching_tiles = [h[1][0] for h in cur_unconquered]
                if getattr(main_host, "tile", None) in matching_tiles:
                    # Besieging holding, hold and complete siege!
                    return
                elif cur_unconquered:
                    # Move to next holding in this province
                    next_holding_tile = cur_unconquered[0][1][0]
                    state.order_army_march_to_tile(main_host, next_holding_tile)
                    state.logs.append(f"⚔ Siege Advance: Halfdan moves to besiege {cur_unconquered[0][0]} in {PROVINCES[main_host.province]['name']}!")
                    return

            # Cunning Target Selection: Evaluate all Saxon shires by strategic score!
            player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == state.player_id]
            if player_provs:
                scored_targets = [(pid, evaluate_saxon_target(state, pid, danelaw_provs, player_armies)) for pid in player_provs]
                scored_targets.sort(key=lambda x: x[1], reverse=True)
                chosen_target = scored_targets[0][0]

                holdings = get_siegeable_holdings(state, chosen_target, state.enemy_id)
                if holdings:
                    target_tile = holdings[0][1][0]
                    h_name = holdings[0][0]
                else:
                    target_tile = get_province_capital_tile(chosen_target)
                    h_name = f"{PROVINCES[chosen_target]['name']} Capital"

                state.order_army_march_to_tile(main_host, target_tile)
                state.logs.append(f"⚔ Strategic Campaign! Halfdan leads {main_host.troops:,} warriors into {PROVINCES[chosen_target]['name']} to capture {h_name}!")
