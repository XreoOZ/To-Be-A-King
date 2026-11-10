"""
Danelaw Viking AI Systems and Law Standardization
"""
from game.data.provinces import PROVINCES
from game.systems.economy import get_vassal_landed_status, sync_province_holdings_stats

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
