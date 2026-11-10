"""
Vassal Finances, Province Holdings Stats, Royal Ledger, and Domain Revenue
"""
from game.data.provinces import PROVINCES
from game.data.characters import CHARACTERS
from game.data.buildings import BUILDING_SPECS, get_barrack_stats

def fmt_gold(val):
    """Formats gold into a clean string, showing 1 decimal place only if fractional (e.g. 1.8g, 0.2g, 5g)."""
    if val is None:
        return "0"
    v = round(float(val), 1)
    if v == int(v):
        return f"{int(v)}"
    return f"{v:.1f}"

def sync_province_holdings_stats(state, pid=None, is_init=False):
    """
    Synchronizes province tax revenue and maximum garrison/levies strictly with its physical holdings:
    - City (1 Tile): +3 Gold/month, +100 Garrison
    - Fort (2 Tiles): +1 Gold/month, +300 Garrison
    - Barracks (1 Tile): +100 Garrison slot (+100 per upgrade level, up to 500)
    """
    target_pids = [pid] if pid else list(PROVINCES.keys())
    for p_key in target_pids:
        prov = PROVINCES.get(p_key)
        if not prov:
            continue

        p_holdings = {}
        for coord, sdata in state.settlements.items():
            if sdata.get("province") == p_key:
                hid = sdata.get("id") or coord
                if hid not in p_holdings:
                    p_holdings[hid] = sdata

        total_tax = 0
        total_garrison = 0
        crown_garrison = 0
        vassal_garrison = 0
        for s in p_holdings.values():
            stype = s.get("type", "city")
            base_tax = 0
            base_garrison = 0
            if stype in ("city", "town"):
                base_tax = 3
                base_garrison = 100
            elif stype == "fort":
                base_tax = 1
                base_garrison = 300
            elif stype == "barrack":
                lvl = s.get("level", 0)
                bstats = get_barrack_stats(lvl)
                base_garrison = bstats["garrison"]
                base_tax = 0

            # Crown Demesne or unassigned -> 100% to liege
            if s.get("is_crown_demesne", False) or not s.get("vassal_id"):
                total_tax += base_tax
                total_garrison += base_garrison
                crown_garrison += base_garrison
            else:
                v_id = s.get("vassal_id")
                v_obj = None
                for v in state.vassals.get(p_key, []):
                    if v.get("id") == v_id or v.get("name") == s.get("lord"):
                        v_obj = v
                        break
                levy_pct = (max(0, min(90, v_obj.get("levy_rate", 20))) / 100.0) if v_obj else 0.20
                tax_pct = (max(0, min(90, v_obj.get("tax_rate", 10))) / 100.0) if v_obj else 0.10
                v_garr = max(0, int(round(base_garrison * levy_pct)))
                total_garrison += v_garr
                vassal_garrison += v_garr
                total_tax += max(0, int(round(base_tax * tax_pct)))

        if not p_holdings:
            total_tax = 0
            total_garrison = 50  # Rural baseline if zero constructed holdings
            vassal_garrison = 50

        prev_max = prov.get("levies_max", 0)
        prov["tax"] = total_tax
        prov["levies_max"] = total_garrison
        prov["crown_levies_max"] = crown_garrison
        prov["vassal_levies_max"] = vassal_garrison
        if is_init or "levies_current" not in prov:
            prov["levies_current"] = total_garrison
        else:
            diff = total_garrison - prev_max
            if diff > 0:
                prov["levies_current"] = min(prov["levies_max"], prov.get("levies_current", 0) + diff)
            else:
                prov["levies_current"] = min(prov["levies_max"], max(0, prov.get("levies_current", total_garrison)))

