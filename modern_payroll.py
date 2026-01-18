from dataclasses import dataclass

@dataclass
class Employee:
    name: str
    hourly_rate: float
    hours_worked: float

class ModernPayroll:
    def calculate_pay(self, employee: Employee) -> float:
        gross_pay = employee.hours_worked * employee.hourly_rate
        net_pay = gross_pay * 0.80  # Assuming a tax rate of 20%
        return net_pay