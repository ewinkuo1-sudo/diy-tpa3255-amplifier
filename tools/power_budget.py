"""First-pass sine-wave budget, standard library only; no device simulation."""
import math


def budget(watts, ohms, channels=2, supply=48.0, efficiency=0.90, aux=5.0):
    if watts <= 0 or ohms <= 0 or channels <= 0 or supply <= 0:
        raise ValueError("Power, load, channels and supply must be positive")
    if not 0 < efficiency <= 1 or aux < 0:
        raise ValueError("Invalid efficiency or auxiliary power")
    vrms = math.sqrt(watts * ohms)
    irms = math.sqrt(watts / ohms)
    pout = channels * watts
    loss = pout * (1 / efficiency - 1)
    pin = pout + loss + aux
    return vrms, vrms * math.sqrt(2), irms, irms * math.sqrt(2), pin, pin / supply, loss


def report():
    print("# V0.1 功率估算\n")
    print("假設：兩聲道同時正弦輸出、48V 電源、功率級效率 90%、另加 5W 輔助預算。")
    print("效率與輔助功耗為估算假設；實際值須量測。\n")
    print("| 每聲道 W | Ω | Vrms | Vpeak | Arms | Apeak | 輸入總 W | 48V 平均 A | 功率級總損耗 W |")
    print("|---|---|---|---|---|---|---|---|---|")
    for watts, ohms in [(10, 8), (50, 8), (100, 8), (50, 4), (100, 4)]:
        values = budget(watts, ohms)
        print(f"| {watts} | {ohms} | " + " | ".join(f"{v:.2f}" for v in values) + " |")
    print("\n公式：Vrms=√(PR)，Irms=√(P/R)，峰值=RMS×√2；Pin=2P/η+Paux。")
    print("\n50W/8Ω 的初步外部電源容量預留 25%：")
    pin = budget(50, 8)[4]
    print(f"{pin * 1.25:.2f}W，即 48V 下 {pin * 1.25 / 48:.2f}A。這是容量篩選起點，不是選定料號。")
    print("\n未含：輸出電感紋波、負載相位、削波餘裕、電源瞬變、開機湧流、散熱器熱阻與環境降額。")
    print("所有列皆為需求情境，不代表 V0.1 可達成；不能由本表宣稱 THD+N 或選定保險絲。")
    print("\n重算：在專案根目錄執行 `python3 tools/power_budget.py`。")


if __name__ == "__main__":
    report()