def get_vassal_landed_status(state, v_dict, prov_id=None):
    """
    Returns detailed landed status, held fiefs, held settlements,
    gross monthly income, tax rate (0-90%), tax paid to liege, net savings,
    total garrison, levy rate (0-90%), levy contribution to liege, and household guard.
    """
    v_name = v_dict["name"]
    v_id = v_dict.get("id")

    held_fiefs = [f for f in state.fiefs.values() if f.get("holder") == v_name or f.get("vassal_id") == v_id]

    held_tiles = list(v_dict.get("tiles", []))
    for f in held_fiefs:
        for t in f.get("tiles", []):
            if t not in held_tiles:
                held_tiles.append(t)

    held_settlements = []
    seen_hids = set()
    for t in held_tiles:
        if t in state.settlements:
            sdata = state.settlements[t]
            if sdata.get("vassal_id") == v_id or sdata.get("lord") == v_name:
                hid = sdata.get("id") or sdata.get("name")
                if hid not in seen_hids:
                    seen_hids.add(hid)
                    held_settlements.append(sdata)

    is_landed = (len(held_fiefs) > 0 or len(held_settlements) > 0 or len(held_tiles) > 0)
    tax_rate = max(0, min(90, v_dict.get("tax_rate", 10)))
    levy_rate = max(0, min(90, v_dict.get("levy_rate", 20)))

    if not is_landed:
        return {
            "is_landed": False,
            "held_fiefs": [],
            "held_settlements": [],
            "total_tiles": 0,
            "gross_income": 0,
            "tax_rate": tax_rate,
            "tax_paid": 0,
            "net_savings": 0,
            "total_garrison": 0,
            "levy_rate": levy_rate,
            "levy_contribution": 0,
            "household_guard": 0
        }

    gross = 0
    total_garrison = 0
    if held_settlements:
        for s in held_settlements:
            stype = s.get("type", "city")
            spec = BUILDING_SPECS.get(stype, {})
            gross += spec.get("income", 0)
            if stype == "barrack":
                lvl = s.get("level", 0)
                bstats = get_barrack_stats(lvl)
                total_garrison += bstats.get("garrison", 100)
            else:
                total_garrison += spec.get("garrison", 100)
    else:
        gross = 0
        total_garrison = len(held_tiles) * 20

    # Sub-Vassal Tax & Levy Aggregation for Direct Vassals (Counts / Dukes)
    sub_vassal_ids = v_dict.get("sub_vassals", [])
    sub_tax_collected = 0.0
    sub_levy_collected = 0
    sub_vassals_list = []

    if sub_vassal_ids:
        target_p = prov_id or v_dict.get("province")
        prov_vassals = state.vassals.get(target_p, []) if target_p else []
        for sv_id in sub_vassal_ids:
            sv = next((v for v in prov_vassals if v.get("id") == sv_id), None)
            if not sv:
                for plist in state.vassals.values():
                    sv = next((v for v in plist if v.get("id") == sv_id), None)
                    if sv: break
            if sv:
                sv_tiles = sv.get("tiles", [])
                sv_gross = 0
                sv_garr = 0
                for t in sv_tiles:
                    s_data = state.settlements.get(t)
                    if s_data:
                        stype = s_data.get("type", "city")
                        spec = BUILDING_SPECS.get(stype, {})
                        sv_gross += spec.get("income", 0)
                        sv_garr += spec.get("garrison", 100)
                sv_tr = max(0, min(90, sv.get("tax_rate", 10)))
                sv_lr = max(0, min(90, sv.get("levy_rate", 20)))
                sv_tax_paid = round(sv_gross * (sv_tr / 100.0), 1)
                sv_levy_contrib = int(round(sv_garr * (sv_lr / 100.0)))
                sub_tax_collected += sv_tax_paid
                sub_levy_collected += sv_levy_contrib
                sub_vassals_list.append(sv)

    total_gross = round(gross + sub_tax_collected, 1)
    total_garrison = total_garrison + sub_levy_collected

    if total_gross > 0 and tax_rate > 0:
        tax_paid = round(total_gross * (tax_rate / 100.0), 1)
        tax_paid = min(tax_paid, float(total_gross))
    else:
        tax_paid = 0.0
    net_savings = round(total_gross - tax_paid, 1)

    levy_contribution = max(0, int(round(total_garrison * (levy_rate / 100.0))))
    household_guard = max(0, total_garrison - levy_contribution)

    return {
        "is_landed": True,
        "is_direct_vassal": v_dict.get("is_direct_vassal", True),
        "rank": v_dict.get("rank", "count"),
        "held_fiefs": held_fiefs,
        "held_settlements": held_settlements,
        "total_tiles": len(held_tiles),
        "own_gross_income": gross,
        "gross_income": total_gross,
        "sub_vassals_count": len(sub_vassal_ids),
        "sub_tax_collected": sub_tax_collected,
        "sub_levy_collected": sub_levy_collected,
        "sub_vassals_list": sub_vassals_list,
        "tax_rate": tax_rate,
        "tax_paid": tax_paid,
        "net_savings": net_savings,
        "total_garrison": total_garrison,
        "levy_rate": levy_rate,
        "levy_contribution": levy_contribution,
        "household_guard": household_guard
    }

