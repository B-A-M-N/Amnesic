global_tax_rate = 0.20
def Calc_Pay(empName, hrs, rate):
    return hrs * rate * (1 - global_tax_rate)