def get_province_holdings(state, pid):
    """Return dict of holding_key -> list of (c, r) tiles in that province."""
    holdings = {}
    for (c, r), s in state.settlements.items():
        if s.get("province") == pid:
            h_key = s.get("id") or s.get("name", "Unknown Holding")
            holdings.setdefault(h_key, []).append((c, r))
    return holdings

def get_all_settlement_holdings(state):
    """Groups settlement tiles into unified multi-tile holding objects strictly per holding/settlement ID."""
    has_ids = any("id" in s for s in state.settlements.values())
    
    if has_ids:
        holdings_by_id = {}
        for coord, sdata in state.settlements.items():
            s_id = sdata.get("id") or coord
            if s_id not in holdings_by_id:
                holdings_by_id[s_id] = {
                    "id": s_id,
                    "name": sdata.get("name", "Holding"),
                    "province": sdata.get("province"),
                    "tiles": [],
                    "primary_tile": coord,
                    "data": sdata,
                    "occupied_by": sdata.get("occupied_by")
                }
            holdings_by_id[s_id]["tiles"].append(coord)

        holdings = []
        for s_id, h in holdings_by_id.items():
            comp = sorted(h["tiles"])
            min_c = min(c for c, r in comp)
            max_c = max(c for c, r in comp)
            min_r = min(r for c, r in comp)
            max_r = max(r for c, r in comp)
            orient = "single"
            if len(comp) == 2:
                if min_r == max_r:
                    orient = "H"
                elif min_c == max_c:
                    orient = "V"
                else:
                    orient = "H"
            elif len(comp) > 2:
                orient = "H" if (max_c - min_c) >= (max_r - min_r) else "V"
            h["min_c"] = min_c
            h["max_c"] = max_c
            h["min_r"] = min_r
            h["max_r"] = max_r
            h["orient"] = orient
            holdings.append(h)
        return holdings

    # Fallback for legacy state without 'id'
    visited = set()
    holdings = []
    for coord, sdata in state.settlements.items():
        if coord in visited:
            continue
        comp = []
        queue = [coord]
        visited.add(coord)
        while queue:
            curr = queue.pop(0)
            comp.append(curr)
            if len(comp) >= 2:
                break
            cx, cy = curr
            for nxt in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]:
                if nxt in state.settlements and nxt not in visited:
                    n_data = state.settlements[nxt]
                    if (n_data.get("province") == sdata.get("province") and
                        n_data.get("name") == sdata.get("name") and
                        n_data.get("vassal_id") == sdata.get("vassal_id") and
                        n_data.get("is_crown_demesne") == sdata.get("is_crown_demesne")):
                        visited.add(nxt)
                        queue.append(nxt)
                        break
        comp.sort()
        min_c = min(c for c, r in comp)
        max_c = max(c for c, r in comp)
        min_r = min(r for c, r in comp)
        max_r = max(r for c, r in comp)
        orient = "single"
        if len(comp) > 1:
            if min_r == max_r:
                orient = "H"
            elif min_c == max_c:
                orient = "V"
            else:
                orient = "H"
        holdings.append({
            "name": sdata.get("name", "Holding"),
            "province": sdata.get("province"),
            "tiles": comp,
            "primary_tile": comp[0],
            "data": sdata,
            "occupied_by": sdata.get("occupied_by"),
            "min_c": min_c, "max_c": max_c,
            "min_r": min_r, "max_r": max_r,
            "orient": orient
        })
    return holdings

def get_realm_finances(state, char_id=None):
    """
    Returns complete itemized breakdown of realm finances:
    - Provincial Tax Income
    - Feudal Vassal Tithes
    - Crown Demesne Direct Revenue
    - Army Field Upkeep
    - Military Facilities Upkeep
    - Net monthly cash flow & Treasury balance
    """
    if char_id is None:
        char_id = state.player_id
    r_char = CHARACTERS.get(char_id, {})

    prov_incomes = []
    total_prov_tax = 0
    for pid, prov in PROVINCES.items():
        if prov["owner"] == char_id:
            ptax = prov.get("tax", 0)
            total_prov_tax += ptax
            prov_incomes.append({
                "pid": pid,
                "name": prov["name"].split()[0],
                "tax": ptax
            })

    vassal_tithes = []
    total_vassal_tax = 0
    direct_vassal_count = 0
    for pid, prov in PROVINCES.items():
        if prov["owner"] == char_id:
            for v in state.vassals.get(pid, []):
                # Only direct vassals pay tax directly to Top Liege (King/char_id)
                if v.get("is_direct_vassal", True) or v.get("liege_id") == char_id:
                    direct_vassal_count += 1
                    st = get_vassal_landed_status(state, v, pid)
                    if st["is_landed"] and st["tax_paid"] > 0:
                        total_vassal_tax += st["tax_paid"]
                        vassal_tithes.append({
                            "name": v["name"],
                            "rank": v.get("rank", "count"),
                            "pid": pid,
                            "prov": PROVINCES[pid]["name"].split()[0],
                            "tax_rate": st["tax_rate"],
                            "tax_paid": st["tax_paid"],
                            "gross": st["gross_income"],
                            "sub_tax_collected": st.get("sub_tax_collected", 0.0),
                            "sub_vassals_count": st.get("sub_vassals_count", 0)
                        })

    # Vassal Limit Penalty: -10% direct vassal tax efficiency per excess vassal
    vassal_limit = getattr(state, "vassal_limit", 5)
    vassal_limit_penalty_pct = 0
    if direct_vassal_count > vassal_limit:
        excess = direct_vassal_count - vassal_limit
        vassal_limit_penalty_pct = min(100, excess * 10)
        efficiency = (100 - vassal_limit_penalty_pct) / 100.0
        total_vassal_tax = round(total_vassal_tax * efficiency, 1)

    crown_holdings = []
    total_crown_income = 0
    for h in get_all_settlement_holdings(state):
        sdata = h["data"]
        pid = h["province"]
        prov_owner = PROVINCES.get(pid, {}).get("owner")
        is_my_crown = False
        # Holding belongs to char_id if explicitly owned or held by char_id
        if sdata.get("owner") == char_id and sdata.get("is_crown_demesne"):
            is_my_crown = True
        elif char_id == state.player_id and sdata.get("lord") == f"{state.player['name']} (Crown Demesne)":
            is_my_crown = True
        elif prov_owner == char_id and sdata.get("is_crown_demesne") and not sdata.get("vassal_id"):
            # Ensure AI's Jorvik holdings are never counted as player's
            if char_id == state.player_id and pid == "jorvik":
                is_my_crown = False
            else:
                is_my_crown = True

        if is_my_crown:
            htype = sdata.get("type", "city")
            if htype == "fort":
                val = 1
            elif htype == "barrack":
                val = 0
            else:
                val = 3
            total_crown_income += val
            clean_name = h["name"].replace("Royal Citadel of ", "").replace("Royal Castle of ", "").replace("Royal Borough of ", "")
            crown_holdings.append({
                "name": clean_name,
                "prov": PROVINCES[pid]["name"].split()[0],
                "type": htype.capitalize(),
                "val": val
            })

    total_vassal_tax = round(total_vassal_tax, 1)
    total_income = round(total_prov_tax + total_vassal_tax + total_crown_income, 1)

    army_expenses = []
    total_army_upkeep = 0
    for a in state.armies:
        if a.owner == char_id:
            c_tr = min(a.troops, getattr(a, "crown_troops", 0))
            a.crown_troops = c_tr
            v_tr = max(0, a.troops - c_tr)
            a.vassal_levies = v_tr
            cost = max(0, int(round(c_tr / 100.0)))
            total_army_upkeep += cost
            army_expenses.append({
                "name": a.name,
                "troops": a.troops,
                "crown_troops": c_tr,
                "vassal_levies": v_tr,
                "cost": cost,
                "status": "Courier En Route" if a.courier_en_route else ("Mustering" if a.is_mustering else ("In Battle" if a.in_battle else "Mobilized"))
            })

    barrack_expenses = []
    total_facility_upkeep = 0
    for coord, sdata in state.settlements.items():
        if sdata.get("is_crown_demesne") and sdata.get("type") == "barrack":
            pid = sdata.get("province")
            prov_owner = PROVINCES.get(pid, {}).get("owner")
            is_my_barrack = (prov_owner == char_id) or (char_id == state.player_id and not sdata.get("vassal_id"))
            if is_my_barrack:
                lvl = sdata.get("level", 0)
                cost = 1 + lvl
                total_facility_upkeep += cost
                barrack_expenses.append({
                    "name": sdata.get("name", "Royal Barracks"),
                    "prov": PROVINCES[pid]["name"].split()[0],
                    "lvl": lvl,
                    "cost": cost
                })

    tribute_expenses = []
    total_tribute = 0
    if char_id == state.player_id and getattr(state, "player_liege", None) == state.enemy_id:
        # Feudal Suzerainty Tax: strictly 20% of player's gross domain income
        trib = round(total_income * 0.20, 1)
        total_tribute = trib
        liege_n = CHARACTERS.get(state.enemy_id, {}).get("name", "High King").split()[0]
        tribute_expenses.append({
            "name": f"Feudal Liege Suzerainty Tax (20%)",
            "liege": liege_n,
            "rate": 20,
            "cost": trib,
            "base": total_income
        })

    total_expense = round(total_army_upkeep + total_facility_upkeep + total_tribute, 1)
    net_monthly = round(total_income - total_expense, 1)

    return {
        "treasury": r_char.get("gold", 0),
        "total_prov_tax": total_prov_tax,
        "prov_incomes": prov_incomes,
        "total_vassal_tax": total_vassal_tax,
        "vassal_tithes": vassal_tithes,
        "total_crown_income": total_crown_income,
        "crown_holdings": crown_holdings,
        "total_income": total_income,
        "total_army_upkeep": total_army_upkeep,
        "army_expenses": army_expenses,
        "total_facility_upkeep": total_facility_upkeep,
        "barrack_expenses": barrack_expenses,
        "total_tribute": total_tribute,
        "tribute_expenses": tribute_expenses,
        "direct_vassal_count": direct_vassal_count,
        "vassal_limit": vassal_limit,
        "vassal_limit_penalty_pct": vassal_limit_penalty_pct,
        "total_expense": total_expense,
        "net_monthly": net_monthly
    }
